"""사용자 키워드 → 시장 컨텍스트로 정제. 다의어(예: '게임' → 비디오게임주 vs 아시안게임) 차단."""
from typing import Optional

from cachetools import TTLCache

from app.clients.llm import LLMClient
from app.config import Settings, get_settings


_SYSTEM = (
    "한국 주식 시장 검색 도우미. 사용자 키워드를 받아 한국 주식 관련 뉴스를 정확히 잡을 수 있는 "
    "검색 쿼리와 대표 한국 종목을 JSON으로 반환한다."
)


class KeywordRefiner:
    """LLM으로 키워드 정제. 24h 캐시. 실패 시 단순 fallback."""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        settings: Optional[Settings] = None,
    ):
        self._llm = llm or LLMClient()
        s = settings or get_settings()
        self._max_tokens = s.llm_max_tokens_keyword_refine
        self._cache = TTLCache(maxsize=s.cache_max_size_keyword, ttl=s.cache_ttl_keyword_refine)

    async def refine(self, keyword: str) -> dict:
        kw = keyword.strip()
        if not kw:
            return {"queries": [], "stocks": []}
        if kw in self._cache:
            return self._cache[kw]
        if not self._llm.available:
            out = self._fallback(kw)
            self._cache[kw] = out
            return out

        user = (
            f'사용자 키워드: "{kw}"\n\n'
            "지시:\n"
            "1. 다의어 회피. 예: '게임' 입력 → 아시안게임/올림픽 X, 비디오게임 회사 ✅.\n"
            "2. queries: 한국 주식 뉴스 검색에 쓸 핵심 검색어 3~5개. 종목명 + 시장 키워드 조합.\n"
            "3. stocks: 그 키워드 대표 한국 상장사 3~6개 (정확한 정식명).\n"
            "4. 비-주식 의미가 강한 키워드면 stocks 빈 배열.\n\n"
            '출력 JSON: {"queries": ["..."], "stocks": ["..."]}'
        )
        data = await self._llm.complete_json(
            _SYSTEM, user, max_tokens=self._max_tokens, label=f"refine:{kw}", temperature=0.2
        )
        if not data:
            out = self._fallback(kw)
        else:
            out = {
                "queries": data.get("queries", [])[:6] or [kw],
                "stocks": data.get("stocks", [])[:6],
            }
        self._cache[kw] = out
        return out

    @staticmethod
    def _fallback(kw: str) -> dict:
        return {"queries": [kw, f"{kw} 주식", f"{kw}주"], "stocks": []}
