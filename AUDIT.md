# HI 섹터체크 — 전체 코드 Audit & 개선 로드맵

> 백엔드 11개 모듈 (2,400 LOC) + 프론트엔드 7개 컴포넌트 (1,250 LOC) + 스타일 1,740 LOC, 총 **5,522 LOC** 풀 스캔.
> 솔직히 부족한 점 + 실질적 개선 방안을 우선순위별로 정리.

---

## 한눈에 — 가장 임팩트 큰 7가지

| 우선 | 항목 | 현재 | 개선 방안 | 예상 임팩트 |
|---|---|---|---|---|
| 🔥1 | **DART 공시 본문 미열람** | 제목만으로 분석 | XBRL/PDF 다운로드 → 핵심 추출 → LLM 입력 | 분석 깊이 10배 ↑ |
| 🔥2 | **분석 history 저장 X** | 매번 즉시 호출만 | SQLite로 누적 → Bull/Bear 적중률 추적 | 신뢰성 / 게임화 |
| 🔥3 | **알림 시스템 부재** | 푸시 X, 이메일 X | 텔레그램 봇 / 웹 PWA push | 활용도 격상 |
| 🔥4 | **사용자 인증 없음** | localStorage만 | Auth0 / Firebase Auth | 다기기 동기화 / 수익화 가능 |
| 🔥5 | **글로벌 데이터 부족** | yfinance만 | Finnhub free + EDGAR + Alpha Vantage | 토스 어닝콜 따라잡기 |
| 🔥6 | **차트 기술 지표 빈약** | RSI/MA/거래량만 | MACD / 볼린저 / 스토캐스틱 / 일목균형 | 찐고수 도구 |
| 🔥7 | **AI 출력 검증 부족** | echoed_by 외 다 LLM 신뢰 | 모든 출처 cross-check, 환각 차단 | 신뢰도 ↑ |

---

## 1. 백엔드 모듈별 진단

### 1.1 `analyst.py` (483 LOC, 가장 큼)
**부족한 점**
- SYSTEM_PROMPT가 인라인 (수정 시 코드 diff 큼)
- LLM API 실패 시 retry 없음 — 간헐적 5xx에 전체 분석 실패
- 토큰/비용 트래킹 0
- gpt-4o-mini 단일 모델 — 깊은 분석 시 부족
- echoed_by만 후처리 검증, 다른 필드는 LLM 신뢰

**개선**
1. **프롬프트 외부 분리**: `prompts/system.txt` 로 → 비개발자도 수정 가능
2. **OpenAI 자동 retry**: `tenacity` 라이브러리 + exponential backoff
3. **비용 누적 로그**: 호출당 `prompt_tokens × 0.15 + completion × 0.60` per 1M → DB 저장
4. **2단계 모델**: 초안 mini → 종합 판정 4o (cluster size 큰 종목만 4o)
5. **출력 검증 확장**: timeline 사건이 실제 공시·뉴스에 존재하는지 cross-check
6. **Bull/Bear 적중률 누적**: 시간 지나면 검증 가능 (다음 N일 주가 vs 판정)

### 1.2 `news.py` (342 LOC)
**부족한 점**
- 클러스터링 O(n²) — 50건이면 2,500 비교
- 한국어 토큰화 단순 (정규식 split)
- API 100건 한도 (페이지네이션 X)
- 같은 사건의 다른 표현 매칭 약함

**개선**
1. **형태소 분석**: `KoNLPy` (Mecab/Okt) 도입 → 명사 추출 정확도 ↑
2. **임베딩 기반 클러스터**: OpenAI `text-embedding-3-small` (저렴) → 코사인 유사도
3. **페이지네이션**: `start` 파라미터로 1000건까지
4. **클러스터 representative**: 같은 사건 N개 매체 보도 시 메이저 매체 1개만 표시 + "외 N매체"

