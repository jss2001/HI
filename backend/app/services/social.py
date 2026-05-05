"""네이버 블로그·카페 검색 → 개인 투자자 sentiment + buzz 측정."""
import asyncio
import re
from datetime import datetime
from typing import Optional

import httpx
from cachetools import TTLCache

from app.clients.naver_search import NaverSearchClient
from app.config import Settings, get_settings


_HTML_RE = re.compile(r"<[^>]+>")
_ENTITIES = {"&quot;": '"', "&amp;": "&", "&apos;": "'", "&lt;": "<", "&gt;": ">"}


def _strip_html(text: str) -> str:
    s = _HTML_RE.sub("", text or "")
    for k, v in _ENTITIES.items():
        s = s.replace(k, v)
    return s.strip()


def _parse_postdate(item: dict) -> Optional[datetime]:
    v = item.get("postdate") or ""
    try:
        return datetime.strptime(v[:8], "%Y%m%d")
    except Exception:
        return None


def _ratio_label(ratio: float) -> tuple:
    if ratio >= 2.5:
        return "급상승", "🔥"
    if ratio >= 1.5:
        return "상승", "📈"
    if ratio >= 0.7:
        return "평소", "—"
    return "조용", "🌙"


class SocialService:
    """fetch_buzz(company) → 화제성 라벨 + 30개 글 샘플."""

    def __init__(
        self,
        naver: Optional[NaverSearchClient] = None,
        settings: Optional[Settings] = None,
    ):
        self._naver = naver or NaverSearchClient()
        self._settings = settings or get_settings()
        self._cache = TTLCache(maxsize=64, ttl=self._settings.cache_ttl_briefing)

    async def fetch_buzz(
        self,
        company: str,
        aliases: Optional[list] = None,
        exclusions: Optional[list] = None,
    ) -> Optional[dict]:
        if not self._naver.available:
            return None
        key = f"buzz:{company}"
        if key in self._cache:
            return self._cache[key]

        aliases = aliases or []
        exclusions = exclusions or []
        terms = [company] + aliases

        async with httpx.AsyncClient(timeout=self._settings.http_timeout_default) as c:
            blog_raw, cafe_raw = await asyncio.gather(
                self._naver.search_buzz(c, "blog", f'"{company}"', 50),
                self._naver.search_buzz(c, "cafearticle", f'"{company}"', 50),
            )

        today = datetime.now()
        counts = {"recent_3d": 0, "recent_week": 0, "recent_month": 0}
        posts = []

        for items, source in [(blog_raw, "blog"), (cafe_raw, "cafe")]:
            for it in items:
                dt = _parse_postdate(it)
                if not dt:
                    continue
                days = (today - dt).days
                if 0 <= days <= 30:
                    counts["recent_month"] += 1
                if 0 <= days <= 7:
                    counts["recent_week"] += 1
                if 0 <= days <= 3:
                    counts["recent_3d"] += 1

                title = _strip_html(it.get("title", ""))
                desc = _strip_html(it.get("description", ""))

                if any(ex in title for ex in exclusions) and company not in title:
                    continue
                if not any(t in title or t in desc[:80] for t in terms):
                    continue

                posts.append({
                    "source": source, "title": title, "snippet": desc[:160],
                    "date": dt.strftime("%Y.%m.%d"), "link": it.get("link", ""),
                })

        daily_avg = counts["recent_month"] / 30 if counts["recent_month"] else 0
        daily_recent = counts["recent_3d"] / 3 if counts["recent_3d"] else 0
        ratio = (daily_recent / daily_avg) if daily_avg > 0 else 0

        api_saturated = counts["recent_month"] >= 95
        if api_saturated:
            if counts["recent_3d"] >= 40:
                label, emoji = "매우 활발", "🔥"
            elif counts["recent_3d"] >= 20:
                label, emoji = "활발", "📈"
            else:
                label, emoji = "꾸준", "—"
            ratio_display = None
        else:
            label, emoji = _ratio_label(ratio)
            ratio_display = round(ratio, 2)

        result = {
            "buzz_label": label, "buzz_emoji": emoji, "buzz_ratio": ratio_display,
            "api_saturated": api_saturated, "counts": counts, "posts": posts[:30],
        }
        self._cache[key] = result
        return result
