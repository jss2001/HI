"""장전·장마감 브리핑 — 포트폴리오 기반, 종목별 병렬 LLM 호출로 깊이 보장."""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from cachetools import TTLCache

from app.clients.dart import DartClient
from app.clients.llm import LLMClient
from app.clients.naver_search import NaverSearchClient
from app.clients.yfinance import YFinanceClient
from app.config import Settings, get_settings


KST = timezone(timedelta(hours=9))


GLOBAL_MARKETS = {
    "S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow": "^DJI",
    "NVDA": "NVDA", "TSM": "TSM",
    "달러원": "KRW=X", "WTI 유가": "CL=F", "10년물 국채": "^TNX",
}


MORNING_SYSTEM = """당신은 베테랑 셀사이드 애널리스트. 한국 개인 투자자를 위한 장전 브리핑 작성.

핵심 원칙 (반드시 지킬 것):
1. **모든 주장에 구체 근거** — 숫자(%, 가격), 날짜, 이벤트, 매체명 인용 필수.
   - 좋음: "NVDA +3.2% 마감, AI 칩 공급망 수혜로 SK하이닉스 갭상승 예상"
   - 나쁨: "기술주 상승 영향으로 긍정적"
2. **인과 메커니즘 명시** — 왜 그 영향이 오는지 한 단계 설명.
3. **일반론·추상 표현 금지** — "주의 필요" "긍정적" 같은 표현 X. 무엇을 어떻게 봐야 할지 구체적으로.
4. **사용자 보유 종목 각각** 에 대해 진짜 종목 특성 반영 (HBM/메모리/2차전지 등).
5. 한국어, 단호한 톤. 분석가가 발신한 short note 느낌."""


EVENING_SYSTEM = """당신은 베테랑 셀사이드 애널리스트. 한국 개인 투자자를 위한 장마감 브리핑 작성.

핵심 원칙:
1. **종목별 움직임 원인을 진짜 뉴스/공시로 구체화** — "노조 파업 우려로 -2.5%" 식.
2. **오전 가설 검증** — 가설이 맞았으면 어디가 맞았고, 틀렸으면 무엇이 변수였는지.
3. **내일 체크리스트** — 추상 X. "삼성전자 노조 협상 결과 확인" 같이 구체적.
4. 한국어, 단호한 톤."""


STOCK_DEEP_SYSTEM_MORNING = """베테랑 셀사이드 애널리스트. 단일 종목에 대한 깊은 장전 분석 작성.
구체 근거 + 인과 + 출처 인용 필수. 일반론 X.
'주의 필요' 같은 추상 표현 금지. 무엇을 어떻게 봐야 하는지 구체적으로."""


STOCK_DEEP_SYSTEM_EVENING = """베테랑 셀사이드 애널리스트. 단일 종목의 장마감 결과 분석 작성.
오늘 무엇이 일어났고, 왜 그 흐름이었는지, 평단 보유자에게 어떤 시사점인지 깊이 분석.
구체 뉴스/공시 인용 필수. 추상 표현 금지."""


