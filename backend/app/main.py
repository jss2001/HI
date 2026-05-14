"""FastAPI 진입점 — 라우터 등록, 토큰 미들웨어, CORS, 정적 프론트엔드 서빙.

확장: 새 엔드포인트 → app/routers/에 모듈 추가 후 아래 include_router에 등록.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import (
    analyst, auth, briefing, news, search, sectors, themes, usage, exchange
)


# 빌드된 Vite 정적 파일 위치 (Dockerfile에서 /app/static으로 복사)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# ── 보호받지 않는 경로 (APP_TOKEN 미들웨어 우회) ───────────
PUBLIC_API_PATHS = frozenset({
    "/api/health",
    "/api/auth/check",
    "/api/usage",
})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="HI · 딸깍 API", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def token_gate(request: Request, call_next):
        token = settings.app_token
        # 토큰 미설정 = 로컬 개발, 그냥 통과
        if not token:
            return await call_next(request)
        path = request.url.path
        # /api/* 만 보호. 정적/HTML 통과
        if not path.startswith("/api"):
            return await call_next(request)
        if path in PUBLIC_API_PATHS:
            return await call_next(request)
        provided = request.headers.get("X-App-Token") or request.query_params.get("token")
        if provided != token:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)

    # 라우터 등록 — 새 라우터는 여기에 추가
    app.include_router(auth.router)
    app.include_router(usage.router)
    app.include_router(sectors.router)
    app.include_router(news.router)
    app.include_router(search.router)
    app.include_router(briefing.router)
    app.include_router(analyst.router)
    app.include_router(themes.router)
    app.include_router(exchange.router)

    # 빌드된 Vite 프론트엔드 정적 서빙 (Docker 빌드 시에만 존재).
    # API 라우터 등록 뒤에 마운트해야 /api/* 가 우선 매칭됨.
    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()
