"""FastAPI Depends() 팩토리 — 라우터에 서비스 인스턴스 주입.

확장: 새 서비스 추가 → 여기에 get_xxx() 추가 후 라우터에서 Depends(get_xxx) 사용.
싱글톤이 필요하면 lru_cache로 감싸기.
"""
from functools import lru_cache

from app.clients.dart import DartClient
from app.clients.llm import LLMClient
from app.clients.naver_finance import NaverFinanceClient
from app.clients.naver_search import NaverSearchClient
from app.clients.yfinance import YFinanceClient
from app.core.technicals import TechnicalAnalyzer
from app.core.usage_tracker import UsageTracker
from app.services.analyst import AnalystService
from app.services.briefing import BriefingService
from app.services.keyword_refiner import KeywordRefiner
from app.services.news import NewsService
from app.services.news_classifier import NewsClassifier
from app.services.sector import SectorService
from app.services.social import SocialService
from app.services.theme import ThemeService


# ── Clients (싱글톤: 캐시 공유) ──────────────────────────
@lru_cache
def get_naver_search() -> NaverSearchClient:
    return NaverSearchClient()


@lru_cache
def get_naver_finance() -> NaverFinanceClient:
    return NaverFinanceClient()


@lru_cache
def get_dart() -> DartClient:
    return DartClient()


@lru_cache
def get_yfinance() -> YFinanceClient:
    return YFinanceClient()


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient()


@lru_cache
def get_usage_tracker() -> UsageTracker:
    return UsageTracker()


@lru_cache
def get_technicals() -> TechnicalAnalyzer:
    return TechnicalAnalyzer()


# ── Services ──────────────────────────────────────────
@lru_cache
def get_keyword_refiner() -> KeywordRefiner:
    return KeywordRefiner(llm=get_llm())


@lru_cache
def get_news_classifier() -> NewsClassifier:
    return NewsClassifier(llm=get_llm())


@lru_cache
def get_news_service() -> NewsService:
    return NewsService(naver=get_naver_search())


@lru_cache
def get_sector_service() -> SectorService:
    return SectorService(yfinance=get_yfinance())


@lru_cache
def get_social_service() -> SocialService:
    return SocialService(naver=get_naver_search())


@lru_cache
def get_theme_service() -> ThemeService:
    return ThemeService(
        yfinance=get_yfinance(),
        news=get_news_service(),
        social=get_social_service(),
        refiner=get_keyword_refiner(),
        classifier=get_news_classifier(),
    )


@lru_cache
def get_analyst_service() -> AnalystService:
    return AnalystService(
        dart=get_dart(),
        naver=get_naver_search(),
        naver_fin=get_naver_finance(),
        yfinance=get_yfinance(),
        technicals=get_technicals(),
        social=get_social_service(),
        llm=get_llm(),
    )


@lru_cache
def get_briefing_service() -> BriefingService:
    return BriefingService(
        yfinance=get_yfinance(),
        dart=get_dart(),
        naver=get_naver_search(),
        llm=get_llm(),
    )
