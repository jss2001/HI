from fastapi import APIRouter, HTTPException
from app.services.exchange import get_exchange_report

router = APIRouter(prefix="/api/exchange", tags=["exchange"])

@router.get("/report")
async def read_exchange_report():
    try:
        data = get_exchange_report()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