### 1.3 `sectors.py` (230 LOC)
**부족한 점**
- ETF 매핑 6개 + 테마 ETF 10개 하드코딩
- 사용자가 새 ETF 추가 어려움
- 노이즈 키워드도 하드코딩

**개선**
1. **`config/etf_mapping.yaml`** 외부 파일로 분리
2. **자동 매핑**: LLM이 "X 테마" → "관련 ETF 추천" → ticker 검증 → 자동 추가
3. **데이터 소스 추상화**: ETF / 종목 평균 / 지수 중 선택

### 1.4 `market_data.py` (223 LOC)
**부족한 점**
- 네이버 금융 정규식이 페이지 변경에 취약
- 외인/기관 5일 매매 정확 매칭 안 됨
- 컨센서스 목표가 부분 추출

**개선**
1. **KIS Open API** (한국투자증권) — 공식 실시간, 무료, 종목당 정확
2. **KRX 정보데이터시스템** OTP 방식으로 외인·기관·공매도 정확 수치
3. **playwright/selenium 백업**: 정규식 깨질 때 헤드리스 브라우저로

### 1.5 `technicals.py` (168 LOC)
**부족한 점**
- RSI(14) / MA(5/20/60) / 거래량만
- 차트는 종가 라인만 (촛대 X)
- 매매 신호 자동화 없음

**개선**
1. **`pandas-ta` 라이브러리**: 100+ 지표 (MACD, 볼린저밴드, 스토캐스틱, ATR, 일목균형, ADX, OBV)
2. **OHLC 촛대 차트**: SVG로 직접 또는 lightweight-charts
3. **자동 매매 신호**: "골든크로스 + RSI < 50 + 거래량 ↑" → "단기 매수 시그널" 라벨링
4. **백테스트 미니**: "이 신호 과거 N회 발생, 다음 N일 평균 +X%"

### 1.6 `dart.py` (177 LOC) ⚠️ 큰 기회
**부족한 점**
- 공시 **제목만** 사용. 본문 다운로드 X
- 정기보고서 (분기·반기·연간 보고서) 안 읽음 — **재무제표 통째로 손도 안 댐**
- 별칭 사전 25개 (제한적)

**개선** (큰 임팩트)
1. **공시 본문 다운로드**: `document.json` API → ZIP → XBRL 파싱 → 핵심 항목 추출
2. **재무제표 자동 추출**: 매출/영업이익/순이익/EBITDA/부채비율/ROE 시계열
3. **별칭 사전 LLM 확장**: "이 회사의 흔한 별명 5개" → 자동 등록
4. **공시 임팩트 분류**: LLM이 공시 본문 보고 "주가에 영향: 강·중·약 / 긍·부·중립" 자동 라벨

### 1.7 `social.py` (146 LOC)
**부족한 점**
- 100건 한도 (페이지네이션 X)
- ratio 계산이 saturated 시 부정확
- sentiment는 LLM 의존만 (자체 분석 X)

**개선**
1. **페이지네이션**: start 파라미터로 1000건 — 진짜 화제성 측정
2. **시간 분포 히스토그램**: 시간별 글 수 → "오후 3시 급증" 같은 패턴
3. **자체 sentiment**: 한국어 sentiment 모델 (KoBERT 기반) — LLM 비용 절감
4. **저자 다양성**: 같은 사람 여러 글 vs 여러 사람 → 진짜 buzz 판별

### 1.8 `keyword_refiner.py` (64 LOC)
**부족한 점**
- LLM이 추천한 stocks 정확도 검증 X (환각 가능)
- 테마 ETF는 추천 안 함

**개선**
1. **stocks cross-check**: DART corp_codes에 존재하는 종목만 keep
2. **테마 ETF 자동 추천**: LLM이 yfinance에서 검증 가능한 ticker도 함께
3. **한국어 형태소 기반 검색어 확장**: "메타버스" → "VR", "AR", "디지털 트윈" 등

