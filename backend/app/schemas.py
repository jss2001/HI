"""HTTP 요청/응답 Pydantic 모델 — 라우터에서 검증."""
from typing import List, Optional

from pydantic import BaseModel


class PortfolioItem(BaseModel):
    stock_code: str
    name: Optional[str] = None
    avg_price: float
    quantity: int


class BriefingRequest(BaseModel):
    portfolio: List[PortfolioItem]
    yesterday_hypothesis: Optional[str] = None
    today_hypothesis: Optional[str] = None
