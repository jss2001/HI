"""뉴스 서비스 — 섹터/커스텀 키워드 검색, 클러스터링 + hotness 점수.

확장: 새 섹터 추가 → SECTOR_TAGS + SECTOR_QUERY 동시 갱신. (섹터 정의는 core/constants.py와 분리:
core/constants는 ETF 시세용, 여기 query는 뉴스 검색어 매핑.)
"""
import asyncio
import math
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.clients.naver_search import NaverSearchClient, MAJOR_OUTLETS
from app.config import Settings, get_settings
from app.core.relevance import RelevanceFilter


SECTOR_TAGS = ["AI", "반도체", "2차전지", "바이오", "금융", "자동차"]

SECTOR_QUERY = {
    "AI": "AI 반도체 주가",
    "반도체": "반도체 주가",
    "2차전지": "2차전지 전기차 배터리",
    "바이오": "바이오 제약 주가",
    "금융": "은행주 금융주",
    "자동차": "자동차 주가 현대차 기아",
}


_TITLE_PUNCT_RE = re.compile(r"[\[\]\(\)<>《》「」『』\"'·,.…!?\-—~`/:]+")
_STOPWORDS = {"속보", "단독", "종합", "기자", "이슈", "특징주", "마감", "개장",
              "전망", "관련주", "동향", "상승", "하락", "보합", "강세", "약세",
              "오늘", "어제", "내일", "이번", "다음", "최근"}
_PARTICLES_RE = re.compile(r"(은|는|이|가|을|를|에|에서|으로|로|와|과|의|도|만|까지|부터)$")


def _title_tokens(title: str) -> set:
    cleaned = _TITLE_PUNCT_RE.sub(" ", title)
    out = set()
    for w in cleaned.split():
        if len(w) < 2 or w in _STOPWORDS:
            continue
        stripped = _PARTICLES_RE.sub("", w)
        if len(stripped) >= 2 and stripped not in _STOPWORDS:
            out.add(stripped)
    return out


def _hours_since(iso: str) -> float:
    if not iso:
        return 999.0
    try:
        dt = datetime.fromisoformat(iso)
        now = datetime.now(dt.tzinfo or timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 3600)
    except Exception:
        return 999.0


def _cluster_sizes(items: list) -> list:
    """제목 토큰 교집합으로 동일 사건 클러스터링 → 각 아이템의 클러스터 크기 반환."""
    n = len(items)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    tokens = [_title_tokens(it.get("title", "")) for it in items]
    for i in range(n):
        if len(tokens[i]) < 2:
            continue
        for j in range(i + 1, n):
            if len(tokens[j]) < 2:
                continue
            inter = len(tokens[i] & tokens[j])
            if inter == 0:
                continue
            smaller = min(len(tokens[i]), len(tokens[j]))
            if inter >= 3 or inter / smaller >= 0.5:
                union(i, j)

    counts: dict = {}
    for i in range(n):
        r = find(i)
        counts[r] = counts.get(r, 0) + 1
    return [counts[find(i)] for i in range(n)]


def _hotness(item: dict, cluster_size: int) -> float:
    hours = _hours_since(item.get("_iso", ""))
    time_score = math.exp(-hours / 12)
    media_weight = 1.0 if item.get("source") in MAJOR_OUTLETS else 0.75
    return time_score * float(cluster_size) * media_weight


