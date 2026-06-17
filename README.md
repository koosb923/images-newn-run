# images-newn-run

`images.newn.run` 도메인에서 사용할 FastAPI 기반 이미지 업로드/정적 서빙 서버입니다.

## 실행 정보

- 서비스명: `images-newn-run`
- Docker compose 서비스명: `images-app`
- 기본 포트: `8507`
- 기본 공개 URL: `https://images.newn.run`
- 기본 저장 경로: `/app/data/images`

## 환경 변수

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | `https://images.newn.run` | 업로드 응답에 포함할 공개 URL |
| `IMAGE_STORAGE_DIR` | `/app/data/images` | 이미지 저장 경로 |
| `MAX_UPLOAD_SIZE_MB` | `20` | 업로드 최대 크기 |
| `IMAGE_SERVER_API_KEY` | 빈 값 | 설정하면 `X-API-Key` 헤더가 있어야 업로드/삭제 가능 |
| `CORS_ALLOW_ORIGINS` | `*` | 쉼표 구분 CORS 허용 origin |

## API

### 헬스체크

```bash
curl http://localhost:8507/health
```

### 이미지 업로드

```bash
curl -X POST http://localhost:8507/v1/images \
  -H "X-API-Key: $IMAGE_SERVER_API_KEY" \
  -F "file=@sample.png" \
  -F "folder=articles" \
  -F "alt=sample image"
```

응답의 `image.url`은 `https://images.newn.run/images/...` 형태입니다.

### 목록 조회

```bash
curl "http://localhost:8507/v1/images?limit=50"
```

### 메타데이터 조회

```bash
curl http://localhost:8507/v1/images/{image_id}
```

### 삭제

```bash
curl -X DELETE http://localhost:8507/v1/images/{image_id} \
  -H "X-API-Key: $IMAGE_SERVER_API_KEY"
```

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
IMAGE_STORAGE_DIR=./data/images uvicorn app.main:app --host 0.0.0.0 --port 8507 --reload
```

## Docker 실행

```bash
docker build -t images-newn-run .
docker run --rm -p 8507:8507 \
  -e PUBLIC_BASE_URL=https://images.newn.run \
  -v "$PWD/data/images:/app/data/images" \
  images-newn-run
```

통합 compose에 `images-app` 서비스가 있으면 아래 명령으로 배포합니다.

```bash
./deploy.sh
```