### 1.9 `global_stock.py` (94 LOC)
**부족한 점**
- 미국 위주 (yfinance가 한국·일본·홍콩 등 일부 지원하지만 미사용)
- 시간대 처리 없음 (NY 장 vs 한국 장)
- 글로벌 종목 → 한국 종목 영향 분석 X (예: NVDA ↑ → SK하이닉스?)

**개선**
1. **여러 시장**: `.T`(도쿄) `.HK`(홍콩) `.L`(런던) `.SS`(상해) 지원
2. **시간대 표시**: "NY 종가 시간 한국 X시"
3. **상관관계 분석**: 글로벌 종목 ↔ 한국 동일 섹터 종목 30일 상관계수

### 1.10 `main.py` (266 LOC)
**부족한 점**
- 라우터 + 비즈니스 로직 섞임
- 에러 핸들링 일관성 X (try/except pass 혼재)
- 의존성 주입 (FastAPI Depends) 미사용

**개선**
1. **APIRouter 분리**: `routers/sectors.py`, `routers/analyst.py`, `routers/themes.py`
2. **공통 에러 핸들러**: HTTPException + 전역 핸들러
3. **레이트 리밋**: `slowapi` (IP당 분당 N회)
4. **의존성 주입**: 클라이언트·LLM 클라이언트를 `Depends`로

### 1.11 `data.py` (193 LOC, 거의 죽은 파일)
- mock fallback은 거의 미사용
- sin wave 차트는 의미 없음
- **개선**: 제거 또는 진짜 백업 데이터 (CSV)

---

## 2. 프론트엔드 진단

### 2.1 `styles.css` (1,740 LOC) ⚠️ 거대 단일 파일
**부족**
- 한 파일에 모든 클래스 — 어떤 컴포넌트가 어떤 스타일 쓰는지 불명
- 클래스 충돌 위험 (네이밍 컨벤션 없음)

**개선**
1. **Tailwind CSS 도입**: 유틸리티 클래스 → 컴포넌트 안에 직접 + CSS 변수 그대로 활용
2. **또는 CSS Modules**: 컴포넌트별 `*.module.css`
3. **또는 styled-components**: JS-in-CSS, 테마 props 자연스러움

### 2.2 `AnalystScreen.jsx` (621 LOC) — 가장 복잡
**부족**
- ThreadPost / PointList / QuotedPost / MiniChart / TechSignals 모두 한 파일
- PERSONA·VERDICT_STYLE 같은 상수도 한 파일
- 단일 화면 = 하나의 큰 함수

**개선**
1. **컴포넌트 분리**:
   - `components/thread/ThreadPost.jsx`
   - `components/thread/QuotedPost.jsx`
   - `components/thread/PointList.jsx`
   - `components/chart/MiniChart.jsx`
   - `components/chart/TechSignals.jsx`
   - `screens/analyst/index.jsx` (메인 컨테이너만)
2. **데이터 페칭 hooks**: `useAnalyst(company)` / `useCompare(a, b)` 분리
3. **PERSONA 상수**: `config/personas.ts`

### 2.3 `SectorCheck.jsx` (162 LOC)
**부족**
- ThemeCard가 키워드별로 fetch → 키워드 N개면 N+1 요청
- 첫 렌더 시 깜빡임 (skeleton 없음)

**개선**
1. **`/api/themes/batch?keywords=A,B,C`** 일괄 endpoint
2. **Skeleton 로딩**: 카드 placeholder

### 2.4 `SectorDetail.jsx` (182 LOC)
**부족**
- 즐겨찾기 localStorage 단일 기기만
- 차트 클릭 인터랙션 X (호버 가격 표시)

**개선**
1. **사용자 인증 + 서버 동기화**: 다기기 즐겨찾기
2. **차트 hover tooltip**: SVG에 mouse event

### 2.5 `ThemeDetail.jsx` (151 LOC)
**부족**
- AI 분석 같은 깊이 없음 (단순 시세 + 뉴스 + buzz)
- 테마 내 대표 종목 자동 분석 안 됨

