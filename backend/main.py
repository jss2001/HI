from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from data import NEWS, SECTOR_DETAILS, SECTORS

app = FastAPI(title="섹터체크 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "sector-check", "ok": True}


@app.get("/api/sectors")
def list_sectors():
    hot = sorted(SECTORS, key=lambda s: abs(s["change"]), reverse=True)[:3]
    return {
        "hot": hot,
        "all": SECTORS,
    }


@app.get("/api/sectors/{sector_id}")
def get_sector(sector_id: str):
    detail = SECTOR_DETAILS.get(sector_id)
    if not detail:
        raise HTTPException(status_code=404, detail="sector not found")
    return detail


@app.get("/api/news")
def list_news(tag: Optional[str] = None):
    items = NEWS if not tag else [n for n in NEWS if n["tag"] == tag]
    grouped = {}
    for n in items:
        grouped.setdefault(n["date"], []).append(n)
    return {
        "groups": [{"date": d, "items": grouped[d]} for d in grouped],
        "tags": sorted({n["tag"] for n in NEWS}),
    }
