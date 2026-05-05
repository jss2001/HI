"""뉴스 — 섹터 태그 또는 사용자 커스텀 키워드."""
from typing import Optional

from fastapi import APIRouter, Depends

from app.core.mock import NEWS_MOCK
from app.dependencies import (
    get_keyword_refiner, get_news_classifier, get_news_service,
)
from app.services.keyword_refiner import KeywordRefiner
from app.services.news import NewsService, SECTOR_TAGS
from app.services.news_classifier import NewsClassifier


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
    news: NewsService = Depends(get_news_service),
    refiner: KeywordRefiner = Depends(get_keyword_refiner),
    classifier: NewsClassifier = Depends(get_news_classifier),
):
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