class BriefingService:
    """morning() / evening() — 시장 종합 + 종목별 깊은 분석 병렬."""

    def __init__(
        self,
        yfinance: Optional[YFinanceClient] = None,
        dart: Optional[DartClient] = None,
        naver: Optional[NaverSearchClient] = None,
        llm: Optional[LLMClient] = None,
        settings: Optional[Settings] = None,
    ):
        self._yf = yfinance or YFinanceClient()
        self._dart = dart or DartClient()
        self._naver = naver or NaverSearchClient()
        self._llm = llm or LLMClient()
        self._settings = settings or get_settings()
        self._cache = TTLCache(maxsize=64, ttl=self._settings.cache_ttl_briefing)

    # ── 공용 헬퍼 ────────────────────────────────────
    def fetch_global_overnight(self) -> dict:
        if "global" in self._cache:
            return self._cache["global"]
        if not self._yf.available:
            return {}
        out = {}
        for name, ticker in GLOBAL_MARKETS.items():
            try:
                t = self._yf._yf.Ticker(ticker)
                info = t.info
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                change_pct = info.get("regularMarketChangePercent")
                if price is not None:
                    out[name] = {
                        "ticker": ticker, "price": price,
                        "change": round(change_pct, 2) if change_pct is not None else None,
                    }
            except Exception:
                continue
        self._cache["global"] = out
        return out

    def fetch_quotes(self, portfolio: list) -> list:
        """포트폴리오 각 종목 현재가 + 평단 대비 ROI."""
        out = []
        for p in portfolio:
            code = (p.get("stock_code") or "").strip()
            avg_price = float(p.get("avg_price", 0) or 0)
            quantity = int(p.get("quantity", 0) or 0)
            if not code or avg_price <= 0:
                continue

            market = self._yf.get_kr_info(code) if code.isdigit() else None
            if not market:
                # 글로벌 ticker 또는 KS suffix 직접 시도
                try:
                    t = self._yf._yf.Ticker(code if not code.isdigit() else f"{code}.KS")
                    info = t.info
                    market = {
                        "price": info.get("regularMarketPrice") or info.get("currentPrice"),
                        "change_pct": info.get("regularMarketChangePercent"),
                    }
                except Exception:
                    market = {}

            cur = market.get("price")
            if cur is None:
                continue
            roi = ((cur - avg_price) / avg_price * 100) if avg_price else 0

            name = p.get("name") or ""
            if not name and code.isdigit():
                corp = self._dart.find(code)
                name = corp["corp_name"] if corp else code
            elif not name:
                name = code

            out.append({
                "stock_code": code, "name": name,
                "avg_price": avg_price, "quantity": quantity,
                "current_price": cur, "today_change": market.get("change_pct"),
                "roi_pct": round(roi, 2),
                "value": round(cur * quantity, 0),
                "pnl": round((cur - avg_price) * quantity, 0),
            })
        return out

    async def _fetch_news_for_quotes(self, quotes: list, max_per_stock: int = 5) -> dict:
        if not quotes:
            return {}
        async with httpx.AsyncClient(timeout=self._settings.http_timeout_default) as c:
            tasks = [self._naver.search_news(c, q["name"], max_per_stock * 2, tag=q["name"])
                     for q in quotes]
            results = await asyncio.gather(*tasks)
        out: dict = {}
        for q, items in zip(quotes, results):
            out[q["stock_code"]] = [
                {"title": it["title"], "source": it["source"], "time": it["time"]}
                for it in items[:max_per_stock]
            ]
        return out

    async def _fetch_filings_for_quotes(self, quotes: list) -> dict:
        out: dict = {}
        for q in quotes:
            if not q["stock_code"].isdigit():
                continue
            try:
                corp = self._dart.find(q["stock_code"])
                if not corp:
                    continue
                filings = await self._dart.get_filings(corp["corp_code"], days=14, limit=8)
                if filings:
                    out[q["stock_code"]] = filings[:5]
            except Exception:
                continue
        return out

    # ── 종목별 깊은 분석 (장전) ────────────────────
    async def _analyze_stock_morning(
        self, quote: dict, news: list, filings: list, global_summary: str,
    ) -> Optional[dict]:
        if not self._llm.available:
            return None
        news_text = "\n".join(f"  - [{n['source']} {n['time']}] {n['title']}" for n in news[:6]) or "  (없음)"
        filings_text = "\n".join(f"  - [{f['date']}] {f['report_nm']}" for f in filings[:5]) or "  (없음)"

        user = f"""# 종목
{quote['name']} ({quote['stock_code']})
평단 {quote['avg_price']:,.0f} → 현재 {quote['current_price']:,.0f} ({quote['roi_pct']:+.2f}%)
보유 {quote['quantity']}주, P/L {quote['pnl']:+,.0f}원

# 밤사이 해외 시장 요약
{global_summary}

# 최근 뉴스
{news_text}

# 최근 14일 DART 공시
{filings_text}

위 데이터로 이 종목의 오늘 분석을 JSON으로 작성. **각 필드 분량 엄격히 지킬 것.**

{{
  "expected": "강세 우호 / 변동성 주의 / 관망 / 약세 우려 중 택1",
  "thesis": "**최소 5문장 (300자 이상)**. ① 종목 현황·최근 동향, ② 글로벌 영향, ③ 종목 고유 이슈, ④ 평단 대비 현재가 의미, ⑤ 단기 전망. 구체 숫자/매체/날짜 인용 필수.",
  "drivers": [
    "호재 1 (사건명 + 임팩트 + 매체+날짜, 30자 이상)",
    "호재 2",
    "호재 3",
    "호재 4 (있으면)"
  ],
  "risks": [
    "리스크 1 (구체 변수 + 영향, 30자 이상)",
    "리스크 2",
    "리스크 3 (있으면)"
  ],
  "key_level": "오늘 의미 있는 가격대 — 상방 저항 X원, 하방 지지 Y원 + 의미",
  "watchpoint": "오늘 봐야 할 핵심 — 시간 + 지표 + 임계치 구체적"
}}"""

        data = await self._llm.complete_json(
            STOCK_DEEP_SYSTEM_MORNING, user,
            max_tokens=self._settings.llm_max_tokens_briefing_stock,
            label=f"morning_stock:{quote['name']}", temperature=0.25,
        )
        if not data:
            return None
        data["stock_code"] = quote["stock_code"]
        data["name"] = quote["name"]
        return data

    # ── 종목별 깊은 분석 (장마감) ──────────────────
    async def _analyze_stock_evening(
        self, quote: dict, news: list, filings: list, today_hypothesis: Optional[str],
    ) -> Optional[dict]:
        if not self._llm.available:
            return None
        news_text = "\n".join(f"  - [{n['source']} {n['time']}] {n['title']}" for n in news[:6]) or "  (없음)"
        filings_text = "\n".join(f"  - [{f['date']}] {f['report_nm']}" for f in filings[:5]) or "  (없음)"
        hypo = f"\n# 오전 가설 (검증용)\n{today_hypothesis}" if today_hypothesis else ""

        user = f"""# 종목
{quote['name']} ({quote['stock_code']})
평단 {quote['avg_price']:,.0f} → 현재 {quote['current_price']:,.0f} ({quote['roi_pct']:+.2f}%)
오늘 {quote.get('today_change', 0) or 0:+.2f}%, 보유 {quote['quantity']}주, P/L {quote['pnl']:+,.0f}원

# 오늘 뉴스
{news_text}

# 최근 14일 공시
{filings_text}
{hypo}

이 종목의 오늘 결과 분석을 JSON으로 작성.

{{
  "verdict": "선전 / 약세 / 보합 / 변동성 큼 중 택1",
  "summary": "**최소 5문장 (300자 이상)**. 등락률+동인, 뉴스/공시 작용, 평단 보유자 시사점, 단기 추세, 다음 변수.",
  "key_drivers": [
    "오늘 움직임 원인 1 (구체 뉴스+매체+영향, 30자 이상)",
    "원인 2",
    "원인 3 (있으면)"
  ],
  "concerns": [
    "오늘 드러난 우려 1 (30자 이상)",
    "우려 2 (있으면)"
  ],
  "holder_take": "평단 {quote['avg_price']:,.0f}원 보유자에게 한 줄 — '추가매수 검토'/'관망'/'익절 고려'/'손절 검토' 같이 구체적",
  "tomorrow_watch": "내일 봐야 할 핵심 — 시간 + 지표 + 임계치"
}}"""

        data = await self._llm.complete_json(
            STOCK_DEEP_SYSTEM_EVENING, user,
            max_tokens=self._settings.llm_max_tokens_briefing_evening_stock,
            label=f"evening_stock:{quote['name']}", temperature=0.25,
        )
        if not data:
            return None
        data["stock_code"] = quote["stock_code"]
        data["name"] = quote["name"]
        data["today_pct"] = quote.get("today_change") or 0
        data["roi_pct"] = quote.get("roi_pct")
        return data

    # ── 메인 엔트리 ────────────────────────────────
    async def morning(self, portfolio: list, yesterday_hypothesis: Optional[str] = None) -> dict:
        if not self._llm.available:
            return {"error": "OPENAI_API_KEY 없음"}

        global_data = self.fetch_global_overnight()
        quotes = self.fetch_quotes(portfolio)
        news_by_stock = await self._fetch_news_for_quotes(quotes, max_per_stock=5)
        filings_by_stock = await self._fetch_filings_for_quotes(quotes)

        global_text = "\n".join(
            f"- {name}: {d['price']} ({d['change']:+.2f}%)" if d.get("change") is not None
            else f"- {name}: {d['price']}"
            for name, d in global_data.items()
        ) or "(데이터 없음)"

        analyses = await asyncio.gather(*[
            self._analyze_stock_morning(
                q, news_by_stock.get(q["stock_code"], []),
                filings_by_stock.get(q["stock_code"], []), global_text,
            )
            for q in quotes
        ])
        stock_impact = [s for s in analyses if s]

        yesterday_text = f"\n# 어제 세웠던 가설\n{yesterday_hypothesis}" if yesterday_hypothesis else ""
        stocks_summary = "\n".join(
            f"- {s['name']}: {s.get('expected','')}, {s.get('thesis','')[:80]}"
            for s in stock_impact
        ) or "(분석 없음)"

        user = f"""# 오늘 날짜
{datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}

# 밤사이 해외 시장
{global_text}

# 사용자 종목별 분석 결과 (이미 종목별로 깊이 분석됨)
{stocks_summary}
{yesterday_text}

지시사항:
- 위 데이터를 종합한 **시장 전체 관점** brief만 작성. 종목별 분석은 이미 완료됨.
- 모든 주장에 구체 수치/이벤트 인용. 추상 표현 X. 인과 메커니즘 명시.

JSON 출력:
{{
  "headline": "오늘 한 줄 (구체 이벤트+숫자, 25-50자)",
  "overseas": "**최소 5문장 (350자 이상)**. S&P/Nasdaq/Dow, NVDA/TSM, 환율·유가, 채권·금리, 한국 시장 시사점.",
  "domestic_impact": "**최소 4문장 (250자 이상)**. 환율→수출주, 유가→에너지, 글로벌 기술주→한국 반도체 등 인과.",
  "hypothesis": "오늘 가장 중요할 단일 변수 (4시 검증 가능 형태)",
  "checklist": [
    "오늘 N시 확인할 변수 1 (시간+지표+임계치)",
    "변수 2", "변수 3", "변수 4 (있으면)"
  ]
}}"""

        brief = await self._llm.complete_json(
            MORNING_SYSTEM, user,
            max_tokens=self._settings.llm_max_tokens_briefing_main,
            label="morning:main", temperature=0.25,
        )
        if not brief:
            return {"error": "LLM 실패"}
        brief["stock_impact"] = stock_impact

        return {
            "type": "morning",
            "timestamp": datetime.now(KST).isoformat(),
            "global": global_data, "portfolio": quotes, "brief": brief,
        }

    async def evening(self, portfolio: list, today_hypothesis: Optional[str] = None) -> dict:
        if not self._llm.available:
            return {"error": "OPENAI_API_KEY 없음"}

        quotes = self.fetch_quotes(portfolio)
        news_by_stock = await self._fetch_news_for_quotes(quotes, max_per_stock=6)
        filings_by_stock = await self._fetch_filings_for_quotes(quotes)

        analyses = await asyncio.gather(*[
            self._analyze_stock_evening(
                q, news_by_stock.get(q["stock_code"], []),
                filings_by_stock.get(q["stock_code"], []), today_hypothesis,
            )
            for q in quotes
        ])
        stock_results = [s for s in analyses if s]

        stocks_summary = "\n".join(
            f"- {s['name']}: {s.get('verdict','')} ({s.get('today_pct',0):+.2f}%) — {s.get('summary','')[:80]}"
            for s in stock_results
        ) or "(분석 없음)"
        hypothesis_text = f"\n# 오전 가설\n{today_hypothesis}" if today_hypothesis else ""

        user = f"""# 오늘 날짜
{datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}

# 종목별 분석 (이미 깊이 완료됨)
{stocks_summary}
{hypothesis_text}

지시: 시장 전체 종합 + 가설 검증 + 내일 체크리스트만 작성.

JSON:
{{
  "headline": "오늘 시장 한 줄 (구체 이벤트+숫자, 25-50자)",
  "market_summary": "**최소 5문장 (350자 이상)**. KOSPI/KOSDAQ, 외국인·기관 수급, 섹터별, 환율, 종합 시사점.",
  "hypothesis_check": "오전 가설 검증 — 최소 3문장 (200자 이상). 어디가 맞고 어디가 빗나갔는지. 가설 없으면 빈 문자열.",
  "key_news": [
    "오늘 핵심 뉴스 1 (30자 이상)", "뉴스 2", "뉴스 3", "뉴스 4 (있으면)"
  ],
  "tomorrow_checklist": [
    "내일 N시 변수 1 (시간+지표+임계치, 30자 이상)",
    "변수 2", "변수 3", "변수 4 (있으면)"
  ]
}}"""

        brief = await self._llm.complete_json(
            EVENING_SYSTEM, user,
            max_tokens=self._settings.llm_max_tokens_briefing_evening_stock,  # 3000
            label="evening:main", temperature=0.3,
        )
        if not brief:
            return {"error": "LLM 실패"}
        brief["stock_results"] = stock_results

        return {
            "type": "evening",
            "timestamp": datetime.now(KST).isoformat(),
            "portfolio": quotes, "brief": brief,
        }

    async def morning_us(self, portfolio: list) -> dict:
        """미장 장전 22:30 KST 프리뷰 — 직전 세션/오버나잇 데이터 → 오늘 미장 시나리오."""
        if not self._llm.available:
            return {"error": "OPENAI_API_KEY 없음"}

        global_data = self.fetch_global_overnight()
        if not global_data:
            return {"error": "글로벌 시세를 불러오지 못했습니다"}

        global_text = "\n".join(
            f"- {name} ({d['ticker']}): {d['price']} ({d['change']:+.2f}%)"
            if d.get("change") is not None else f"- {name}: {d['price']}"
            for name, d in global_data.items()
        )

        user = f"""# 시각
{datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')} (오늘 미장 22:30 개장 전)

# 직전 세션 + 오버나잇 스냅샷
{global_text}

지시:
- **오늘 미장 장전 프리뷰** 작성. 22:30 개장 전 체크해야 할 것들.
- 직전 세션 클로즈, 프리마켓 동향, 매크로 변수(달러/유가/금리), 주요 빅테크 이벤트.
- 구체 수치 + 인과 메커니즘. 추상 표현 X.

JSON:
{{
  "headline": "오늘 미장 한 줄 프리뷰 (구체 이벤트+숫자, 25-50자)",
  "overseas": "**최소 5문장 (350자 이상)**. 직전 세션 종가/등락, 프리마켓, 빅테크 이벤트, 환율·유가·금리 흐름.",
  "domestic_impact": "**최소 3문장**. 미국 시장 흐름이 한국 시장(특히 ADR/반도체/관련주)에 줄 영향.",
  "hypothesis": "오늘 미장 가장 중요한 단일 변수 (5시 마감 시 검증 가능 형태)",
  "checklist": [
    "오늘 N시 확인할 변수 1 (시간+지표+임계치)",
    "변수 2", "변수 3", "변수 4 (있으면)"
  ]
}}"""

        brief = await self._llm.complete_json(
            MORNING_SYSTEM, user,
            max_tokens=self._settings.llm_max_tokens_briefing_main,
            label="morning_us:main", temperature=0.25,
        )
        if not brief:
            return {"error": "LLM 실패"}
        brief["stock_impact"] = []
        return {
            "type": "morning",
            "market": "us",
            "timestamp": datetime.now(KST).isoformat(),
            "global": global_data, "portfolio": [], "brief": brief,
        }

    async def evening_us(self, portfolio: list) -> dict:
        """미장 종합 — 글로벌 인덱스/주요 빅테크 스냅샷 + LLM 코멘트."""
        if not self._llm.available:
            return {"error": "OPENAI_API_KEY 없음"}

        global_data = self.fetch_global_overnight()
        if not global_data:
            return {"error": "글로벌 시세를 불러오지 못했습니다"}

        global_text = "\n".join(
            f"- {name} ({d['ticker']}): {d['price']} ({d['change']:+.2f}%)"
            if d.get("change") is not None else f"- {name}: {d['price']}"
            for name, d in global_data.items()
        )

        user = f"""# 시각
{datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')} (직전 미장 세션 결과 기준)

# 미국 시장 스냅샷
{global_text}

지시:
- **미국 시장 관점**의 장마감 종합 brief 작성. 한국 시장 언급 최소화.
- 지수(S&P/Nasdaq/Dow), 빅테크(NVDA/TSM), 매크로(달러·유가·금리) 흐름과 인과.
- 구체 수치 인용. 추상 표현 X.

JSON:
{{
  "headline": "오늘 미장 한 줄 (구체 이벤트+숫자, 25-50자)",
  "market_summary": "**최소 5문장 (350자 이상)**. S&P/Nasdaq/Dow, 빅테크/반도체, 환율·유가·채권, 섹터 로테이션, 한국 ADR 시사점.",
  "key_news": [
    "미국 핵심 뉴스/이벤트 1 (30자 이상)", "뉴스 2", "뉴스 3", "뉴스 4 (있으면)"
  ],
  "tomorrow_checklist": [
    "다음 미장 N시 변수 1 (시간+지표+임계치, 30자 이상)",
    "변수 2", "변수 3", "변수 4 (있으면)"
  ]
}}"""

        brief = await self._llm.complete_json(
            EVENING_SYSTEM, user,
            max_tokens=self._settings.llm_max_tokens_briefing_main,
            label="evening_us:main", temperature=0.3,
        )
        if not brief:
            return {"error": "LLM 실패"}
        brief["stock_results"] = []
        return {
            "type": "evening",
            "market": "us",
            "timestamp": datetime.now(KST).isoformat(),
            "global": global_data, "portfolio": [], "brief": brief,
        }
