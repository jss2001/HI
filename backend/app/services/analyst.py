"""Bull · Bear · Judge 페르소나 + 커뮤니티 sentiment + 시장 데이터 종합 분석."""
import asyncio
import re
from typing import Optional

import httpx
from cachetools import TTLCache

from app.clients.dart import DartClient
from app.clients.llm import LLMClient
from app.clients.naver_finance import NaverFinanceClient
from app.clients.naver_search import NaverSearchClient
from app.clients.yfinance import YFinanceClient, is_global_ticker
from app.config import Settings, get_settings
from app.core.technicals import TechnicalAnalyzer
from app.services.social import SocialService


SYSTEM_PROMPT = """당신은 한국 주식 분석 시스템. **2명의 인플루언서가 양 시각으로 분석하고 1명의 중재자가 종합 판정**한다.

## 페르소나 (단호한 톤 필수)

1. **🐂 Bull (강세론자 김불, 10년 전업 적극파)**
   - 톤: 자신감 폭발. **"사라" / "지금이 매수타임" / "안 사면 후회한다"**.
   - "권유하지는 않습니다만~" 같은 흐릿한 표현 금지.
   - 위트 OK. 입담 강하게.

2. **🐻 Bear (약세론자 박베어, 前 헤지펀드 RM 13년)**
   - 톤: 냉정·단호. **"지금 사면 물린다" / "현금 들고 기다려라" / "절대 비추"**.
   - 냉소적 표현 OK. ("호재? 이미 다 반영됐다." 같은)

3. **⚖️ Judge (중재자)**
   - 톤: 차분·객관적. 양쪽 논리 평가 후 명확한 비중 판정.

## 핵심 원칙

- 흐릿한 표현 X. **단호하게.**
- 모든 주장 옆 출처 표기 ([DART], [매일경제] 등)
- 사실(공시/뉴스 인용)과 해석(분석) 구분
- 각 시각마다 **커뮤니티 글에서 같은 톤의 진짜 사람 글을 인용**(echoed_by) — 사람 voice가 AI 옆에 있어야 신뢰가 생긴다.

핵심 원칙 (매우 중요):
- **타겟은 일반 개인 투자자**. 분석가/기관 X.
- 전문 용어는 풀어쓰기 (예: HBM → "고대역폭 메모리(AI 칩에 들어감)")
- 한국어, 친근한 톤. 단정적 투자권유 표현 X ("매수 추천" X, "이런 시각이 있어요" O)
- 모든 주장 옆에 출처 표기 (예: [DART 2026.04.24], [매일경제])
- 사실(공시·뉴스 인용)과 해석(분석)을 구분

**반드시 아래 JSON 스키마로 응답:**
{
  "headline": "한 줄(15-35자). 절대 일반론 X. 구체적 이벤트/숫자/주체를 포함. 좋음 예: '노무라 목표가 234만원 상향 + 노조 파업 D-3' / 나쁨: '반도체 호황 속 변수 존재'",
  "bull": {
    "thesis": "왜 사도 될지 한 문장 (적극·자신감, '사라/지금이 매수타임' 톤)",
    "single_quote": "Bull의 한마디 명대사 (트위터/스레드 식 강한 한 줄, 위트 OK, 12-30자)",
    "points": [
      {"text": "강세 근거 1 (가능하면 PER/외인순매수/목표가 등 시장 수치 인용)", "sources": ["DART...", "매일경제"]},
      {"text": "강세 근거 2", "sources": [...]},
      {"text": "강세 근거 3", "sources": [...]}
    ],
    "weakness": "이 시각이 틀릴 수 있는 한 가지 (Bull 본인이 인정)",
    "echoed_by": [
      {"title": "커뮤니티 글 리스트에서 강세 톤 글 제목 1~2개 글자 그대로. 본문은 시스템이 채움."}
    ]
  },
  "bear": {
    "thesis": "왜 조심해야 할지 한 문장 (냉정·단호, '물린다/현금 들고 가라' 톤)",
    "single_quote": "Bear의 한마디 명대사 (냉소·위트 OK, 12-30자)",
    "points": [
      {"text": "약세 근거 1 (가능하면 공매도/외인순매도/PER 고평가 등 시장 수치 인용)", "sources": [...]},
      {"text": "약세 근거 2", "sources": [...]},
      {"text": "약세 근거 3", "sources": [...]}
    ],
    "weakness": "이 시각이 틀릴 수 있는 한 가지",
    "echoed_by": [
      {"title": "약세 톤 글 제목 글자 그대로 (커뮤니티 리스트에서)"}
    ],
    "rebuts_bull": "Bull의 thesis에 대한 한 줄 반박 (직접적·날카롭게)"
  },
  "judge": {
    "verdict": "BULL_WINS | BEAR_WINS | TIE | NEEDS_MORE_DATA",
    "confidence": 0-100,
    "reasoning": "왜 그렇게 봤는지, 2~3문장 쉬운 말로",
    "swing_factor": "이 판단이 바뀔 수 있는 하나의 변수 (쉬운 말로)"
  },
  "today_one_thing": "만약 오늘 이 종목에 대해 단 한 가지만 알아야 한다면? 한 문장",
  "for_holders": "이 종목을 갖고 있는 사람을 위한 한 줄 (관망/주시할 포인트 등, 권유 X)",
  "for_non_holders": "갖고 있지 않은 사람을 위한 한 줄 (지켜볼 포인트 등, 권유 X)",
  "timeline": [
    {
      "date": "YYYY.MM.DD",
      "event": "한 줄 이벤트 요약 (간결, 사실)",
      "kind": "filing | news | earnings",
      "vibe": "positive | negative | neutral",
      "why_matters": "이 사건이 주가/회사에 왜 의미 있는지 1줄 (해석)"
    },
    "최대 6개. 의미 있는 사건만. 시간 역순 (최근이 위)."
  ],
  "trend_summary": "기간 동안의 변화/추세 한 줄. 변화가 약하면 빈 문자열.",
  "tech_take": "차트 기술적 지표 한 줄 해석 (RSI/이평/거래량/크로스 종합). 데이터 없으면 빈 문자열. 예: 'RSI 73 과매수 + 5일선 20일선 위 돌파 — 단기 추가 상승 부담'",
  "sentiment": {
    "score": -100~100 (정수). 매핑 엄격: 80+ '매우 긍정' / 30~79 '긍정' / -29~29 '중립' / -30~-79 '부정' / -80- '매우 부정',
    "label": "위 매핑에 따라 한 라벨 선택",
    "summary": "투자자 커뮤니티 분위기 한 줄 (블로그·카페 글 기반)",
    "tone_notes": "자주 등장하는 표현 1~3개 (예: '실망', '환호', '관망'). 글 없으면 빈 문자열"
  },
  "data_quality": "데이터 충분 / 공시 부족 / 뉴스 부족 / 둘 다 부족 중 택1"
}"""


