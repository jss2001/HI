"""사용자 정의 테마."""
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_theme_service
from app.services.theme import ThemeService


router = APIRouter()


@router.get("/api/themes")
async def theme(keyword: str, svc: ThemeService = Depends(get_theme_service)):
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="keyword required")
    return await svc.fetch(keyword)
