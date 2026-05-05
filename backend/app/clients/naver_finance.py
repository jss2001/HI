"""네이버 금융 종목 페이지 크롤링 — 외인/기관 매매, PER/PBR, 컨센서스, 공매도.

비공식 크롤링이라 차단 위험 → 강한 캐싱 + UA 위장.
확장: 새 시그널은 fetch_main()에서 정규식 추가.
"""
import re
from typing import Optional

import httpx
from cachetools import TTLCache

from app.config import Settings, get_settings


_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36"


def _to_int(s: str) -> Optional[int]:
    try:
        return int(s.replace(",", "").replace("+", "").strip())
    except Exception:
        return None


def _to_float(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", "").strip())
    except Exception:
        return None


class NaverFinanceClient:
    """네이버 금융 종목 페이지 크롤러. 인스턴스 캐시."""

    BASE = "https://finance.naver.com"

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self._cache = TTLCache(
            maxsize=128, ttl=self._settings.cache_ttl_briefing
        )

    async def fetch_main(self, stock_code: str) -> dict:
        """item/main — 현재가/PER/PBR/컨센서스/52주 + 외인 보유율."""
        if not stock_code or not stock_code.isdigit():
            return {}
        key = f"nf_main:{stock_code}"
        if key in self._cache:
            return self._cache[key]

        url = f"{self.BASE}/item/main.naver?code={stock_code}"
        out: dict = {}
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.http_timeout_market, headers={"User-Agent": _UA}
            ) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    return {}
                html = r.content.decode("euc-kr", errors="ignore")
        except Exception:
            return {}

        m = re.search(r'<dd class="no_today"><span class="blind">현재가</span>[^<]*<span class="blind">([\d,]+)</span>', html)
        if m:
            out["price"] = _to_int(m.group(1))

        m2 = re.search(r'<dd>전일대비</dd>\s*<dd[^>]*>(\-?[\d,\.]+)\s*([\-\+]?[\d\.]+)%', html)
        if m2:
            out["change"] = _to_float(m2.group(1))
            out["change_pct"] = _to_float(m2.group(2))

        m = re.search(r'<em id="_market_sum">([\s\S]+?)</em>', html)
        if m:
            out["market_cap_text"] = re.sub(r"[^\d,조억]", "", m.group(1))
        m = re.search(r'<em id="_per">([\d\.\-,]+)</em>', html)
        if m:
            out["per"] = _to_float(m.group(1))
        m = re.search(r'<em id="_pbr">([\d\.\-,]+)</em>', html)
        if m:
            out["pbr"] = _to_float(m.group(1))
        m = re.search(r'<em>([\d,]+)</em>\s*<span class="ng">목표주가', html)
        if m:
            out["target_price"] = _to_int(m.group(1))
        m = re.search(r'52주최고[^<]*</th>\s*<td[^>]*>\s*<em>([\d,]+)</em>', html)
        if m:
            out["high_52w"] = _to_int(m.group(1))
        m = re.search(r'52주최저[^<]*</th>\s*<td[^>]*>\s*<em>([\d,]+)</em>', html)
        if m:
            out["low_52w"] = _to_int(m.group(1))
        m = re.search(r'외국인소진율[^<]*</th>\s*<td[^>]*>\s*<em>([\d\.,]+)</em>', html)
        if m:
            out["foreign_ratio"] = _to_float(m.group(1))

        self._cache[key] = out
        return out

    async def fetch_trading_flow(self, stock_code: str) -> dict:
        """item/frgn — 외인/기관 5일 순매매."""
        if not stock_code or not stock_code.isdigit():
            return {}
        key = f"nf_flow:{stock_code}"
        if key in self._cache:
            return self._cache[key]

        url = f"{self.BASE}/item/frgn.naver?code={stock_code}"
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.http_timeout_market, headers={"User-Agent": _UA}
            ) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    return {}
                html = r.content.decode("euc-kr", errors="ignore")
        except Exception:
            return {}

        rows = re.findall(
            r'<tr[^>]*>\s*<td[^>]*class="tc"[^>]*>(\d{4}\.\d{2}\.\d{2})</td>'
            r'[\s\S]+?<td[^>]*class="num"[^>]*>([\d,]+)</td>'
            r'[\s\S]+?<td[^>]*class="num"[^>]*>(\-?[\d,\.]+%?)</td>'
            r'[\s\S]+?<td[^>]*class="num"[^>]*>([\-\+]?[\d,]+|0)</td>'
            r'[\s\S]+?<td[^>]*class="num"[^>]*>([\-\+]?[\d,]+|0)</td>'
            r'[\s\S]+?<td[^>]*class="num"[^>]*>([\-\+]?[\d,]+|0)</td>',
            html,
        )
        days = []
        for date, close, _chg, _vol, frgn, instn in rows[:5]:
            days.append({
                "date": date, "close": _to_int(close),
                "foreign_net": _to_int(frgn), "institution_net": _to_int(instn),
            })
        if not days:
            return {}
        out = {
            "days": days,
            "foreign_5d_net": sum((d.get("foreign_net") or 0) for d in days),
            "institution_5d_net": sum((d.get("institution_net") or 0) for d in days),
        }
        self._cache[key] = out
        return out

    async def fetch_short_selling(self, stock_code: str) -> dict:
        """item/sise — 공매도 잔고 비중."""
        if not stock_code or not stock_code.isdigit():
            return {}
        key = f"nf_short:{stock_code}"
        if key in self._cache:
            return self._cache[key]

        url = f"{self.BASE}/item/sise.naver?code={stock_code}"
        out: dict = {}
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.http_timeout_market, headers={"User-Agent": _UA}
            ) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    self._cache[key] = out
                    return out
                html = r.content.decode("euc-kr", errors="ignore")
        except Exception:
            self._cache[key] = out
            return out

        m = re.search(r'공매도\s*잔고[^<]*</th>\s*<td[^>]*>\s*([\d\.,]+)\s*%', html)
        if m:
            out["short_ratio_pct"] = _to_float(m.group(1))
        self._cache[key] = out
        return out

    @staticmethod
    def merge(naver: dict, fallback: dict) -> dict:
        """네이버 우선, 빈 값은 fallback(yfinance)로 채움."""
        out = dict(fallback or {})
        for k, v in (naver or {}).items():
            if v is not None:
                out[k] = v
        return out
