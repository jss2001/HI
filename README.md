# 섹터체크 (Sector Check)

이미지 시안 기반 모바일 UI — FastAPI 백엔드 + React(Vite) 프론트엔드.

## 구성
- `backend/` — FastAPI. 섹터 목록, 섹터 상세, 뉴스 API.
- `frontend/` — Vite + React. 모바일 프레임 안에 3개 화면 (섹터체크 / 섹터 상세 / 뉴스 타임라인).

## 실행

### 1. 백엔드
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. 프론트엔드
```bash
cd frontend
npm install
npm run dev
```

브라우저에서 http://localhost:5173 접속.
3개 화면을 한 번에 보려면 http://localhost:5173/#showcase

## API
- `GET /api/sectors` — hot/all 섹터 목록
- `GET /api/sectors/{id}` — 섹터 상세 (차트, 코멘트)
- `GET /api/news?tag=AI` — 날짜별 그룹된 뉴스
