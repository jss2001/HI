"""종목 검색 (자동완성)."""
from fastapi import APIRouter, Depends

from app.clients.dart import DartClient
from app.dependencies import get_dart


router = APIRouter()


@router.get("/api/search")
def search_stock(q: str = "", dart: DartClient = Depends(get_dart)):
    return {"results": dart.search(q, limit=8)}
