"""중앙 설정 — 시크릿/타이머블 한 곳에서 로드. 의존성 주입은 Depends(get_settings).

확장: 새 외부 API 추가 시 Secrets 섹션에, 매직 넘버는 Tunable 섹션에 추가.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Secrets (커밋 금지, .env 경유) ────────────────────────────
    naver_client_id: str = Field("", alias="NAVER_CLIENT_ID")
    naver_client_secret: str = Field("", alias="NAVER_CLIENT_SECRET")
    dart_api_key: str = Field("", alias="DART_API_KEY")
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    app_token: str = Field("", alias="APP_TOKEN")

    # ── HTTP 타임아웃 ────────────────────────────────────────────
    http_timeout_default: float = 8.0
    http_timeout_naver_news: float = 6.0
    http_timeout_market: float = 10.0
    http_timeout_dart: float = 30.0

    # ── 캐시 TTL (초) ────────────────────────────────────────────
    cache_ttl_briefing: int = 600        # 10분
    cache_ttl_sectors: int = 300         # 5분
    cache_ttl_yfinance: int = 900        # 15분
    cache_ttl_keyword_refine: int = 86400  # 24시간
    cache_ttl_news_classifier: int = 600   # 10분

    cache_max_size_default: int = 64
    cache_max_size_keyword: int = 256

    # ── LLM ──────────────────────────────────────────────────────
    llm_model_default: str = "gpt-4o-mini"
    llm_max_tokens_analyst: int = 3500
    llm_max_tokens_briefing_main: int = 4000
    llm_max_tokens_briefing_stock: int = 2000
    llm_max_tokens_briefing_evening_stock: int = 3000
    llm_max_tokens_keyword_refine: int = 400
    llm_max_tokens_news_classifier: int = 200

    # ── 기타 ─────────────────────────────────────────────────────
    usage_file: str = "usage.json"
    usage_max_records: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
