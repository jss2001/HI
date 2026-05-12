"""yfinance 통합 클라이언트 — 글로벌 종목 + 한국 종목 fallback + 섹터/테마 ETF.

확장: 새 fetch 메서드는 _resolve_kr() 같은 헬퍼 재사용.
"""
import math
import re
from datetime import datetime
from typing import Optional

from cachetools import TTLCache

from app.config import Settings, get_settings
from app.core.constants import PERIOD_CONFIG, SECTOR_DEFS, THEME_ETF_MAP, sector_defs_for


_TICKER_RE = re.compile(r"^[A-Z]{1,6}(\.[A-Z]+)?$")


def _safe_num(v):
    """NaN/Inf 제거 → JSON 직렬화 가능한 값으로 변환."""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def is_global_ticker(query: str) -> bool:
    """영문 대문자 1~6자(.확장)면 글로벌 ticker로 간주."""
    return bool(_TICKER_RE.match(query.strip()))


# 한국어 검색어 → 미국 티커 / 정식 영문명
# 사용자가 "엔비디아"를 쳤을 때 yfinance Search에 영문으로 전달하기 위함.
US_KR_ALIASES: dict = {
    "엔비디아": "NVIDIA", "엔비디": "NVIDIA",
    "애플": "Apple", "마이크로소프트": "Microsoft", "MS": "Microsoft",
    "테슬라": "Tesla", "구글": "Alphabet", "알파벳": "Alphabet",
    "메타": "Meta Platforms", "페이스북": "Meta Platforms",
    "아마존": "Amazon", "넷플릭스": "Netflix",
    "TSMC": "Taiwan Semiconductor", "티에스엠씨": "Taiwan Semiconductor",
    "AMD": "Advanced Micro Devices", "인텔": "Intel",
    "퀄컴": "Qualcomm", "브로드컴": "Broadcom", "마이크론": "Micron",
    "ASML": "ASML", "어플라이드머티리얼즈": "Applied Materials",
    "JP모건": "JPMorgan Chase", "제이피모건": "JPMorgan Chase",
    "골드만삭스": "Goldman Sachs", "모건스탠리": "Morgan Stanley",
    "뱅크오브아메리카": "Bank of America", "씨티그룹": "Citigroup",
    "비자": "Visa", "마스터카드": "Mastercard",
    "버크셔": "Berkshire Hathaway", "버크셔해서웨이": "Berkshire Hathaway",
    "엑손모빌": "Exxon Mobil", "엑손": "Exxon Mobil",
    "셰브론": "Chevron", "코노코필립스": "ConocoPhillips",
    "일라이릴리": "Eli Lilly", "릴리": "Eli Lilly",
    "화이자": "Pfizer", "존슨앤존슨": "Johnson & Johnson", "J&J": "Johnson & Johnson",
    "머크": "Merck", "애브비": "AbbVie", "노보노디스크": "Novo Nordisk",
    "유나이티드헬스": "UnitedHealth", "유나이티드 헬스": "UnitedHealth",
    "월마트": "Walmart", "코스트코": "Costco", "타겟": "Target",
    "맥도날드": "McDonald's", "스타벅스": "Starbucks", "코카콜라": "Coca-Cola",
    "펩시": "PepsiCo", "P&G": "Procter & Gamble", "프록터": "Procter & Gamble",
    "디즈니": "Walt Disney", "월트디즈니": "Walt Disney",
    "보잉": "Boeing", "캐터필러": "Caterpillar", "디어": "Deere",
    "팔란티어": "Palantir", "스노우플레이크": "Snowflake",
    "오라클": "Oracle", "세일즈포스": "Salesforce", "어도비": "Adobe",
    "쇼피파이": "Shopify", "우버": "Uber", "리프트": "Lyft",
    "리비안": "Rivian", "루시드": "Lucid",
    "코인베이스": "Coinbase", "로빈후드": "Robinhood", "페이팔": "PayPal",
    "스냅": "Snap", "핀터레스트": "Pinterest", "로블록스": "Roblox",
    "에어비앤비": "Airbnb", "도어대시": "DoorDash",
    "스페이스X": "SpaceX",  # private, but include for fallback
    "버라이즌": "Verizon", "AT&T": "AT&T", "T-모바일": "T-Mobile",
    "S&P": "S&P 500", "S&P500": "S&P 500", "에스앤피": "S&P 500",
    "나스닥": "NASDAQ", "다우": "Dow Jones",
}


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

    # ── US 종목 검색 (자동완성) ────────────────────────
    def search_us(self, query: str, limit: int = 8) -> list:
        """yfinance Search → 미국 거래소 종목/ETF 자동완성. 한국어 별칭도 처리."""
        if not self.available:
            return []
        q = (query or "").strip()
        if not q:
            return []
        # 한국어 → 영문 회사명 별칭
        translated = US_KR_ALIASES.get(q, q)
        try:
            s = self._yf.Search(translated, max_results=max(limit * 2, 8))
            quotes = s.quotes or []
        except Exception:
            return []
        out: list = []
        seen: set = set()
        for it in quotes:
            symbol = (it.get("symbol") or "").strip()
            exch = (it.get("exchDisp") or it.get("exchange") or "").upper()
            # 미국 거래소만 (NASDAQ, NYSE, BATS, NMS, NYQ, ASE 등)
            if not symbol or symbol in seen:
                continue
            us_markers = ("NASDAQ", "NYSE", "NMS", "NYQ", "BATS", "ASE", "AMEX", "ARCA", "PCX")
            if not any(m in exch for m in us_markers):
                continue
            seen.add(symbol)
            name = it.get("longname") or it.get("shortname") or symbol
            out.append({
                "stock_code": symbol,
                "corp_name": name,
                "exchange": exch,
                "market": "us",
            })
            if len(out) >= limit:
                break
        return out

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

    # ── US 시장 종합 뉴스 ────────────────────────────────
    US_NEWS_TICKERS = [
        ("NVDA", "AI/반도체"), ("AAPL", "빅테크"), ("MSFT", "빅테크"),
        ("GOOGL", "빅테크"), ("META", "빅테크"), ("AMZN", "빅테크"),
        ("TSLA", "전기차"), ("JPM", "금융"), ("XOM", "에너지"),
        ("UNH", "헬스"), ("^GSPC", "지수"), ("^IXIC", "지수"),
    ]

    def fetch_us_market_news(self, per_ticker: int = 4) -> list:
        """주요 미국 티커별 yfinance 뉴스 → 단일 리스트로 병합."""
        merged: list = []
        seen: set = set()
        for ticker, tag in self.US_NEWS_TICKERS:
            items = self.get_global_news(ticker, limit=per_ticker)
            for n in items:
                link = n.get("link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                # time format from get_global_news: "YYYY.MM.DD HH:MM" or "YYYY-MM-DDTHH:MM"
                raw_time = (n.get("time") or "").strip()
                date_label, iso = self._us_news_bucket(raw_time)
                merged.append({
                    "id": f"us-{abs(hash(link)) % 10_000_000}",
                    "title": n.get("title", ""),
                    "source": n.get("source", ""),
                    "time": raw_time,
                    "link": link,
                    "summary": n.get("summary", ""),
                    "tag": tag,
                    "date": date_label,
                    "_iso": iso,
                    "cluster_size": 1,
                    "is_hot": False,
                })
        merged.sort(key=lambda x: x.get("_iso", ""), reverse=True)
        return merged

    @staticmethod
    def _us_news_bucket(raw: str) -> tuple:
        """raw time → ('오늘'|'어제'|'N일 전'|'기타', iso)."""
        from datetime import datetime as _dt, timezone as _tz
        if not raw:
            return "기타", ""
        norm = raw.replace(".", "-").replace("/", "-").replace(" ", "T")
        try:
            dt = _dt.fromisoformat(norm[:19])
        except Exception:
            try:
                dt = _dt.strptime(raw[:10], "%Y-%m-%d")
            except Exception:
                return "기타", ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_tz.utc)
        now = _dt.now(dt.tzinfo)
        delta = (now.date() - dt.date()).days
        if delta <= 0:
            label = "오늘"
        elif delta == 1:
            label = "어제"
        elif delta < 7:
            label = f"{delta}일 전"
        else:
            label = dt.strftime("%Y-%m-%d")
        return label, dt.isoformat()

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
    def fetch_sector(self, sector_id: str, period_key: str = "daily", market: str = "kr") -> Optional[dict]:
        defs = sector_defs_for(market)
        if sector_id not in defs or not self.available:
            return None
        pc = PERIOD_CONFIG.get(period_key, PERIOD_CONFIG["daily"])
        key = f"sec:{market}:{sector_id}:{period_key}"
        if key in self._sector_cache:
            return self._sector_cache[key]

        s = defs[sector_id]
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

        default_ccy = "USD" if market == "us" else "KRW"
        out = {
            "id": sector_id, "name": s["name"], "icon": s["icon"], "color": s["color"],
            "ticker": ticker, "subtitle": s["subtitle"], "summary_query": s["summary_query"],
            "price": _safe_num(price), "change": _safe_num(round(change_pct, 2)),
            "high_3mo": _safe_num(max(closes) if closes else None),
            "low_3mo": _safe_num(min(closes) if closes else None),
            "chart": [c for c in closes if not (isinstance(c, float) and (math.isnan(c) or math.isinf(c)))],
            "period_key": period_key, "period_label": pc["label"],
            "currency": info.get("currency", default_ccy),
            "market": market,
        }
        self._sector_cache[key] = out
        return out

    def fetch_all_sectors(self, market: str = "kr") -> list:
        key = f"sec:all:{market}"
        if key in self._sector_cache:
            return self._sector_cache[key]
        out = []
        for sid in sector_defs_for(market):
            s = self.fetch_sector(sid, market=market)
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
