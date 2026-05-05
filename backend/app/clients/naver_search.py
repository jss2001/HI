"""Naver Search API — news / blog / cafearticle 통합 클라이언트.

확장: 새 검색 타입 → search() endpoint 인자에 ('shop', 'webkr' 등) 추가.
"""
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from cachetools import TTLCache

from app.config import Settings, get_settings


_HTML_RE = re.compile(r"<[^>]+>")
_ENTITY_MAP = {"&quot;": '"', "&amp;": "&", "&apos;": "'", "&lt;": "<", "&gt;": ">", "&#39;": "'"}


def _strip_html(text: str) -> str:
    s = _HTML_RE.sub("", text or "")
    for k, v in _ENTITY_MAP.items():
        s = s.replace(k, v)
    return s.strip()


def _format_pub(pub_date: str) -> tuple:
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
    except Exception:
        return "기타", pub_date or "", ""
    now = datetime.now(dt.tzinfo)
    delta = (now.date() - dt.date()).days
    if delta <= 0:
        label = "오늘"
    elif delta == 1:
        label = "어제"
    elif delta < 7:
        label = f"{delta}일 전"
    else:
        label = dt.strftime("%Y.%m.%d")
    return label, dt.strftime("%Y.%m.%d %H:%M"), dt.isoformat()


# 매체명 매핑 — 도메인 → 한국어 매체명
OUTLET_BY_HOSTNAME: dict = {
    "biz.chosun.com": "조선비즈", "biz.heraldcorp.com": "헤럴드경제",
    "biz.sbs.co.kr": "SBS Biz", "news.naver.com": "네이버뉴스", "n.news.naver.com": "네이버뉴스",
    "news.einfomax.co.kr": "연합인포맥스", "news.mt.co.kr": "머니투데이",
    "weekly.chosun.com": "주간조선", "monthly.chosun.com": "월간조선",
    "weekly.donga.com": "주간동아", "shindonga.donga.com": "신동아",
    "it.chosun.com": "IT조선", "stock.mk.co.kr": "매일경제", "vip.mk.co.kr": "매일경제",
    "sports.donga.com": "스포츠동아", "sports.chosun.com": "스포츠조선",
    "newsroom.kbs.co.kr": "KBS뉴스", "imnews.imbc.com": "MBC뉴스",
}

OUTLET_BY_STEM: dict = {
    "chosun": "조선일보", "joongang": "중앙일보", "joins": "중앙일보",
    "donga": "동아일보", "hani": "한겨레", "khan": "경향신문",
    "hankookilbo": "한국일보", "kmib": "국민일보", "munhwa": "문화일보",
    "segye": "세계일보", "seoul": "서울신문", "naeil": "내일신문",
    "mk": "매일경제", "hankyung": "한국경제", "mt": "머니투데이",
    "edaily": "이데일리", "sedaily": "서울경제", "ajunews": "아주경제",
    "fnnews": "파이낸셜뉴스", "asiae": "아시아경제", "asiatoday": "아시아투데이",
    "moneys": "머니S", "thebell": "더벨", "ebn": "EBN", "viva100": "브릿지경제",
    "businesspost": "비즈니스포스트", "businesskorea": "비즈니스코리아", "biztribune": "비즈트리뷴",
    "thefairnews": "공정뉴스", "todayenergy": "투데이에너지", "energydaily": "에너지데일리",
    "g-enews": "글로벌이코노믹",
    "yna": "연합뉴스", "yonhapnews": "연합뉴스", "yonhapnewstv": "연합뉴스TV",
    "newsis": "뉴시스", "news1": "뉴스1", "newspim": "뉴스핌",
    "ytn": "YTN", "imbc": "MBC", "sbs": "SBS", "kbs": "KBS",
    "jtbc": "JTBC", "mbn": "MBN", "channela": "채널A", "tvchosun": "TV조선",
    "zdnet": "ZDNet코리아", "bloter": "블로터", "inews24": "아이뉴스24",
    "digitaltoday": "디지털투데이", "ddaily": "디지털데일리",
    "etnews": "전자신문", "theelec": "디일렉",
    "heraldcorp": "헤럴드경제", "heraldbiz": "헤럴드경제",
    "wikitree": "위키트리", "newsway": "뉴스웨이", "newsprime": "뉴스프라임",
    "topdaily": "톱데일리", "todaykorea": "투데이코리아",
    "mediapen": "미디어펜", "womaneconomy": "여성경제신문",
    "theviewers": "더뷰어스", "view": "뷰어스",
    "newsen": "뉴스엔", "mydaily": "마이데일리", "newdaily": "뉴데일리",
    "sisajournal": "시사저널", "sisaweek": "시사위크", "viewsnnews": "뷰스앤뉴스",
    "nocutnews": "노컷뉴스", "ohmynews": "오마이뉴스", "pressian": "프레시안",
    "ilyo": "일요신문", "ilyoseoul": "일요서울",
    "tokenpost": "토큰포스트", "blockmedia": "블록미디어",
    "coindeskkorea": "코인데스크코리아", "blockchaintoday": "블록체인투데이",
    "cbci": "차이나비즈니스", "koreaherald": "코리아헤럴드", "koreatimes": "코리아타임스",
    "tf": "더팩트", "aitimes": "AI타임스", "getnews": "겟뉴스",
    "news2day": "뉴스투데이", "choicenews": "초이스경제", "newsworks": "뉴스웍스",
    "etoday": "이투데이", "skyedaily": "스카이데일리", "newscj": "천지일보",
    "infostockdaily": "인포스탁데일리", "stockdaily": "스탁데일리",
    "dailian": "데일리안", "kbsm": "한국금융신문", "fntimes": "한국금융신문",
    "ekn": "에너지경제", "ekoreanews": "이코리아",
    "ilyosisa": "일요시사", "weeklyhk": "주간한국",
    "naver": "네이버뉴스",
}