class NewsService:
    """섹터 태그 / 커스텀 키워드 뉴스 검색.

    - sector tag: SECTOR_QUERY 매핑된 검색어로
    - 커스텀: 호출자(라우터)가 keyword_refiner로 정제 후 fetch_one_query 직접 호출
    """

    def __init__(
        self,
        naver: Optional[NaverSearchClient] = None,
        relevance: Optional[RelevanceFilter] = None,
        settings: Optional[Settings] = None,
    ):
        self._naver = naver or NaverSearchClient()
        self._relevance = relevance or RelevanceFilter()
        self._settings = settings or get_settings()

    async def fetch_for_tag(self, tag: Optional[str] = None) -> Optional[dict]:
        """섹터 태그 또는 커스텀 키워드 → 그룹화된 뉴스 응답."""
        if not self._naver.available:
            return None

        if tag and tag in SECTOR_TAGS:
            tags = [tag]
        elif tag:
            tags = [tag]
        else:
            tags = SECTOR_TAGS
        display = 30 if tag else 15

        async with httpx.AsyncClient(timeout=self._settings.http_timeout_naver_news) as c:
            results = await asyncio.gather(*(self._fetch_tag(c, t, display) for t in tags))

        merged, seen = [], set()
        for items in results:
            for it in items:
                if it["link"] in seen:
                    continue
                seen.add(it["link"])
                merged.append(it)

        sizes = _cluster_sizes(merged)
        for it, sz in zip(merged, sizes):
            it["cluster_size"] = sz
            it["is_hot"] = sz >= 3
            it["_score"] = _hotness(it, sz)

        merged.sort(key=lambda x: x.get("_score", 0), reverse=True)
        merged = merged[:25 if tag else 30]

        grouped: dict = {}
        for n in merged:
            grouped.setdefault(n["date"], []).append(
                {k: v for k, v in n.items() if not k.startswith("_")}
            )
        order = {"오늘": 0, "어제": 1}
        ordered = sorted(grouped.keys(), key=lambda d: (order.get(d, 2), d))
        return {
            "groups": [{"date": d, "items": grouped[d]} for d in ordered],
            "tags": SECTOR_TAGS,
            "source": "naver",
        }

    async def _fetch_tag(self, client: httpx.AsyncClient, tag: str, display: int) -> list:
        query = SECTOR_QUERY.get(tag, tag)
        items = await self._naver.search_news(client, query, display, tag=tag)

        if tag in SECTOR_TAGS or tag in SECTOR_QUERY:
            kw = [tag] + (SECTOR_QUERY.get(tag, "") or "").split()
        else:
            kw = [tag]
        return self._relevance.apply(items, kw)

    async def fetch_one_query(
        self, client: httpx.AsyncClient, query: str, display: int = 30
    ) -> list:
        """라우터(custom keyword path)에서 직접 호출용."""
        return await self._naver.search_news(client, query, display, tag=query)

    async def fetch_with_refinement(
        self,
        keyword: str,
        refiner,
        classifier,
        *,
        period_target: int = 5,
        classify_max: int = 12,
        news_display: int = 30,
        stock_display: int = 20,
    ) -> dict:
        """sector detail / custom keyword / theme이 공유하는 파이프라인:
        refiner → 병렬 검색 → 노이즈 필터 → 적응형 기간 → LLM 분류.

        반환: {items, period, refined}
        """
        from app.core.period import PeriodFilter

        refined = await refiner.refine(keyword)
        queries = refined.get("queries", [keyword])[:5]
        stocks = refined.get("stocks", [])[:4]

        async with httpx.AsyncClient(timeout=self._settings.http_timeout_default) as c:
            tasks = [self._naver.search_news(c, q, news_display, tag=keyword) for q in queries]
            tasks += [self._naver.search_news(c, s, stock_display, tag=keyword) for s in stocks]
            results = await asyncio.gather(*tasks)

        all_items = [it for r in results for it in r]
        seen, merged = set(), []
        for it in all_items:
            if it.get("link") in seen:
                continue
            seen.add(it.get("link"))
            merged.append(it)

        match_kw = [keyword] + queries + stocks
        filtered = self._relevance.apply(merged, match_kw)

        period_items, period_label = PeriodFilter(target=period_target).apply(filtered)
        period_items = await classifier.filter(period_items, keyword, max_keep=classify_max)

        return {"items": period_items, "period": period_label, "refined": refined}