**개선**
1. **테마용 LLM 분석**: 가벼운 버전 ("이 테마 지금 뜨는 이유" 한 줄 + 대표 종목 3개 간략 분석)
2. **테마 → 종목 클릭** → AI 분석으로 deep dive

### 2.6 `NewsTimeline.jsx` (68 LOC) — 가장 단순
**부족**
- 검색 input 없음
- 무한 스크롤 X (현재는 최초 N건만)
- 뉴스 클릭 시 분석 연결 X

**개선**
1. **검색 input**: 화면 내 즉시 필터
2. **infinite scroll**: 스크롤 끝나면 추가 fetch
3. **뉴스 카드 → AI 분석**: 회사명 자동 추출 → "이 종목 분석" 버튼

### 2.7 `App.jsx` (78 LOC)
**부족**
- 자체 view state 관리 (객체 mutate)
- URL 공유 불가 (해시 라우트도 없음)
- 뒤로 가기 버튼 동작 안 함

**개선**
1. **react-router** 도입: `/sector/:id`, `/theme/:kw`, `/analyst/:company` URL
2. **브라우저 히스토리** 정상 동작
3. **공유 링크**: 분석 결과 URL로 공유

---

## 3. 인프라 / 운영 — 거의 0

| 항목 | 현재 | 추천 |
|---|---|---|
| 데이터베이스 | 메모리 캐시만 | SQLite (개발) → PostgreSQL (배포) |
| 인증 | localStorage | Auth0 / Firebase Auth (5분 셋업) |
| 알림 | 없음 | 텔레그램 봇 또는 PWA push notification |
| 모니터링 | print | Sentry (에러) + 자체 로그 (분석 비용·사용량) |
| 로깅 | print | `structlog` JSON 로그 |
| 테스트 | 0개 | pytest (백엔드 핵심 함수) + Vitest (frontend) |
| CI/CD | 없음 | GitHub Actions (lint + test + 자동 배포) |
| 배포 | 로컬만 | Railway / Fly.io / Vercel |
| 환경 분리 | dev만 | dev/staging/prod `.env` |
| 레이트 리밋 | 없음 | slowapi (분당 30) |
| CORS | `*` | 도메인 화이트리스트 |
| 시크릿 관리 | `.env` | AWS Secrets / Vault (prod) |
| 백업 | 없음 | DB snapshot + 분석 결과 S3 |

---

## 4. 데이터 — 진짜 차별화 포인트

| 데이터 | 현재 | 개선 후 가치 |
|---|---|---|
| **DART 공시 본문** | ❌ 제목만 | 정기·주요사항·잠정실적 본문 → 진짜 행간 읽기 |
| **재무제표 시계열** | ❌ | 매출/영업이익 5년 추이 → 추세·턴어라운드 자동 감지 |
| **컨센서스 (애널 평균)** | ❌ 부분 | EPS·매출·목표가 컨센 추적 → 어닝 서프라이즈 |
| **외인·기관 정확 매매** | △ 부분 | KRX 공식 → "기관이 N일 연속 매수" 시그널 |
| **공매도 잔고 추이** | △ 부분 | KRX → 공매도 급증 = 약세 시그널 |
| **신용잔고** | ❌ | KRX → 개미 빚투 비율 |
| **블록딜 / 대량매매** | ❌ | DART 공시 → 5% 룰 변동 추적 |
| **글로벌 어닝콜** | ❌ | 자동 번역 + 핵심 추출 (토스 따라잡기) |
| **EDGAR (미국 SEC)** | ❌ | 글로벌 종목 분석 시 |
| **한국 국채 수익률** | ❌ | FRED / 한은 → 매크로 영향 |
| **환율·원자재** | ❌ | yfinance → 수출주 영향 |

---

## 5. LLM — 더 똑똑하게

