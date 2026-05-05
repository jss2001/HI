"""yfinance/Naver 실패 시 fallback용 mock 시드 데이터."""
import math
from datetime import datetime, timedelta


SECTORS_MOCK: list = [
    {"id": "ai", "name": "AI", "icon": "🤖", "color": "#6366F1", "change": 3.42,
     "price": 1842.55, "summary": "AI 반도체 수요 급증, 빅테크 실적 호조"},
    {"id": "semiconductor", "name": "반도체", "icon": "💾", "color": "#22C55E", "change": 2.18,
     "price": 4213.00, "summary": "HBM 공급 확대, 고대역폭 메모리 가격 강세"},
    {"id": "battery", "name": "2차전지", "icon": "🔋", "color": "#F97316", "change": 1.56,
     "price": 982.40, "summary": "전기차 보조금 정책 기대감 확산"},
    {"id": "bio", "name": "바이오", "icon": "🧬", "color": "#EC4899", "change": -0.83,
     "price": 1124.20, "summary": "임상 결과 발표 앞두고 관망세"},
    {"id": "finance", "name": "금융", "icon": "🏦", "color": "#0EA5E9", "change": 0.45,
     "price": 2310.10, "summary": "금리 인하 기대감으로 은행주 강보합"},
    {"id": "auto", "name": "자동차", "icon": "🚗", "color": "#14B8A6", "change": -1.12,
     "price": 1675.80, "summary": "글로벌 판매 둔화 우려 지속"},
]


def _gen_chart(base: float, change_pct: float, points: int = 40) -> list:
    series = []
    start = base / (1 + change_pct / 100)
    for i in range(points):
        t = i / (points - 1)
        wave = math.sin(t * math.pi * 2.2) * (base * 0.004)
        drift = (base - start) * t
        series.append(round(start + drift + wave, 2))
    return series


SECTOR_DETAILS_MOCK: dict = {
    s["id"]: {
        **s,
        "starred": s["id"] == "semiconductor",
        "chart": _gen_chart(s["price"], s["change"]),
        "comments": [
            {"id": f"{s['id']}-c1", "user": "투자자_민준", "time": "방금 전",
             "text": f"{s['name']} 섹터 오늘 흐름 좋네요. 외인 순매수 들어오는 듯.", "likes": 24},
            {"id": f"{s['id']}-c2", "user": "차트분석가", "time": "5분 전",
             "text": "단기 저항선 돌파 시도 중. 거래량 증가 확인됨.", "likes": 17},
            {"id": f"{s['id']}-c3", "user": "장기투자러", "time": "12분 전",
             "text": "장기적으로 우상향 그림 좋아 보입니다. 분할매수 중.", "likes": 9},
            {"id": f"{s['id']}-c4", "user": "데일리트레이더", "time": "30분 전",
             "text": "오전 갭상승 후 눌림목 매수 자리 나왔네요.", "likes": 5},
        ],
    }
    for s in SECTORS_MOCK
}


def _ts(days_ago: int, hour: int, minute: int) -> str:
    base = datetime(2026, 4, 25, hour, minute) - timedelta(days=days_ago)
    return base.strftime("%Y.%m.%d %H:%M")


NEWS_MOCK: list = [
    {"id": "n1", "date": "오늘", "time": _ts(0, 18, 42), "tag": "AI",
     "title": "엔비디아, 차세대 AI 가속기 양산 본격화 발표",
     "summary": "차세대 데이터센터용 칩 공급망이 안정화되며 출하량이 빠르게 확대될 전망",
     "source": "테크인사이트"},
    {"id": "n2", "date": "오늘", "time": _ts(0, 16, 10), "tag": "반도체",
     "title": "HBM4 양산 임박, 메모리 3사 공급 경쟁 격화",
     "summary": "삼성·SK·마이크론 모두 2026년 하반기 본격 양산 채비",
     "source": "마켓워치"},
    {"id": "n3", "date": "오늘", "time": _ts(0, 14, 5), "tag": "2차전지",
     "title": "전기차 보조금 확대안 국회 본회의 통과",
     "summary": "국내 2차전지 셀 업체 수혜 기대감 확산",
     "source": "에너지데일리"},
    {"id": "n4", "date": "어제", "time": _ts(1, 21, 30), "tag": "AI",
     "title": "오픈AI, 멀티모달 에이전트 신모델 공개",
     "summary": "이미지·음성·코드 통합 에이전트로 기업 시장 정조준",
     "source": "AI타임스"},
    {"id": "n5", "date": "어제", "time": _ts(1, 17, 22), "tag": "금융",
     "title": "한은 금통위, 기준금리 동결 가닥",
     "summary": "물가 둔화 추세 확인 시 하반기 인하 가능성 제기",
     "source": "이코노믹리뷰"},
    {"id": "n6", "date": "어제", "time": _ts(1, 11, 8), "tag": "바이오",
     "title": "국내 바이오텍, FDA 임상 3상 IND 승인",
     "summary": "글로벌 시장 진출 신호탄, 라이센스아웃 협상도 진행 중",
     "source": "바이오스펙테이터"},
    {"id": "n7", "date": "2일 전", "time": _ts(2, 19, 55), "tag": "자동차",
     "title": "현대차, 차세대 SDV 플랫폼 로드맵 공개",
     "summary": "OTA 기반 소프트웨어 중심 차량으로의 전환 가속",
     "source": "오토뉴스"},
    {"id": "n8", "date": "2일 전", "time": _ts(2, 13, 2), "tag": "반도체",
     "title": "TSMC, 2나노 공정 시제품 양산 돌입",
     "summary": "주요 팹리스 고객사 테이프아웃 본격화",
     "source": "테크인사이트"},
]
