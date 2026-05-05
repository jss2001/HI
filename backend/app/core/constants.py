"""도메인 상수 — 코드 한복판이 아닌 한 곳에서 관리.

확장:
- 새 섹터 → SECTOR_DEFS에 추가 (id/name/icon/color/ticker/summary_query/subtitle)
- 새 테마 → THEME_ETF_MAP에 (키워드 → ETF ticker) 추가
- 차트 기간 옵션 → PERIOD_CONFIG에 추가
"""

SECTOR_DEFS: dict = {
    "ai": {
        "name": "AI", "icon": "🤖", "color": "#6366F1",
        "ticker": "469150.KS",
        "summary_query": "AI 반도체 주가",
        "subtitle": "AI 반도체 공급망",
    },
    "semiconductor": {
        "name": "반도체", "icon": "💾", "color": "#22C55E",
        "ticker": "091160.KS",
        "summary_query": "반도체 주가",
        "subtitle": "KODEX 반도체",
    },
    "battery": {
        "name": "2차전지", "icon": "🔋", "color": "#F97316",
        "ticker": "305720.KS",
        "summary_query": "2차전지 전기차 배터리",
        "subtitle": "KODEX 2차전지산업",
    },
    "bio": {
        "name": "바이오", "icon": "🧬", "color": "#EC4899",
        "ticker": "244580.KS",
        "summary_query": "바이오 제약 주가",
        "subtitle": "KODEX 바이오",
    },
    "finance": {
        "name": "금융", "icon": "🏦", "color": "#0EA5E9",
        "ticker": "091170.KS",
        "summary_query": "은행주 금융주",
        "subtitle": "KODEX 은행",
    },
    "auto": {
        "name": "자동차", "icon": "🚗", "color": "#14B8A6",
        "ticker": "091180.KS",
        "summary_query": "자동차 주가 현대차 기아",
        "subtitle": "KODEX 자동차",
    },
}


PERIOD_CONFIG: dict = {
    "daily":   {"period": "1mo", "interval": "1d",  "label": "최근 1개월 일봉 · 전일 대비"},
    "weekly":  {"period": "6mo", "interval": "1wk", "label": "최근 6개월 주봉 · 전주 대비"},
    "monthly": {"period": "2y",  "interval": "1mo", "label": "최근 2년 월봉 · 전월 대비"},
    "yearly":  {"period": "10y", "interval": "1mo", "label": "최근 10년 · 1년 전 대비"},
}


# 테마 키워드 → ETF 티커 (사용자 정의 테마에서 시세 매핑)
THEME_ETF_MAP: dict = {
    "로봇": "445290.KS",
    "방산": "449450.KS",
    "우주": "475730.KS",
    "메타버스": "401170.KS",
    "게임": "300610.KS",
    "헬스케어": "266390.KS",
    "전기차": "412960.KS",
    "화장품": "228790.KS",
    "음식료": "228810.KS",
    "미디어": "228800.KS",
}


# OpenAI 가격 (USD per token, 2026 기준)
OPENAI_PRICES: dict = {
    "gpt-4o-mini":  {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o":       {"input": 2.50 / 1_000_000, "output": 10.0 / 1_000_000},
    "gpt-4.1-mini": {"input": 0.40 / 1_000_000, "output": 1.60 / 1_000_000},
    "gpt-4.1":      {"input": 2.00 / 1_000_000, "output": 8.00 / 1_000_000},
}