MAJOR_OUTLETS = {
    "조선일보", "중앙일보", "동아일보", "한겨레", "경향신문", "한국일보",
    "매일경제", "한국경제", "머니투데이", "이데일리", "서울경제", "파이낸셜뉴스",
    "아시아경제", "헤럴드경제", "조선비즈", "연합뉴스", "연합인포맥스",
    "뉴시스", "뉴스1", "뉴스핌", "YTN", "MBC", "SBS", "KBS", "JTBC",
    "MBN", "TV조선", "전자신문",
}

_TLD_SUFFIXES = (".co.kr", ".or.kr", ".go.kr", ".re.kr", ".ne.kr", ".pe.kr",
                 ".com", ".net", ".org", ".io", ".kr")


def _domain_stem(host: str) -> str:
    h = host[4:] if host.startswith("www.") else host
    for suf in _TLD_SUFFIXES:
        if h.endswith(suf):
            h = h[: -len(suf)]
            break
    return h.split(".")[-1]


def _outlet_name(link: str) -> str:
    try:
        host = (urlparse(link).hostname or "").lower()
        if not host:
            return "뉴스"
        host_clean = host[4:] if host.startswith("www.") else host
        if host_clean in OUTLET_BY_HOSTNAME:
            return OUTLET_BY_HOSTNAME[host_clean]
        return OUTLET_BY_STEM.get(_domain_stem(host_clean), _domain_stem(host_clean))
    except Exception:
        return "뉴스"


class NaverSearchClient:
    """Naver OpenAPI search — news / blog / cafearticle.

    인스턴스마다 독립 캐시. settings를 안 넘기면 전역 settings 사용.
    """

    BASE = "https://openapi.naver.com/v1/search"

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self._cache_news = TTLCache(
            maxsize=self._settings.cache_max_size_default, ttl=300
        )
        self._cache_buzz = TTLCache(
            maxsize=self._settings.cache_max_size_default, ttl=self._settings.cache_ttl_briefing
        )

    @property
    def available(self) -> bool:
        return bool(self._settings.naver_client_id and self._settings.naver_client_secret)

    @property
    def headers(self) -> dict:
        return {
            "X-Naver-Client-Id": self._settings.naver_client_id,
            "X-Naver-Client-Secret": self._settings.naver_client_secret,
        }

    async def search_news(
        self,
        client: httpx.AsyncClient,
        query: str,
        display: int,
        tag: Optional[str] = None,
    ) -> list:
        """news.json 검색 + 우리 표준 형식으로 변환."""
        cache_key = f"news:{tag or query}:{display}"
        if cache_key in self._cache_news:
            return self._cache_news[cache_key]
        if not self.available:
            return []

        try:
            r = await client.get(
                f"{self.BASE}/news.json",
                params={"query": query, "display": display, "sort": "date"},
                headers=self.headers,
            )
            r.raise_for_status()
            items = r.json().get("items", [])
        except Exception:
            return []

        out = []
        for it in items:
            link = it.get("originallink") or it.get("link") or ""
            date_label, time_str, iso = _format_pub(it.get("pubDate", ""))
            out.append({
                "id": hashlib.md5(link.encode()).hexdigest()[:10],
                "date": date_label,
                "time": time_str,
                "_iso": iso,
                "tag": tag or query,
                "title": _strip_html(it.get("title", "")),
                "summary": _strip_html(it.get("description", "")),
                "source": _outlet_name(link),
                "link": link,
            })
        self._cache_news[cache_key] = out
        return out

    async def search_buzz(
        self, client: httpx.AsyncClient, endpoint: str, query: str, display: int = 50,
    ) -> list:
        """blog 또는 cafearticle 원본 raw items. 가공은 호출자(SocialService)가."""
        if not self.available:
            return []
        try:
            r = await client.get(
                f"{self.BASE}/{endpoint}.json",
                params={"query": query, "display": display, "sort": "date"},
                headers=self.headers,
            )
            if r.status_code != 200:
                return []
            return r.json().get("items", [])
        except Exception:
            return []
