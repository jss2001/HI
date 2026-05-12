"""장전·장마감 브리핑."""
from fastapi import APIRouter, Depends

from app.dependencies import get_briefing_service
from app.schemas import BriefingRequest
from app.services.briefing import BriefingService


router = APIRouter()


@router.post("/api/briefing/morning")
async def briefing_morning(
    req: BriefingRequest,
    svc: BriefingService = Depends(get_briefing_service),
):
    portfolio = [p.model_dump() for p in req.portfolio]
    if (req.market or "kr") == "us":
        return await svc.morning_us(portfolio)
    return await svc.morning(portfolio, req.yesterday_hypothesis)


@router.post("/api/briefing/evening")
async def briefing_evening(
    req: BriefingRequest,
    svc: BriefingService = Depends(get_briefing_service),
):
    portfolio = [p.model_dump() for p in req.portfolio]
    if (req.market or "kr") == "us":
        return await svc.evening_us(portfolio)
    return await svc.evening(portfolio, req.today_hypothesis)