**현재**: gpt-4o-mini 단일 모델 + 단순 프롬프트.

**개선**
1. **2단계 모델**: 후보 mini → 핫토픽만 4o (비용 절감 + 핵심은 깊이)
2. **프롬프트 캐싱**: OpenAI prompt cache 활용 (동일 SYSTEM_PROMPT 부분 50% 할인)
3. **함수 호출 / 도구 사용**: LLM이 직접 DART API / yfinance 호출하게
4. **RAG 도입**: 분석 history를 벡터 DB에 저장 → 비슷한 과거 사례 자동 검색
5. **자기 검증**: LLM이 자기 답변을 다시 평가 ("위 분석에 환각이 있다면?" )
6. **출처 검증 자동화**: 인용된 모든 [DART], [매체] 가 실제 데이터에 존재하는지

---

## 6. UX/UI — 디테일

| 영역 | 부족 | 개선 |
|---|---|---|
| 데스크톱 레이아웃 | 모바일만 | 폰 프레임 + 사이드 패널 (대시보드 모드) |
| 다국어 | 한국어만 | i18n (영문 → 글로벌 종목 시) |
| a11y | aria-label 일부 | 전 키보드 네비, 스크린 리더 호환 |
| 첫 로딩 | 깜빡임 | Skeleton + Suspense |
| 에러 화면 | 단순 텍스트 | 친절한 일러스트 + 재시도 버튼 |
| 검색 | NewsTimeline 없음 | 글로벌 검색 (모든 화면 ⌘+K) |
| 단축키 | 없음 | Cmd+K 검색, 1~5 탭 |
| 다크모드 디테일 | 색만 변경 | 차트·sparkline 색상 미세 조정 |
| 애니메이션 | 일부 과함 | 일관된 motion 디자인 |
| 공유 카드 | 미구현 | html2canvas → 카톡·트위터 이미지 공유 |

---

## 7. 비즈니스 / 차별화

**현재**: 토스 'AI 시그널' 대비 더 풍부한 듀얼 AI + 커뮤니티 sentiment + 차트 기술 지표.

**부족**
1. **수익 모델 X** — 무료 버전만
2. **사용자 피드백 수집 X** — 분석 품질 평가 없음
3. **콘텐츠 자산화 X** — 매일 분석한 게 누적 안 됨
4. **소셜 X** — 다른 사용자와 공유·토론 X

**개선**
1. **유료 구독**:
   - 무료: 일 5회 분석 / 광고
   - Pro ₩9,900/월: 무제한 + Pro 페르소나 + 알림
   - Premium ₩29,900/월: 모델 4o + 종목 무제한 추적 + API
2. **분석 평가**: "이 분석 도움됐나요? 👍/👎" → LLM 출력 학습 데이터
3. **분석 아카이브**: "OO 종목 지난 30일 분석 추이" — 콘텐츠 자산
4. **공유 기능**: 명대사 카드 → 카톡 → 바이럴
5. **알림 봇**: 텔레그램 / 카톡 채널 → 핫토픽 자동 발송

---

## 8. 기술 부채

| 항목 | 현재 | 개선 |
|---|---|---|
| Python 버전 | 3.9 (Optional[str] 등) | 3.11+ (PEP 604 `str \| None`) |
| Node 버전 | 15 → Vite 2.9 다운그레이드 | Node 20 LTS → Vite 5 |
| 한국어/영어 메시지 혼재 | 일관성 X | 명확한 컨벤션 (UI 한글, 로그 영문) |
| 로깅 | print | structlog JSON |
| 테스트 | 0 | 핵심 함수 unit + e2e 1~2개 |
| 의존성 버전 핀 | 일부 | uv.lock / poetry.lock |

---

## 9. 보안

