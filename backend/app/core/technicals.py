"""차트 기술적 지표 — yfinance OHLC → RSI / 이평 / 거래량 / 크로스 패턴."""
from typing import Optional

from cachetools import TTLCache

from app.config import get_settings


class TechnicalAnalyzer:
    """순수 시그널 계산기. yfinance ticker만 외부 의존.

    확장: 새 지표(MACD, 볼린저 등) 추가 → 메서드로 분리하고 analyze()에서 호출.
    """

    def __init__(self, yf_module=None, cache: Optional[TTLCache] = None):
        s = get_settings()
        self._yf = yf_module
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
            except Exception:
                self._yf = None
        self._cache = cache if cache is not None else TTLCache(
            maxsize=128, ttl=s.cache_ttl_yfinance
        )

    @property
    def available(self) -> bool:
        return self._yf is not None

    def analyze(self, code_or_ticker: str) -> dict:
        if not self.available or not code_or_ticker:
            return {}
        key = f"tech:{code_or_ticker}"
        if key in self._cache:
            return self._cache[key]

        t = self._resolve_ticker(code_or_ticker)
        if t is None:
            self._cache[key] = {}
            return {}

        try:
            df = t.history(period="3mo", interval="1d")
        except Exception:
            self._cache[key] = {}
            return {}
        if df.empty:
            self._cache[key] = {}
            return {}

        closes = [round(v, 2) for v in df["Close"].tolist()]
        volumes = [int(v) for v in df["Volume"].tolist()]
        dates = [d.strftime("%Y.%m.%d") for d in df.index]

        ma5 = self._ma(closes, 5)
        ma20 = self._ma(closes, 20)
        ma60 = self._ma(closes, 60)
        rsi = self._rsi(closes, 14)

        rsi_label, rsi_signal = self._rsi_signal(rsi)
        ma_align, ma_signal = self._ma_signal(ma5, ma20, ma60)
        cross_event = self._cross_event(ma5, ma20)
        vol_ratio, vol_label, vol_signal = self._vol_signal(volumes)

        keep = 60
        out = {
            "dates": dates[-keep:], "closes": closes[-keep:],
            "ma5": ma5[-keep:], "ma20": ma20[-keep:], "ma60": ma60[-keep:],
            "rsi": rsi, "rsi_label": rsi_label, "rsi_signal": rsi_signal,
            "ma_align": ma_align, "ma_signal": ma_signal,
            "cross_event": cross_event,
            "vol_ratio": vol_ratio, "vol_label": vol_label, "vol_signal": vol_signal,
            "last_close": closes[-1] if closes else None,
            "high_3mo": max(closes) if closes else None,
            "low_3mo": min(closes) if closes else None,
        }
        self._cache[key] = out
        return out

    # ── 내부 ─────────────────────────────────────────
    def _resolve_ticker(self, code_or_ticker: str):
        # 한국 종목 코드면 .KS/.KQ 양쪽 시도, 영문 ticker는 그대로
        candidates = [code_or_ticker]
        if code_or_ticker.isdigit():
            candidates = [f"{code_or_ticker}.KS", f"{code_or_ticker}.KQ"]
        for c in candidates:
            try:
                t = self._yf.Ticker(c)
                df = t.history(period="3mo", interval="1d")
                if not df.empty:
                    return t
            except Exception:
                continue
        return None

    @staticmethod
    def _ma(values: list, period: int) -> list:
        out = []
        for i in range(len(values)):
            if i < period - 1:
                out.append(None)
            else:
                window = values[i - period + 1: i + 1]
                out.append(round(sum(window) / period, 2))
        return out

    @staticmethod
    def _rsi(closes: list, period: int = 14) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 1)

    @staticmethod
    def _rsi_signal(rsi):
        if rsi is None:
            return "—", "neutral"
        if rsi >= 70:
            return "과매수", "negative"
        if rsi <= 30:
            return "과매도", "positive"
        return "중립", "neutral"

    @staticmethod
    def _ma_signal(ma5, ma20, ma60):
        last5, last20, last60 = ma5[-1], ma20[-1], ma60[-1]
        if not (last5 and last20 and last60):
            return "—", "neutral"
        if last5 > last20 > last60:
            return "정배열 (5>20>60)", "positive"
        if last5 < last20 < last60:
            return "역배열 (5<20<60)", "negative"
        if last5 > last20:
            return "단기 우위 (5>20)", "positive"
        if last5 < last20:
            return "단기 약세 (5<20)", "negative"
        return "혼조", "neutral"

    @staticmethod
    def _cross_event(ma5, ma20):
        if len(ma5) < 6:
            return None
        if not (ma5[-6] and ma20[-6] and ma5[-1] and ma20[-1]):
            return None
        prev = ma5[-6] - ma20[-6]
        last = ma5[-1] - ma20[-1]
        if prev < 0 < last:
            return "골든크로스"
        if prev > 0 > last:
            return "데드크로스"
        return None

    @staticmethod
    def _vol_signal(volumes):
        if len(volumes) < 20:
            return None, "—", "neutral"
        recent5 = sum(volumes[-5:]) / 5
        avg20 = sum(volumes[-20:]) / 20
        if not avg20:
            return None, "—", "neutral"
        ratio = round(recent5 / avg20, 2)
        if ratio >= 1.5:
            return ratio, "거래량 급증", "positive"
        if ratio >= 1.1:
            return ratio, "거래량 증가", "positive"
        if ratio <= 0.7:
            return ratio, "거래량 감소", "negative"
        return ratio, "평소", "neutral"
