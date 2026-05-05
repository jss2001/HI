"""뉴스가 '주가에 진짜 의미 있는가' LLM 분류 — 룰베이스로 못 잡는 케이스 차단.

확장: 새 제외/포함 카테고리 추가 → _USER_TEMPLATE 수정.
"""
import hashlib
from typing import Optional

from cachetools import TTLCache

from app.clients.llm import LLMClient
from app.config import Settings, get_settings


_SYSTEM = (
    "당신은 한국 주식 뉴스 분류기. 사용자가 제공한 뉴스 제목 목록 중 "
    "특정 회사/섹터의 '주가·실적·기업가치'에 진짜 의미 있는 것만 골라낸다."
)

_USER_TEMPLATE = """대상: {context}

다음 뉴스 중 {context}의 **주가/실적/기업가치**에 의미 있는 것만 골라.

❌ 제외:
- 일반 제품 리뷰 (세탁기 사용기, 냉장고 비교, 자동차 시승기)
- 광고 캠페인 / 마케팅 행사
- 임직원 봉사활동 / 사회공헌 / 후원
- 사내 행사 / 채용 박람회 / 인턴십
- 일반 인터뷰 (가벼운 라이프스타일)
- 전시회 단순 참가 / 부스 안내
- 임원 개인사 (결혼/부고/기부 등)

✅ 포함:
- 실적·공시·분기 어닝·잠정실적
- 신제품 출시 (시장 임팩트 있는 것)
- 인수합병·투자·구조조정
- 주가 분석·목표가 변경·증권사 리포트
- 산업 정책·규제 영향
- 노조·파업·실적 가이던스
- 외국인/기관 매매 동향
- 글로벌 경쟁사 영향

뉴스 목록:
{titles}

엄격하게 의미 있는 것만 (최대 {max_keep}개).
JSON 출력: {{"keep": [번호1, 번호2, ...]}}"""


class NewsClassifier:
    """LLM에게 뉴스 제목 일괄 분류. 10분 캐시 + md5 키로 동일 입력 재사용."""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        settings: Optional[Settings] = None,
    ):
        self._llm = llm or LLMClient()
        s = settings or get_settings()
        self._max_tokens = s.llm_max_tokens_news_classifier
        self._cache = TTLCache(maxsize=512, ttl=s.cache_ttl_news_classifier)

    async def filter(self, items: list, context: str, max_keep: int = 12) -> list:
        if not items or not self._llm.available:
            return items
        titles = [it.get("title", "") for it in items]
        if not any(titles):
            return items

        key = hashlib.md5((context + "|" + "|".join(titles)).encode("utf-8")).hexdigest()
        if key in self._cache:
            idx = self._cache[key]
            return [items[i] for i in idx if 0 <= i < len(items)]

        titles_text = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
        user = _USER_TEMPLATE.format(context=context, titles=titles_text, max_keep=max_keep)

        data = await self._llm.complete_json(
            _SYSTEM, user, max_tokens=self._max_tokens, label=f"classify:{context}", temperature=0,
        )
        if not data:
            return items

        keep = data.get("keep", [])
        idx = [i - 1 for i in keep if isinstance(i, int) and 0 < i <= len(items)]
        self._cache[key] = idx
        return [items[i] for i in idx]