| 위험 | 대응 |
|---|---|
| `.env` 키들이 채팅·git history에 노출됨 | 모두 즉시 revoke 후 재발급. dotenv-vault 도입 |
| CORS `*` | 도메인 화이트리스트 |
| API 레이트 리밋 X | slowapi |
| LLM 프롬프트 인젝션 | 사용자 입력 sanitize (특수 문자 / 길이 제한) |
| SQL injection (DB 도입 시) | parameterized query 강제 |
| 클라이언트 시크릿 노출 | 백엔드 프록시로만 |

---

## 10. 실행 우선순위 추천

### 다음 1주 (MVP 완성도)
- [ ] DART 공시 본문 다운로드 + 핵심 추출
- [ ] 알림 봇 (텔레그램) — 핫토픽 자동 발송
- [ ] history.py SQLite — 분석 누적
- [ ] 명대사 공유 카드 (html2canvas)
- [ ] NewsTimeline 검색 input

### 다음 2주 (Pro급)
- [ ] 차트 지표 확장 (pandas-ta) + 촛대 차트
- [ ] 컴포넌트 리팩터 (AnalystScreen 분리)
- [ ] react-router 도입
- [ ] Auth0 인증 + 즐겨찾기 서버 동기화
- [ ] 구독 결제 (토스페이먼츠)

### 다음 1달 (확장)
- [ ] KIS Open API 통합 (실시간 시세·수급 정확도)
- [ ] 글로벌 어닝콜 자동 번역
- [ ] 임베딩 클러스터링 (텍스트-3-small)
- [ ] CI/CD (GitHub Actions)
- [ ] 배포 (Railway / Fly.io)

---

## 11. 진짜 차별화로 가는 길 (블루오션)

**아무도 안 하는데 가능한 것:**

1. **공시 + 뉴스 + 커뮤니티 모순 자동 검출**
   - 회사가 공시에서는 호재라 했는데 뉴스 행간엔 우려, 커뮤니티엔 매도 쏠림 → "주의 신호"
2. **분석가 vs AI 적중률 추적**
   - 셀사이드 리포트 목표가 vs 실제 주가 → 어떤 분석가가 정확한지 자동
3. **공시 발표 → 주가 반응 학습**
   - 같은 회사 같은 종류 공시 (자기주식 매입 등)에 과거 N회 주가 반응
   - "이번에도 비슷할 것" 패턴 매칭
4. **이상 거래 자동 감지**
   - 거래량 급증 + 외인 매도 + 공매도 증가 → "지금 뭔가 있다" 알람
5. **CEO/임원 발언 NLP**
   - 컨콜 트랜스크립트 / 공시 인용문 → 톤 변화 (자신감 ↓ = 실적 우려?)
6. **종목별 좁은 LLM**
   - "삼성전자 전문가" 같은 fine-tuned 페르소나 (RAG로 그 종목 5년치 공시 다 읽음)
7. **밸류에이션 자동 모델**
   - DCF / PER 비교 자동 → "지금 가격이 싼가?" 정량 판단

---

## 12. 마무리 — 솔직한 평가

**잘한 점:**
- ✅ 토스 'AI 시그널' 보다 듀얼 페르소나 + 사람 voice 매칭으로 한 발 앞섬
- ✅ Threads 톤 UI는 fintech에서 진짜 처음
- ✅ 한국 ETF + yfinance + DART + 네이버 통합 — 데이터 폭 넓음
- ✅ 다크/라이트/그린 테마 진짜 작동

**부족한 점:**
- ❌ 공시 본문 안 읽으니 "표면 분석" 한계
- ❌ DB 없으니 누적 가치 0
- ❌ 알림 없으니 한 번 보고 끝
- ❌ 컴포넌트 분리 안 돼서 유지보수 부담
- ❌ 보안·배포·테스트 0

**한 줄 평가:**
> "데이터 파이프라인 + AI 풀 흐름은 잘 짰다. 하지만 **저장(DB) + 알림(푸시)** 두 개 추가하면 일회성 도구 → 매일 보는 앱으로 격이 변한다."
