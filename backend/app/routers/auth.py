"""Auth 체크 + health."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import get_settings


router = APIRouter()


@router.get("/")
def root():
    return {"service": "HI", "ok": True}


@router.get("/api/auth/check")
def auth_check(token: str = ""):
    """프론트엔드 첫 호출 시 비밀번호 검증."""
    s = get_settings()
    if not s.app_token:
        return {"ok": True, "auth_required": False}
    if token == s.app_token:
        return {"ok": True, "auth_required": True}
    return JSONResponse({"ok": False, "auth_required": True}, status_code=401)
