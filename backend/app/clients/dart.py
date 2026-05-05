"""DART OpenAPI — corp_code 매핑 + 공시 목록 + 종목 검색.

확장: 새 별칭 → ALIASES에 추가. 새 공시 카테고리 → REPORT_LABELS에 추가.
"""
import io
import zipfile
from datetime import datetime, timedelta
from typing import Optional
from xml.etree import ElementTree as ET

import httpx
from cachetools import TTLCache

from app.config import Settings, get_settings


# 흔한 약칭 → 정식 회사명
ALIASES: dict = {
    "현대차": "현대자동차", "기아차": "기아", "삼전": "삼성전자", "삼바": "삼성바이오로직스",
    "하닉": "SK하이닉스", "SK하닉": "SK하이닉스", "LG엔솔": "LG에너지솔루션",
    "엘지엔솔": "LG에너지솔루션", "엘앤에프": "엘앤에프", "카뱅": "카카오뱅크",
    "케뱅": "케이뱅크", "한전": "한국전력공사", "셀트리": "셀트리온",
    "한미반": "한미반도체", "이오테크": "이오테크닉스", "에코프로": "에코프로",
    "LG화": "LG화학", "LG생건": "LG생활건강", "LG디플": "LG디스플레이",
    "포스코": "POSCO홀딩스", "포스코홀딩스": "POSCO홀딩스",
    "신한": "신한지주", "KB": "KB금융", "우리": "우리금융지주", "하나": "하나금융지주",
    "두산": "두산", "한화": "한화", "네이버": "NAVER", "다음": "카카오",
}


REPORT_LABELS: dict = {
    "A": "정기공시", "B": "주요사항보고", "C": "발행공시",
    "D": "지분공시", "E": "기타공시", "F": "외부감사관련",
    "G": "펀드공시", "H": "자산유동화", "I": "거래소공시", "J": "공정위공시",
}


class DartClient:
    """corp_code 캐시(24h) + 공시 목록 캐시(15분). 검색 헬퍼 포함."""

    BASE = "https://opendart.fss.or.kr/api"

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self._corp_cache = TTLCache(maxsize=1, ttl=24 * 3600)
        self._filings_cache = TTLCache(maxsize=128, ttl=15 * 60)

    @property
    def available(self) -> bool:
        return bool(self._settings.dart_api_key)

    # ── corp 검색 ──────────────────────────────────
    def _load_corps(self) -> list:
        if "corp" in self._corp_cache:
            return self._corp_cache["corp"]
        if not self.available:
            return []
        url = f"{self.BASE}/corpCode.xml"
        r = httpx.get(url, params={"crtfc_key": self._settings.dart_api_key},
                      timeout=self._settings.http_timeout_dart)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            with zf.open(zf.namelist()[0]) as f:
                tree = ET.parse(f)
        corps = []
        for el in tree.getroot().findall("list"):
            sc = (el.findtext("stock_code") or "").strip()
            if not sc:
                continue
            corps.append({
                "corp_code": el.findtext("corp_code", "").strip(),
                "corp_name": el.findtext("corp_name", "").strip(),
                "stock_code": sc,
            })
        self._corp_cache["corp"] = corps
        return corps

    def search(self, query: str, limit: int = 8) -> list:
        """자동완성 — 정확 → prefix → substring 우선순위."""
        corps = self._load_corps()
        q = (query or "").strip()
        if not q:
            return []
        q = ALIASES.get(q, q)

        matches = []
        for c in corps:
            sc, nm = c.get("stock_code", ""), c.get("corp_name", "")
            if not sc:
                continue
            if sc == q:
                matches.append((0, c))
            elif nm == q:
                matches.append((1, c))
            elif sc.startswith(q):
                matches.append((2, c))
            elif nm.startswith(q):
                matches.append((3, c))
            elif q in nm:
                matches.append((4, c))
        matches.sort(key=lambda x: (x[0], len(x[1].get("corp_name", ""))))
        return [
            {"stock_code": c["stock_code"], "corp_name": c["corp_name"]}
            for _, c in matches[:limit]
        ]

    def find(self, query: str) -> Optional[dict]:
        """단일 회사 매칭 — 별칭 → 종목코드 → 이름 → prefix → substring."""
        corps = self._load_corps()
        q = ALIASES.get(query.strip(), query.strip())
        for c in corps:
            if c["stock_code"] == q:
                return c
        for c in corps:
            if c["corp_name"] == q:
                return c
        prefix = sorted(
            [c for c in corps if c["corp_name"].startswith(q)],
            key=lambda c: (len(c["corp_name"]), c["stock_code"]),
        )
        if prefix:
            return prefix[0]
        sub = sorted(
            [c for c in corps if q in c["corp_name"]],
            key=lambda c: (len(c["corp_name"]), c["stock_code"]),
        )
        return sub[0] if sub else None

    def find_similar_names(self, prefix: str, exclude: Optional[str] = None) -> list:
        return [
            c["corp_name"] for c in self._load_corps()
            if c["corp_name"].startswith(prefix) and c["corp_name"] != exclude
        ]

    @staticmethod
    def aliases_for(corp_name: str) -> list:
        return [a for a, full in ALIASES.items() if full == corp_name]

    # ── 공시 ──────────────────────────────────────
    async def get_filings(self, corp_code: str, days: int = 7, limit: int = 30) -> list:
        key = f"filings:{corp_code}:{days}"
        if key in self._filings_cache:
            return self._filings_cache[key]
        if not self.available:
            return []

        end = datetime.now()
        start = end - timedelta(days=days)
        params = {
            "crtfc_key": self._settings.dart_api_key,
            "corp_code": corp_code,
            "bgn_de": start.strftime("%Y%m%d"),
            "end_de": end.strftime("%Y%m%d"),
            "page_count": limit,
        }
        async with httpx.AsyncClient(timeout=self._settings.http_timeout_market) as client:
            try:
                r = await client.get(f"{self.BASE}/list.json", params=params)
                r.raise_for_status()
                d = r.json()
            except Exception:
                return []
        if d.get("status") != "000":
            return []

        items = []
        for it in d.get("list", []):
            date_str = it.get("rcept_dt", "")
            try:
                date_fmt = datetime.strptime(date_str, "%Y%m%d").strftime("%Y.%m.%d")
            except Exception:
                date_fmt = date_str
            items.append({
                "rcept_no": it.get("rcept_no", ""),
                "report_nm": it.get("report_nm", "").strip(),
                "date": date_fmt,
                "submitter": it.get("flr_nm", ""),
                "category": REPORT_LABELS.get(it.get("rcept_no", "")[:1], "기타"),
                "link": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={it.get('rcept_no', '')}",
            })
        self._filings_cache[key] = items
        return items
