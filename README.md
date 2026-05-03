# opensac

예술의전당 음악당 공연 정보를 작곡가/곡 단위로 검색·필터링하는 웹 앱.

## 구성

- `web/` — Express + React (CDN, no build) 단일 페이지
- `ml/` — Python 파이프라인 (LLM 추출 + 정규화 + SQLite)
- `Dockerfile` — node:20-slim + python3 단일 컨테이너
- `.github/workflows/docker-publish.yml` — main push 시 Docker Hub로 push

## 로컬 실행

```bash
cd web
npm install
ADMIN_USER=admin ADMIN_PASS=test123 \
  OPENROUTER_API_KEY=sk-or-... \
  node server.js
# http://localhost:3000          (사용자 화면)
# http://localhost:3000/admin    (관리자, basic auth)
```

데이터 추가:
```bash
cd ml
pip install -r requirements.txt
# CSV 준비 후
OPENROUTER_API_KEY=sk-or-... python run_pipeline.py --month 2026-05 --csv data/sac_2026_05.csv
```

## Docker

```bash
docker build -t opensac .
docker run --rm -p 3000:3000 \
  -e ADMIN_USER=admin -e ADMIN_PASS=secret \
  -e OPENROUTER_API_KEY=sk-or-... \
  -v $(pwd)/data:/data \
  opensac
```

## 환경변수

| 이름 | 필수 | 기본 | 설명 |
|---|---|---|---|
| `PORT` | | 3000 | HTTP 포트 |
| `DATA_DIR` | | `/data` | SQLite + JSON 위치 |
| `OPENROUTER_API_KEY` | ✓ | | LLM 추출/정규화용 |
| `ADMIN_USER` | (admin 활성 시) | | 관리자 ID |
| `ADMIN_PASS` | (admin 활성 시) | | 관리자 비번 |

`ADMIN_USER`/`ADMIN_PASS` 미설정 시 `/admin`은 503 반환.

## 배포

ColaServerInfra의 `oci/argocd/opensac/` manifest로 ArgoCD가 자동 sync. GitHub Actions가 main push마다 `cola314/opensac:latest` 빌드/푸시.
