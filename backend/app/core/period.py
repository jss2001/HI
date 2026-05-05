"""적응형 기간 필터 — 오늘 → 1주 → 1개월 → 전체. 충분히 모이면 stop."""
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

KST = timezone(timedelta(hours=9))


class PeriodFilter:
    """뉴스 아이템의 _iso 필드 기준으로 기간을 좁혀나가는 필터.

    확장: 새 tier 추가 → TIERS에 (days, label) 한 줄.
    """

    TIERS: List[Tuple[int, str]] = [
        (1, "오늘"),
        (7, "최근 1주"),
        (30, "최근 1개월"),
    ]

    def __init__(self, target: int = 5):
        self.target = target

    def apply(self, items: list) -> Tuple[list, str]:
        now = datetime.now(KST)
        for days, label in self.TIERS:
            cutoff = now - timedelta(days=days)
            sub = [it for it in items if self._after(it, cutoff)]
            if len(sub) >= self.target:
                return sub, label
        return items, "전체 기간"

    @staticmethod
    def _after(item: dict, cutoff: datetime) -> bool:
        iso = item.get("_iso", "")
        if not iso:
            return False
        try:
            pub = datetime.fromisoformat(iso)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=KST)
            return pub >= cutoff
        except Exception:
            return False
