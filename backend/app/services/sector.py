"""섹터 시세 서비스 — YFinanceClient 위에 얇게 래핑."""
from typing import Optional

from app.clients.yfinance import YFinanceClient


class SectorService:
    def __init__(self, yfinance: Optional[YFinanceClient] = None):
        self._yf = yfinance or YFinanceClient()

    def fetch_all(self) -> list:
        return self._yf.fetch_all_sectors()

    def fetch(self, sector_id: str, period_key: str = "daily") -> Optional[dict]:
        return self._yf.fetch_sector(sector_id, period_key)
