"""사용자 정의 테마 — keyword → 시세(매핑 시) + 정제된 뉴스 + buzz."""
from typing import Optional

from app.clients.yfinance import YFinanceClient
from app.services.keyword_refiner import KeywordRefiner
from app.services.news import NewsService
from app.services.news_classifier import NewsClassifier
from app.services.social import SocialService


class ThemeService:
    """ThemeService.fetch(keyword) → {market, buzz, news, refined}."""

    def __init__(
        self,
        yfinance: Optional[YFinanceClient] = None,
        news: Optional[NewsService] = None,
        social: Optional[SocialService] = None,
        refiner: Optional[KeywordRefiner] = None,
        classifier: Optional[NewsClassifier] = None,
    ):
        self._yf = yfinance or YFinanceClient()
        self._news = news or NewsService()
        self._social = social or SocialService()
        self._refiner = refiner or KeywordRefiner()
        self._classifier = classifier or NewsClassifier()

    async def fetch(self, keyword: str) -> dict:
        kw = keyword.strip()
        market = self._yf.fetch_theme(kw)
        buzz = await self._social.fetch_buzz(kw)

        refined: dict = {"queries": [kw], "stocks": []}
        related_news: list = []
        period_used: Optional[str] = None
        try:
            pipeline = await self._news.fetch_with_refinement(
                kw, self._refiner, self._classifier, period_target=5, classify_max=12
            )
            refined = pipeline["refined"]
            period_used = pipeline["period"]
            related_news = [
                {"id": it["id"], "title": it["title"], "source": it["source"],
                 "time": it["time"], "link": it["link"]}
                for it in pipeline["items"][:10]
            ]
        except Exception:
            pass

        return {
            "keyword": kw, "market": market, "buzz": buzz,
            "news": related_news, "news_period": period_used, "refined": refined,
        }
