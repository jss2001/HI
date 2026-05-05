"""LLM 호출 통합 어댑터 — OpenAI Async 클라이언트 + 자동 사용량 트래킹.

확장: 다른 LLM 추가 시 동일 인터페이스(complete_json/complete_text)로 새 클라이언트 작성.
"""
import json
from typing import Optional

from openai import AsyncOpenAI

from app.config import Settings, get_settings
from app.core.usage_tracker import UsageTracker


class LLMClient:
    """OpenAI Async + UsageTracker 자동 결합. JSON 응답 파싱까지 처리."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        tracker: Optional[UsageTracker] = None,
    ):
        self._settings = settings or get_settings()
        self._tracker = tracker or UsageTracker()
        self._client = (
            AsyncOpenAI(api_key=self._settings.openai_api_key)
            if self._settings.openai_api_key
            else None
        )

    @property
    def available(self) -> bool:
        return self._client is not None

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int,
        label: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Optional[dict]:
        """JSON 응답을 받아 파싱. 실패 시 None."""
        if not self._client:
            return None
        try:
            resp = await self._client.chat.completions.create(
                model=model or self._settings.llm_model_default,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception:
            return None

        self._track(resp, model or self._settings.llm_model_default, label)
        try:
            return json.loads(resp.choices[0].message.content)
        except Exception:
            return None

    async def complete_text(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int,
        label: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """일반 텍스트 응답."""
        if not self._client:
            return None
        try:
            resp = await self._client.chat.completions.create(
                model=model or self._settings.llm_model_default,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception:
            return None

        self._track(resp, model or self._settings.llm_model_default, label)
        try:
            return resp.choices[0].message.content
        except Exception:
            return None

    def _track(self, resp, model: str, label: str) -> None:
        try:
            self._tracker.record(
                model,
                resp.usage.prompt_tokens,
                resp.usage.completion_tokens,
                label,
            )
        except Exception:
            pass
