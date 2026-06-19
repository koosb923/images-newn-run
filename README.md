# cdn-newn-run

`cdn.newn.run` 도메인에서 사용할 FastAPI 기반 이미지 CDN 서버입니다.

이미지 업로드/목록/삭제/다운로드 API는 `api-newn-run`의 `/v1/images`에서 처리합니다. 이 서버는 공유 저장소의 `public` 파일만 정적 URL로 제공하고, `private` 파일 직접 접근은 `403`으로 차단합니다.

## 실행 정보

- 서비스명: `cdn-newn-run`
- Docker compose 서비스명: `cdn-app`
- 기본 포트: `8507`
- 기본 공개 URL: `https://cdn.newn.run`
- 기본 저장 경로: `/app/data/images`

## 환경 변수

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `IMAGE_STORAGE_DIR` | `/app/data/images` | 이미지 저장 경로 |
| `CORS_ALLOW_ORIGINS` | `*` | 쉼표 구분 CORS 허용 origin |

## API

### 헬스체크

```bash
curl http://localhost:8507/health
```

### public 이미지 조회

```bash
curl -i https://cdn.newn.run/public/articles/sample.png
```

### private 이미지 직접 조회 차단 확인

```bash
curl -i https://cdn.newn.run/private/articles/sample.png
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
docker build -t cdn-newn-run .
docker run --rm -p 8507:8507 \
  -v "$PWD/data/images:/app/data/images" \
  cdn-newn-run
```

통합 compose에 `cdn-app` 서비스가 있으면 아래 명령으로 배포합니다.

```bash
./deploy.sh
```

## 업로드 API

외부 클라이언트는 이미지 업로드/목록/삭제/다운로드를 `api-newn-run`으로 요청합니다.

```bash
curl -X POST "https://api.newn.run/v1/images/upload?api_key=$API_KEY" \
  -F "file=@sample.png" \
  -F "folder=articles" \
  -F "alt=sample image" \
  -F "visibility=private"
```

private 응답의 `image.url`은 `https://api.newn.run/v1/images/{image_id}/download` 형태이며, 기존 API 인증을 통과해야 파일을 받을 수 있습니다. public 응답의 `image.url`과 `image.public_url`은 `https://cdn.newn.run/public/...` 형태이며 바로 공개됩니다.

## 자동 배포

`main` 브랜치에 push되면 GitHub webhook이 `https://deploy.newn.run/webhook`으로 전달되고, 중앙 배포 웹훅 서버가 `./deploy.sh`를 실행해 `cdn-app` 컨테이너를 재빌드/재시작합니다.
