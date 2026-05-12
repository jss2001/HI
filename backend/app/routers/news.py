"""뉴스 — 섹터 태그 또는 사용자 커스텀 키워드."""
import asyncio
from typing import Optional

import httpx
from fastapi import APIRouter, Depends

from app.config import get_settings
from app.core.mock import NEWS_MOCK
from app.dependencies import (
    get_keyword_refiner, get_news_classifier, get_news_service,
)
from app.services.keyword_refiner import KeywordRefiner
from app.services.news import NewsService, SECTOR_TAGS
from app.services.news_classifier import NewsClassifier


US_NEWS_TAGS = ["지수", "빅테크", "AI/반도체", "전기차", "금융", "에너지", "헬스"]

US_NEWS_QUERIES: dict = {
    "지수":      ["S&P 500", "나스닥 지수", "다우 지수"],
    "빅테크":    ["애플 주가", "마이크로소프트 주가", "구글 주가", "메타 주가"],
    "AI/반도체": ["엔비디아 주가", "TSMC 주가", "AMD 주가"],
    "전기차":    ["테슬라 주가", "리비안 전기차"],
    "금융":      ["JP모건 미국 은행", "골드만삭스 주가"],
    "에너지":    ["엑손모빌 미국 유가", "셰브론 주가"],
    "헬스":      ["일라이릴리 주가", "화이자 주가"],
}


router = APIRouter()


def _mock_news(tag: Optional[str]):
    items = NEWS_MOCK if not tag else [n for n in NEWS_MOCK if n["tag"] == tag]
    grouped: dict = {}
    for n in items:
        grouped.setdefault(n["date"], []).append(n)
    return {
        "groups": [{"date": d, "items": grouped[d]} for d in grouped],
        "tags": sorted({n["tag"] for n in NEWS_MOCK}),
        "source": "mock",
    }


@router.get("/api/news")
async def list_news(
    tag: Optional[str] = None,
    market: str = "kr",
    news: NewsService = Depends(get_news_service),
    refiner: KeywordRefiner = Depends(get_keyword_refiner),
    classifier: NewsClassifier = Depends(get_news_classifier),
):
    # US 마켓 모드 — 네이버 한국어 검색으로 미장 종목/지수 뉴스
    if market == "us":
        if tag and tag in US_NEWS_QUERIES:
            pairs = [(tag, q) for q in US_NEWS_QUERIES[tag]]
        else:
            pairs = [(cat, q) for cat, qs in US_NEWS_QUERIES.items() for q in qs]
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.http_timeout_naver_news) as c:
            tasks = [news._naver.search_news(c, q, 12, tag=cat) for cat, q in pairs]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        merged: list = []
        seen: set = set()
        for items in results:
            if isinstance(items, Exception):
                continue
            for it in items:
                link = it.get("link")
                if not link or link in seen:
                    continue
                seen.add(link)
                merged.append(it)
        merged.sort(key=lambda x: x.get("_iso", ""), reverse=True)
        merged = merged[:60]
        grouped: dict = {}
        for n in merged:
            grouped.setdefault(n["date"], []).append(
                {k: v for k, v in n.items() if not k.startswith("_")}
            )
        order = {"오늘": 0, "어제": 1}
        ordered = sorted(grouped.keys(), key=lambda d: (order.get(d, 2), d))
        return {
            "groups": [{"date": d, "items": grouped[d]} for d in ordered],
            "tags": US_NEWS_TAGS,
            "source": "naver",
            "market": "us",
        }

    # 커스텀 키워드 (sector tag 아님) → LLM refine 파이프라인
    if tag and tag not in SECTOR_TAGS:
        try:
            pipeline = await news.fetch_with_refinement(
                tag, refiner, classifier, period_target=8, classify_max=20,
            )
            grouped: dict = {}
            for n in pipeline["items"][:30]:
                n["tag"] = tag
                grouped.setdefault(n["date"], []).append(
                    {k: v for k, v in n.items() if not k.startswith("_")}
                )
            order = {"오늘": 0, "어제": 1}
            ordered = sorted(grouped.keys(), key=lambda d: (order.get(d, 2), d))
            return {
                "groups": [{"date": d, "items": grouped[d]} for d in ordered],
                "tags": SECTOR_TAGS,
                "source": "naver+llm",
                "period": pipeline["period"],
                "refined": pipeline["refined"],
            }
        except Exception:
            pass

    live = await news.fetch_for_tag(tag)
    if live and live.get("groups"):
        return live
    return _mock_news(tag)
