"""뉴스 관련성 필터 — 시장 노이즈 차단 + 키워드 매칭.

확장: 새 노이즈 카테고리 추가 → MARKET_NOISE에 단어 추가.
"""
from typing import Iterable


MARKET_NOISE: tuple = (
    # 시장 종합 (지수/전체 시황)
    "코스피", "코스닥", "ETF", "시황", "마감", "장중", "장마감",
    "업종별", "순매수", "순매도", "주간 ", "일주일", "한 주의",
    "특징주", "상승률", "하락률", "거래량 상위", "리스트", "순위",
    # 스포츠
    "아시안게임", "올림픽", "월드컵", "K리그", "프로야구", "프로축구",
    "프로농구", "프로배구", "골프", "축구", "야구", "농구", "배구",
    "테니스", "마라톤", "스포츠",
    # 연예/문화
    "예능", "드라마", "공연", "콘서트", "팬미팅", "아이돌", "배우",
    "가수", "음반", "방송", "OTT",
    # 운세/생활
    "운세", "사주", "별자리", "타로", "오늘의 운세",
    "맛집", "여행", "레시피", "요리",
    # 정치 (주가에 직접 영향 안 가는 일반 정치)
    "총선", "대선", "선거", "재보선", "탄핵",
    # 사건/사고
    "교통사고", "화재", "폭행", "살인", "강도",
)


class RelevanceFilter:
    """노이즈 단어 + 키워드 매칭을 한 번에 적용."""

    def __init__(self, noise: Iterable[str] = MARKET_NOISE):
        self._noise = tuple(noise)

    def apply(self, items: list, keywords: list) -> list:
        out, seen = [], set()
        for it in items:
            link = it.get("link")
            if link in seen:
                continue
            seen.add(link)
            title = it.get("title", "")
            if any(n in title for n in self._noise):
                continue
            if not any(k.strip() and k in title for k in keywords):
                continue
            out.append(it)
        return out
