"""종목 검색 (자동완성)."""
from fastapi import APIRouter, Depends

from app.clients.dart import DartClient
from app.clients.yfinance import YFinanceClient
from app.dependencies import get_dart, get_yfinance


router = APIRouter()


@router.get("/api/search")
def search_stock(
    q: str = "",
    market: str = "kr",
    dart: DartClient = Depends(get_dart),
    yfinance: YFinanceClient = Depends(get_yfinance),
):
    if market == "us":
        return {"results": yfinance.search_us(q, limit=8)}
    return {"results": dart.search(q, limit=8)}