def _format_filings(filings: list) -> str:
    if not filings:
        return "(최근 7일 공시 없음)"
    return "\n".join(
        f"- [{f['date']}] {f['report_nm']} (제출자: {f['submitter']})"
        for f in filings[:15]
    )


def _format_news(news: list) -> str:
    if not news:
        return "(최근 뉴스 없음)"
    lines = []
    for n in news[:15]:
        cluster = f" [{n.get('cluster_size', 1)}매체보도]" if n.get("cluster_size", 1) > 1 else ""
        lines.append(f"- [{n['source']} {n['time']}]{cluster} {n['title']}")
    return "\n".join(lines)


def _enrich_echoed_by(brief: dict, posts: list) -> None:
    """LLM이 echoed_by에 적은 title을 실제 글로 매칭. 매칭 실패 항목은 제거."""
    if not posts:
        for side in ("bull", "bear"):
            brief.setdefault(side, {})["echoed_by"] = []
        return

    by_title = {p["title"]: p for p in posts}

    def _tokens(s: str) -> set:
        return {w for w in re.split(r"[\s\(\)\[\]<>《》「」!?,.…-]+", s) if len(w) >= 2}

    def find_post(needle: str):
        if not needle:
            return None
        if needle in by_title:
            return by_title[needle]
        nt = _tokens(needle)
        if not nt:
            return None
        best, best_overlap = None, 0
        for p in posts:
            pt = _tokens(p["title"])
            if not pt:
                continue
            overlap = len(nt & pt)
            if overlap > best_overlap and overlap >= max(2, len(nt) // 2):
                best_overlap, best = overlap, p
        return best

    for side in ("bull", "bear"):
        echoed = (brief.get(side) or {}).get("echoed_by") or []
        enriched, seen = [], set()
        for e in echoed:
            real = find_post(e.get("title", ""))
            if not real or real["link"] in seen:
                continue
            seen.add(real["link"])
            enriched.append({
                "source": real["source"], "title": real["title"],
                "snippet": real["snippet"], "date": real["date"],
                "link": real["link"], "verified": True,
            })
            if len(enriched) >= 2:
                break
        brief.setdefault(side, {})["echoed_by"] = enriched


class AnalystService:
    """generate(query) → {company, brief(JSON), buzz, market, sources, ...}."""

    def __init__(
        self,
        dart: Optional[DartClient] = None,
        naver: Optional[NaverSearchClient] = None,
        naver_fin: Optional[NaverFinanceClient] = None,
        yfinance: Optional[YFinanceClient] = None,
        technicals: Optional[TechnicalAnalyzer] = None,
        social: Optional[SocialService] = None,
        llm: Optional[LLMClient] = None,
        settings: Optional[Settings] = None,
    ):
        self._dart = dart or DartClient()
        self._naver = naver or NaverSearchClient()
        self._naver_fin = naver_fin or NaverFinanceClient()
        self._yf = yfinance or YFinanceClient()
        self._tech = technicals or TechnicalAnalyzer()
        self._social = social or SocialService(self._naver)
        self._llm = llm or LLMClient()
        self._settings = settings or get_settings()
        self._cache = TTLCache(maxsize=64, ttl=3600)

    async def generate(self, company_query: str, market: str = "kr") -> Optional[dict]:
        if not self._llm.available:
            return {"error": "OPENAI_API_KEY 없음"}

        q = company_query.strip()

        # US 모드 — yfinance Search로 한국어/영문명 → ticker 해석
        if market == "us":
            if is_global_ticker(q):
                return await self._generate_global(q)
            results = self._yf.search_us(q, limit=1)
            if results:
                return await self._generate_global(results[0]["stock_code"])
            return {"error": f"'{company_query}' 미국 종목을 찾을 수 없습니다"}

        # KR (기본) — 영문 ticker는 글로벌, 그 외 DART
        if is_global_ticker(q):
            return await self._generate_global(q)

        corp = self._dart.find(company_query)
        if not corp:
            return {"error": f"'{company_query}' 종목을 찾을 수 없습니다"}

        key = f"brief:{corp['corp_code']}"
        if key in self._cache:
            return self._cache[key]

        aliases = self._dart.aliases_for(corp["corp_name"])
        exclusions = []
        for term in [corp["corp_name"]] + aliases:
            exclusions += self._dart.find_similar_names(term, exclude=corp["corp_name"])
        exclusions = list(set(exclusions))

        # 데이터 수집 병렬
        news_task = self._fetch_news_for_company(corp["corp_name"], aliases, exclusions)
        buzz_task = self._social.fetch_buzz(corp["corp_name"], aliases, exclusions)
        finance_task = self._naver_fin.fetch_main(corp["stock_code"])
        flow_task = self._naver_fin.fetch_trading_flow(corp["stock_code"])
        short_task = self._naver_fin.fetch_short_selling(corp["stock_code"])
        news, buzz, naver_fin, flow, short = await asyncio.gather(
            news_task, buzz_task, finance_task, flow_task, short_task
        )
        yf_fin = self._yf.get_kr_info(corp["stock_code"])
        finance = NaverFinanceClient.merge(naver_fin, yf_fin)
        tech = self._tech.analyze(corp["stock_code"])

        filings = []
        period_days = 7
        for days in (7, 30, 90, 180):
            filings = await self._dart.get_filings(corp["corp_code"], days=days, limit=30)
            period_days = days
            if len(filings) >= 3:
                break

        period_label = {7: "최근 7일", 30: "최근 30일", 90: "최근 3개월",
                        180: "최근 6개월"}.get(period_days, f"최근 {period_days}일")

        prompt = self._build_prompt(corp, finance, flow, short, tech,
                                    filings, news, buzz, period_label)
        brief = await self._llm.complete_json(
            SYSTEM_PROMPT, prompt,
            max_tokens=self._settings.llm_max_tokens_analyst,
            label=f"analyst:{corp['corp_name']}",
            temperature=0.5,
        )
        if not brief:
            return {"error": "LLM 호출 실패"}

        _enrich_echoed_by(brief, (buzz or {}).get("posts", []))

        result = {
            "company": corp["corp_name"], "stock_code": corp["stock_code"],
            "corp_code": corp["corp_code"], "period_days": period_days,
            "brief": brief, "buzz": buzz,
            "market": {"finance": finance, "flow": flow, "short": short, "tech": tech},
            "sources": {
                "filings": filings[:15],
                "news": [{k: v for k, v in n.items() if not k.startswith("_")} for n in news[:15]],
            },
            "model": self._settings.llm_model_default,
        }
        self._cache[key] = result
        return result

    # ── 내부: 종목 뉴스 검색 (별칭 + 동음 회사 제외) ──
    async def _fetch_news_for_company(
        self, company: str, aliases: list, exclusions: list
    ) -> list:
        terms = [company] + aliases
        async with httpx.AsyncClient(timeout=self._settings.http_timeout_default) as c:
            results = await asyncio.gather(
                self._naver.search_news(c, f'"{company}"', 100, tag=company),
                self._naver.search_news(c, company, 100, tag=company),
                *(self._naver.search_news(c, a, 100, tag=company) for a in aliases),
            )
        seen, out = set(), []
        for items in results:
            for it in items:
                if it["link"] in seen:
                    continue
                seen.add(it["link"])
                title = it.get("title", "")
                if any(ex in title for ex in exclusions) and company not in title:
                    continue
                if any(name in title for name in terms):
                    out.append(it)
        return out[:30]

    # ── 내부: 한국 종목 user prompt 빌드 ──
    @staticmethod
    def _build_prompt(corp, finance, flow, short, tech, filings, news, buzz, period_label) -> str:
        market_section = ""
        if finance:
            parts = []
            if finance.get("price"): parts.append(f"현재가: {finance['price']:,}원")
            if finance.get("change_pct") is not None:
                parts.append(f"등락률: {finance['change_pct']:+.2f}%")
            if finance.get("per"): parts.append(f"PER: {finance['per']}")
            if finance.get("pbr"): parts.append(f"PBR: {finance['pbr']}")
            if finance.get("target_price"): parts.append(f"애널리스트 목표가: {finance['target_price']:,}원")
            if finance.get("foreign_ratio"): parts.append(f"외국인 보유율: {finance['foreign_ratio']}%")
            if finance.get("high_52w"): parts.append(f"52주 최고: {finance['high_52w']:,}")
            if finance.get("low_52w"): parts.append(f"52주 최저: {finance['low_52w']:,}")
            if parts:
                market_section += "\n# 시세·밸류에이션·컨센서스\n" + " · ".join(parts)
        if flow and flow.get("days"):
            recent = flow["days"][:3]
            lines = "\n".join(
                f"- {d['date']}: 외인 {d.get('foreign_net',0):+,}주 / 기관 {d.get('institution_net',0):+,}주"
                for d in recent
            )
            market_section += f"\n\n# 외국인·기관 순매매 (최근 일자별)\n{lines}"
            market_section += (
                f"\n5일 누적: 외인 {flow.get('foreign_5d_net',0):+,}주, "
                f"기관 {flow.get('institution_5d_net',0):+,}주"
            )
        if short and short.get("short_ratio_pct"):
            market_section += f"\n\n# 공매도 잔고: {short['short_ratio_pct']}%"
        if tech:
            tparts = []
            if tech.get("rsi") is not None: tparts.append(f"RSI(14): {tech['rsi']} ({tech['rsi_label']})")
            if tech.get("ma_align"): tparts.append(f"이평선: {tech['ma_align']}")
            if tech.get("cross_event"): tparts.append(f"⚠️ {tech['cross_event']} 발생")
            if tech.get("vol_label") and tech.get("vol_label") != "—":
                tparts.append(f"거래량: {tech['vol_label']} ({tech.get('vol_ratio','')}배)")
            if tparts:
                market_section += "\n\n# 차트 기술적 지표\n" + " · ".join(tparts)

        buzz_section = ""
        if buzz and buzz.get("posts"):
            lines = []
            for p in buzz["posts"][:18]:
                snippet = (p.get("snippet") or "").strip().replace("\n", " ")
                lines.append(f'- [{p["source"]}] "{p["title"]}"\n    └ {snippet[:180]}')
            buzz_section = (
                f"\n# 투자자 커뮤니티 글 ({len(buzz['posts'])}건)\n"
                f"화제성: {buzz['buzz_label']} · 3일 {buzz['counts']['recent_3d']}건, "
                f"1주 {buzz['counts']['recent_week']}건, 1개월 {buzz['counts']['recent_month']}건\n"
                + "\n".join(lines)
            )

        return f"""# 분석 대상
{corp['corp_name']} ({corp['stock_code']})
{market_section}

# DART 공시 ({period_label}, {len(filings)}건)
{_format_filings(filings)}

# 뉴스 (네이버 검색, 제목 매칭, {len(news)}건)
{_format_news(news)}
{buzz_section}
지시사항:
- 위 데이터를 종합해 듀얼 시각 + 시계열 + sentiment 브리프를 JSON으로.
- 공시 부족하면 {period_label}로 확장된 흐름을 timeline + trend_summary에 반영.
- bull.echoed_by / bear.echoed_by: 위 커뮤니티 글 중 강세/약세 톤 글 1~2개씩 인용. 제목은 글 그대로. 글 없으면 빈 배열.
- bear.rebuts_bull: Bull thesis 직접 반박 한 줄.
- sentiment.score: 블로그·카페 글의 톤 반영. 글 없으면 score 0, label "중립".
- 공시·뉴스 부족하면 data_quality에 표시."""

    # ── 글로벌 종목 분기 ──
    async def _generate_global(self, ticker: str) -> Optional[dict]:
        key = f"brief_g:{ticker}"
        if key in self._cache:
            return self._cache[key]

        info = self._yf.get_global_info(ticker)
        if not info:
            return {"error": f"글로벌 종목 '{ticker}'을(를) 찾을 수 없습니다"}

        news = self._yf.get_global_news(ticker, limit=15)
        news_text = "\n".join(
            f"- [{n['source']}] {n['title']} ({n['time']})" for n in news[:15]
        ) or "(뉴스 없음)"

        pe = f"{info['pe_ratio']:.1f}" if info.get("pe_ratio") else "N/A"
        mcap = f"${info['market_cap']/1e9:.1f}B" if info.get("market_cap") else "N/A"
        price = f"{info.get('price','N/A')} {info.get('currency','')}"
        chg = f"{info.get('change_pct',0):.2f}%" if info.get("change_pct") is not None else ""

        user = f"""# 분석 대상 (글로벌)
{info['name']} ({ticker}, {info.get('exchange','')})
섹터/산업: {info.get('sector','')} / {info.get('industry','')}
국가: {info.get('country','')}
가격: {price} ({chg})
시가총액: {mcap}, P/E: {pe}

# 회사 개요
{info.get('summary','')}

# Yahoo Finance 최근 뉴스 ({len(news)}건)
{news_text}

지시:
- 한국 종목과 동일 JSON 스키마. DART 공시 X 이므로 timeline은 뉴스/실적 위주.
- sentiment는 뉴스 톤만으로. 글 없으면 0/중립.
- buzz 빈 객체. 출처는 [Yahoo], [Reuters] 등."""

        brief = await self._llm.complete_json(
            SYSTEM_PROMPT, user,
            max_tokens=self._settings.llm_max_tokens_analyst,
            label=f"analyst:{ticker}", temperature=0.5,
        )
        if not brief:
            return {"error": "LLM 호출 실패"}

        result = {
            "company": info["name"], "stock_code": ticker, "corp_code": ticker,
            "period_days": 0, "brief": brief, "buzz": None,
            "global_info": info,
            "sources": {
                "filings": [],
                "news": [
                    {"id": str(hash(n.get("link", n["title"]))),
                     "date": n.get("time", ""), "time": n.get("time", ""),
                     "tag": "global", "title": n["title"],
                     "summary": n.get("summary", ""), "source": n.get("source", ""),
                     "link": n.get("link", "")}
                    for n in news[:15]
                ],
            },
            "model": self._settings.llm_model_default,
        }
        self._cache[key] = result
        return result
