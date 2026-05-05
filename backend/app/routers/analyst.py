"""Bull · Bear · Judge 종합 분석 + 비교."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_analyst_service
from app.services.analyst import AnalystService


router = APIRouter()


@router.get("/api/analyst")
async def analyst(company: str, svc: AnalystService = Depends(get_analyst_service)):
    result = await svc.generate(company)
    if result and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/api/compare")
async def compare(a: str, b: str, svc: AnalystService = Depends(get_analyst_service)):
    brief_a, brief_b = await asyncio.gather(svc.generate(a), svc.generate(b))
    for x, label in ((brief_a, a), (brief_b, b)):
        if x and x.get("error"):
            raise HTTPException(status_code=400, detail=f"{label}: {x['error']}")
    return {"a": brief_a, "b": brief_b}
