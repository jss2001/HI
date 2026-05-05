"""yfinance 통합 클라이언트 — 글로벌 종목 + 한국 종목 fallback + 섹터/테마 ETF.

확장: 새 fetch 메서드는 _resolve_kr() 같은 헬퍼 재사용.
"""
import re
from datetime import datetime
from typing import Optional

from cachetools import TTLCache

from app.config import Settings, get_settings
from app.core.constants import PERIOD_CONFIG, SECTOR_DEFS, THEME_ETF_MAP


_TICKER_RE = re.compile(r"^[A-Z]{1,6}(\.[A-Z]+)?$")


def is_global_ticker(query: str) -> bool:
    """영문 대문자 1~6자(.확장)면 글로벌 ticker로 간주."""
    return bool(_TICKER_RE.match(query.strip()))


class YFinanceClient:
    """yfinance import 한 곳에서 처리. 기능별 메서드로 분리."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        try:
            import yfinance as yf
            self._yf = yf
        except Exception:
            self._yf = None
        self._info_cache = TTLCache(maxsize=64, ttl=self._settings.cache_ttl_yfinance)
        self._news_cache = TTLCache(maxsize=64, ttl=self._settings.cache_ttl_yfinance)
        self._sector_cache = TTLCache(maxsize=64, ttl=self._settings.cache_ttl_sectors)
        self._kr_cache = TTLCache(maxsize=128, ttl=self._settings.cache_ttl_briefing)

    @property
    def available(self) -> bool:
        return self._yf is not None

    # ── 글로벌 종목 (NVDA, AAPL 등) ────────────────────────
    def get_global_info(self, ticker: str) -> Optional[dict]:
        if not self.available:
            return None
        if ticker in self._info_cache:
            return self._info_cache[ticker]
        try:
            t = self._yf.Ticker(ticker)
            info = t.info
            if not info or not info.get("shortName"):
                return None
            out = {
                "ticker": ticker,
                "name": info.get("longName") or info.get("shortName"),
                "short_name": info.get("shortName"),
                "exchange": info.get("exchange"),
                "currency": info.get("currency"),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "change_pct": info.get("regularMarketChangePercent"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "summary": (info.get("longBusinessSummary") or "")[:500],
            }
            self._info_cache[ticker] = out
            return out
        except Exception:
            return None

    def get_global_news(self, ticker: str, limit: int = 15) -> list:
        if not self.available:
            return []
        if ticker in self._news_cache:
            return self._news_cache[ticker][:limit]
        try:
            t = self._yf.Ticker(ticker)
            raw = t.news or []
        except Exception:
            return []
        items = []
        for n in raw[:30]:
            content = n.get("content") or n
            title = content.get("title") or n.get("title", "")
            publisher = (content.get("provider") or {}).get("displayName") or n.get("publisher", "")
            pub_dt = content.get("pubDate") or n.get("providerPublishTime")
            if isinstance(pub_dt, (int, float)):
                try:
                    date_str = datetime.fromtimestamp(pub_dt).strftime("%Y.%m.%d %H:%M")
                except Exception:
                    date_str = ""
            elif isinstance(pub_dt, str):
                date_str = pub_dt[:16].replace("T", " ")
            else:
                date_str = ""
            link = (
                (content.get("canonicalUrl") or {}).get("url")
                or content.get("clickThroughUrl", {}).get("url")
                or n.get("link", "")
            )
            if not title:
                continue
            items.append({
                "title": title, "source": publisher, "time": date_str,
                "link": link, "summary": (content.get("summary") or "")[:200],
            })
        self._news_cache[ticker] = items
        return items[:limit]

    # ── 한국 종목 (yfinance fallback) ─────────────────────
    def get_kr_info(self, stock_code: str) -> dict:
        if not stock_code or not stock_code.isdigit() or not self.available:
            return {}
        if stock_code in self._kr_cache:
            return self._kr_cache[stock_code]
        out: dict = {}
        for suffix in (".KS", ".KQ"):
            try:
                t = self._yf.Ticker(f"{stock_code}{suffix}")
                info = t.info
                if info and (info.get("currentPrice") or info.get("regularMarketPrice")):
                    out = {
                        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                        "change_pct": info.get("regularMarketChangePercent"),
                        "per": info.get("trailingPE"),
                        "pbr": info.get("priceToBook"),
                        "high_52w": info.get("fiftyTwoWeekHigh"),
                        "low_52w": info.get("fiftyTwoWeekLow"),
                        "market_cap": info.get("marketCap"),
                        "currency": info.get("currency"),
                    }
                    break
            except Exception:
                continue
        self._kr_cache[stock_code] = out
        return out

    # ── 섹터 ETF ──────────────────────────────────────────
    def fetch_sector(self, sector_id: str, period_key: str = "daily") -> Optional[dict]:
        if sector_id not in SECTOR_DEFS or not self.available:
            return None
        pc = PERIOD_CONFIG.get(period_key, PERIOD_CONFIG["daily"])
        key = f"sec:{sector_id}:{period_key}"
        if key in self._sector_cache:
            return self._sector_cache[key]

        s = SECTOR_DEFS[sector_id]
        ticker = s["ticker"]
        try:
            t = self._yf.Ticker(ticker)
            info = t.info
            if not info or not (info.get("regularMarketPrice") or info.get("currentPrice")):
                return None
            hist = t.history(period=pc["period"], interval=pc["interval"])
            if hist.empty:
                return None
        except Exception:
            return None

        closes = [round(v, 2) for v in hist["Close"].tolist()]
        price = closes[-1] if closes else None
        if period_key == "yearly":
            ref = closes[-13] if len(closes) >= 13 else (closes[0] if closes else price)
        else:
            ref = closes[-2] if len(closes) >= 2 else price
        change_pct = ((price - ref) / ref * 100) if ref else 0

        out = {
            "id": sector_id, "name": s["name"], "icon": s["icon"], "color": s["color"],
            "ticker": ticker, "subtitle": s["subtitle"], "summary_query": s["summary_query"],
            "price": price, "change": round(change_pct, 2),
            "high_3mo": max(closes) if closes else None,
            "low_3mo": min(closes) if closes else None,
            "chart": closes, "period_key": period_key, "period_label": pc["label"],
            "currency": info.get("currency", "KRW"),
        }
        self._sector_cache[key] = out
        return out

    def fetch_all_sectors(self) -> list:
        key = "sec:all"
        if key in self._sector_cache:
            return self._sector_cache[key]
        out = []
        for sid in SECTOR_DEFS:
            s = self.fetch_sector(sid)
            if s:
                out.append(s)
        self._sector_cache[key] = out
        return out

    # ── 테마 ETF ──────────────────────────────────────────
    def fetch_theme(self, keyword: str) -> Optional[dict]:
        if not self.available:
            return None
        ticker = THEME_ETF_MAP.get(keyword.strip())
        if not ticker:
            return None
        key = f"theme:{keyword}"
        if key in self._sector_cache:
            return self._sector_cache[key]
        try:
            t = self._yf.Ticker(ticker)
            info = t.info
            if not info or not (info.get("regularMarketPrice") or info.get("currentPrice")):
                return None
            hist = t.history(period="1mo", interval="1d")
            if hist.empty:
                return None
        except Exception:
            return None

        closes = [round(v, 2) for v in hist["Close"].tolist()]
        price = closes[-1] if closes else None
        prev = closes[-2] if len(closes) >= 2 else price
        change = ((price - prev) / prev * 100) if prev else 0
        out = {
            "ticker": ticker,
            "etf_name": info.get("shortName") or info.get("longName"),
            "price": price, "change": round(change, 2),
            "chart": closes[-30:],
        }
        self._sector_cache[key] = out
        return out
