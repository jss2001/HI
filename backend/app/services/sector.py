"""섹터 시세 서비스 — YFinanceClient 위에 얇게 래핑."""
from typing import Optional

from app.clients.yfinance import YFinanceClient


class SectorService:
    def __init__(self, yfinance: Optional[YFinanceClient] = None):
        self._yf = yfinance or YFinanceClient()

    def fetch_all(self, market: str = "kr") -> list:
        return self._yf.fetch_all_sectors(market=market)

    def fetch(self, sector_id: str, period_key: str = "daily", market: str = "kr") -> Optional[dict]:
        return self._yf.fetch_sector(sector_id, period_key, market=market)
