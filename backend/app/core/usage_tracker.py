"""LLM 호출량/비용 트래커 — record() 후 summary()로 대시보드 데이터 제공.

확장: 새 모델 가격 → app/core/constants.py OPENAI_PRICES에 추가.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from app.config import get_settings
from app.core.constants import OPENAI_PRICES

KST = timezone(timedelta(hours=9))


class UsageTracker:
    def __init__(self, log_path: Optional[Path] = None, max_records: Optional[int] = None):
        s = get_settings()
        self._path = Path(log_path) if log_path else Path(__file__).resolve().parent.parent.parent / s.usage_file
        self._max = max_records if max_records is not None else s.usage_max_records
        self._lock = Lock()

    def record(self, model: str, prompt_tokens: int, completion_tokens: int, label: str = "") -> None:
        if prompt_tokens is None and completion_tokens is None:
            return
        with self._lock:
            data = self._load()
            price = OPENAI_PRICES.get(model, OPENAI_PRICES["gpt-4o-mini"])
            cost = (prompt_tokens or 0) * price["input"] + (completion_tokens or 0) * price["output"]
            entry = {
                "ts": datetime.now(KST).isoformat(timespec="seconds"),
                "model": model,
                "prompt": prompt_tokens or 0,
                "completion": completion_tokens or 0,
                "cost_usd": round(cost, 6),
                "label": label,
            }
            data["calls"].append(entry)
            if len(data["calls"]) > self._max:
                data["calls"] = data["calls"][-self._max:]
            data["totals"]["prompt"] += entry["prompt"]
            data["totals"]["completion"] += entry["completion"]
            data["totals"]["cost_usd"] = round(data["totals"]["cost_usd"] + cost, 6)
            try:
                self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            except Exception:
                pass

    def summary(self, limit: int = 50) -> dict:
        data = self._load()
        by_day, by_label, by_model = {}, {}, {}
        for c in data["calls"]:
            day = c["ts"][:10]
            self._bucket(by_day, day, c)
            lbl_root = c.get("label", "(unlabeled)").split(":")[0]
            self._bucket_lite(by_label, lbl_root, c)
            self._bucket(by_model, c["model"], c)

        today = datetime.now(KST).strftime("%Y-%m-%d")
        today_stats = by_day.get(today, {"calls": 0, "prompt": 0, "completion": 0, "cost_usd": 0.0})

        return {
            "total": data["totals"],
            "today": today_stats,
            "today_date": today,
            "by_day": [{"date": d, **v} for d, v in sorted(by_day.items(), reverse=True)][:30],
            "by_label": [{"label": k, **v} for k, v in sorted(by_label.items(), key=lambda x: -x[1]["cost_usd"])],
            "by_model": [{"model": k, **v} for k, v in sorted(by_model.items(), key=lambda x: -x[1]["cost_usd"])],
            "recent": data["calls"][-limit:][::-1],
        }

    # ── 내부 ──
    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                pass
        return {"calls": [], "totals": {"prompt": 0, "completion": 0, "cost_usd": 0.0}}

    @staticmethod
    def _bucket(d: dict, key: str, c: dict):
        d.setdefault(key, {"calls": 0, "prompt": 0, "completion": 0, "cost_usd": 0.0})
        d[key]["calls"] += 1
        d[key]["prompt"] += c["prompt"]
        d[key]["completion"] += c["completion"]
        d[key]["cost_usd"] = round(d[key]["cost_usd"] + c["cost_usd"], 6)

    @staticmethod
    def _bucket_lite(d: dict, key: str, c: dict):
        d.setdefault(key, {"calls": 0, "cost_usd": 0.0})
        d[key]["calls"] += 1
        d[key]["cost_usd"] = round(d[key]["cost_usd"] + c["cost_usd"], 6)
