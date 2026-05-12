"""섹터 시세 + 섹터 상세 (관련 뉴스 포함)."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.mock import SECTOR_DETAILS_MOCK, SECTORS_MOCK
from app.dependencies import (
    get_keyword_refiner, get_news_classifier, get_news_service, get_sector_service,
)
from app.services.keyword_refiner import KeywordRefiner
from app.services.news import NewsService
from app.services.news_classifier import NewsClassifier
from app.services.sector import SectorService


router = APIRouter()


@router.get("/api/sectors")
def list_sectors(
    market: str = "kr",
    svc: SectorService = Depends(get_sector_service),
):
    live = svc.fetch_all(market=market)
    if live:
        all_sectors = [
            {"id": s["id"], "name": s["name"], "icon": s["icon"], "color": s["color"],
             "change": s["change"], "price": s["price"], "summary": s["subtitle"],
             "currency": s.get("currency", "KRW")}
            for s in live
        ]
        hot = sorted(all_sectors, key=lambda s: abs(s["change"]), reverse=True)[:3]
        return {"hot": hot, "all": all_sectors, "source": "yfinance", "market": market}

    if market == "us":
        return {"hot": [], "all": [], "source": "yfinance", "market": "us"}
    hot = sorted(SECTORS_MOCK, key=lambda s: abs(s["change"]), reverse=True)[:3]
    return {"hot": hot, "all": SECTORS_MOCK, "source": "mock", "market": "kr"}


@router.get("/api/sectors/{sector_id}")
async def get_sector(
    sector_id: str,
    period: str = "daily",
    market: str = "kr",
    svc: SectorService = Depends(get_sector_service),
    news: NewsService = Depends(get_news_service),
    refiner: KeywordRefiner = Depends(get_keyword_refiner),
    classifier: NewsClassifier = Depends(get_news_classifier),
):
    sec = svc.fetch(sector_id, period_key=period, market=market)
    if sec:
        related_news = []
        sector_news_period = None
        try:
            pipeline = await news.fetch_with_refinement(
                sec["name"], refiner, classifier, period_target=5, classify_max=10
            )
            sector_news_period = pipeline["period"]
            related_news = [
                {"id": it["id"], "user": it["source"], "time": it["time"],
                 "text": it["title"], "link": it["link"], "kind": "news"}
                for it in pipeline["items"][:8]
            ]
        except Exception:
            pass
        return {
            "id": sec["id"], "name": sec["name"], "icon": sec["icon"], "color": sec["color"],
            "ticker": sec["ticker"], "subtitle": sec["subtitle"],
            "starred": sec["id"] == "semiconductor",
            "change": sec["change"], "price": sec["price"],
            "high_3mo": sec["high_3mo"], "low_3mo": sec["low_3mo"],
            "chart": sec["chart"],
            "period_key": sec.get("period_key", "daily"),
            "period_label": sec.get("period_label", ""),
            "currency": sec.get("currency", "KRW"),
            "summary": sec["subtitle"],
            "comments": related_news,
            "news_period": sector_news_period,
            "source": "yfinance+naver",
        }

    detail = SECTOR_DETAILS_MOCK.get(sector_id)
    if not detail:
        raise HTTPException(status_code=404, detail="sector not found")
    return detail
