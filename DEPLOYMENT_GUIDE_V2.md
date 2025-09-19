# HVDC Dashboard v2.0 - 배포 가이드

## 🚀 "누르면 바로 배포·안전하게 굴러가는" 시스템 구축

이 가이드는 HVDC SKU Master Dashboard v2.0을 **Vercel 자동배포 + ENV 체계 + CI/CD**로 완전 자동화하는 방법을 설명합니다.

---

## 📋 배포 체크리스트

| 단계 | 항목 | 필수/선택 | 값/예시 |
|------|------|-----------|---------|
| ENV | `NEXT_PUBLIC_MODE` | 필수 | `A` or `B` |
| ENV | MODE_A: `NEXT_PUBLIC_PARQUET_URL_*` | 선택(모드A) | SKU/EVENTS/EXCEPTIONS Parquet URL |
| ENV | MODE_B: `DUCKDB_PATH` | 선택(모드B) | `out_recon/sku_master_v2.duckdb` |
| Vercel | Functions Runtime | 필수(모드B) | **nodejs22.x** (Edge X) |
| S3 | CORS | 필수(모드A) | GET, HEAD, `*` or 특정 Origin |
| Repo | LFS/대용량 | 권장 | `.gitattributes` + LFS, 또는 빌드시 다운로드 |
| CI | 타입·빌드 | 권장 | `tsc --noEmit`, `next build` |
| API | 캐시 | 권장 | `Cache-Control` (30–120s SWR) |
| 보안 | 비밀키 | 권장 | Parquet/DB presign 링크, 공개 저장소 주의 |

---

## 🔧 1단계: GitHub Actions CI/CD 설정

### A. GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions에서 다음 시크릿을 추가:

```
VERCEL_TOKEN=your_vercel_token
VERCEL_ORG_ID=your_vercel_org_id
VERCEL_PROJECT_ID=your_vercel_project_id
DUCKDB_DOWNLOAD_URL=https://your-s3-presigned-url/sku_master_v2.duckdb
```

### B. Vercel 토큰 생성

1. [Vercel Dashboard](https://vercel.com/account/tokens)에서 토큰 생성
2. Organization ID와 Project ID는 Vercel 프로젝트 설정에서 확인

### C. CI 파이프라인 실행 확인

```bash
git add .
git commit -m "🚀 Add CI/CD pipeline and deployment config"
git push origin master
```

GitHub Actions에서 자동으로 빌드 및 배포가 시작됩니다.

---

## 🎯 2단계: Vercel 프로젝트 설정

### A. Vercel 프로젝트 생성

1. [Vercel Dashboard](https://vercel.com/new)에서 새 프로젝트 생성
2. GitHub 저장소 `macho715/stock` 연결
3. 프레임워크: **Next.js** 자동 감지

### B. 환경 변수 설정

Vercel 프로젝트 → Settings → Environment Variables에서 추가:

#### 필수 환경 변수
```bash
NEXT_PUBLIC_MODE=B
DUCKDB_PATH=out_recon/sku_master_v2.duckdb
DEFAULT_TOLERANCE_PCT=10
```

#### MODE_A용 환경 변수 (선택사항)
```bash
NEXT_PUBLIC_PARQUET_URL_SKU=https://your-bucket.s3.amazonaws.com/data/SKU_MASTER_v2.parquet
NEXT_PUBLIC_PARQUET_URL_EVENTS=https://your-bucket.s3.amazonaws.com/data/events.parquet
NEXT_PUBLIC_PARQUET_URL_EXCEPTIONS=https://your-bucket.s3.amazonaws.com/data/exceptions_by_sku.parquet
```

#### CI/CD용 환경 변수
```bash
DUCKDB_DOWNLOAD_URL=https://your-s3-presigned-url/sku_master_v2.duckdb
```

### C. Vercel CLI로 한 번에 설정

```bash
# Vercel CLI 설치
npm i -g vercel

# 프로젝트 연결
vercel link

# 환경 변수 추가
vercel env add NEXT_PUBLIC_MODE production
vercel env add DUCKDB_PATH production
vercel env add DEFAULT_TOLERANCE_PCT production
```

---

## 🗄️ 3단계: 데이터 파일 관리

### A. Git LFS 설정 (권장)

```bash
# Git LFS 설치
git lfs install

# 대용량 파일 LFS 설정
git lfs track "*.parquet"
git lfs track "*.duckdb"
git lfs track "*.xlsx"

# 변경사항 커밋
git add .gitattributes
git commit -m "📦 Configure Git LFS for large files"
```

### B. S3 + Presigned URL 방식 (보안 권장)

1. **S3 버킷 생성 및 CORS 설정**
```json
{
  "AllowedHeaders": ["*"],
  "AllowedMethods": ["GET", "HEAD"],
  "AllowedOrigins": ["*"],
  "ExposeHeaders": ["ETag"],
  "MaxAgeSeconds": 300
}
```

2. **DuckDB 파일 업로드**
```bash
aws s3 cp out_recon/sku_master_v2.duckdb s3://your-bucket/data/
```

3. **Presigned URL 생성**
```bash
aws s3 presign s3://your-bucket/data/sku_master_v2.duckdb --expires-in 604800
```

---

## 🌐 4단계: MODE_A (Client-side) 설정

### A. Parquet 파일 S3 업로드

```bash
# Parquet 파일들을 S3에 업로드
aws s3 cp out_recon/SKU_MASTER_v2.parquet s3://your-bucket/data/
aws s3 cp out_recon/events.parquet s3://your-bucket/data/
aws s3 cp out_recon/exceptions_by_sku.parquet s3://your-bucket/data/
```

### B. CORS 설정 적용

```bash
aws s3api put-bucket-cors --bucket your-bucket --cors-configuration file://docs/s3-cors-config.json
```

### C. 환경 변수 업데이트

```bash
NEXT_PUBLIC_MODE=A
NEXT_PUBLIC_PARQUET_URL_SKU=https://your-bucket.s3.amazonaws.com/data/SKU_MASTER_v2.parquet
NEXT_PUBLIC_PARQUET_URL_EVENTS=https://your-bucket.s3.amazonaws.com/data/events.parquet
NEXT_PUBLIC_PARQUET_URL_EXCEPTIONS=https://your-bucket.s3.amazonaws.com/data/exceptions_by_sku.parquet
```

---

## 🖥️ 5단계: MODE_B (Server-side) 설정

### A. DuckDB 파일 준비

```bash
# 로컬에서 DuckDB 파일 생성
python run_recon_pipeline.py

# 파일 확인
ls -la out_recon/sku_master_v2.duckdb
```

### B. 환경 변수 설정

```bash
NEXT_PUBLIC_MODE=B
DUCKDB_PATH=out_recon/sku_master_v2.duckdb
DEFAULT_TOLERANCE_PCT=10
```

### C. 빌드 시 DuckDB 다운로드

CI/CD 파이프라인에서 자동으로 `DUCKDB_DOWNLOAD_URL`에서 파일을 다운로드합니다.

---

## 🔍 6단계: 배포 검증

### A. API 엔드포인트 테스트

```bash
# KPI API 테스트
curl https://your-app.vercel.app/api/kpi

# 3-Way Reconciliation 테스트
curl "https://your-app.vercel.app/api/3way?tol=10"

# Heatmap API 테스트
curl https://your-app.vercel.app/api/heatmap

# Case Flow API 테스트
curl https://your-app.vercel.app/api/caseflow
```

### B. 응답 시간 및 캐시 헤더 확인

```bash
# 응답 시간 측정
curl -w "@curl-format.txt" -o /dev/null -s https://your-app.vercel.app/api/kpi

# 캐시 헤더 확인
curl -I https://your-app.vercel.app/api/kpi
```

### C. 예상 응답

```json
{
  "total": 6791,
  "mismatch_pct": 15.2,
  "flow_coverage": 100.0,
  "stock_coverage": 85.5,
  "sqm_coverage": 100.0,
  "location_count": 12
}
```

---

## 📊 7단계: 성능 최적화

### A. 캐시 설정 확인

Vercel에서 다음 캐시 헤더가 자동 적용됩니다:

- `/api/kpi`: 120초 캐시 + 600초 stale-while-revalidate
- `/api/heatmap`: 300초 캐시 + 1800초 stale-while-revalidate
- `/api/*`: 60초 캐시 + 300초 stale-while-revalidate

### B. 지역 설정

```json
{
  "regions": ["icn1", "hnd1"]
}
```

한국(icn1)과 일본(hnd1) 지역에서 실행되어 아시아 지역 최적화됩니다.

### C. 함수 메모리 및 타임아웃

```json
{
  "runtime": "nodejs22.x",
  "memory": 1024,
  "maxDuration": 30
}
```

1GB 메모리, 30초 최대 실행 시간으로 설정되어 있습니다.

---

## 🚨 8단계: 모니터링 및 알림

### A. Vercel Analytics 설정

1. Vercel 프로젝트 → Analytics 탭
2. Web Analytics 활성화
3. Performance Insights 모니터링

### B. 에러 모니터링

```bash
# Sentry 설정 (선택사항)
SENTRY_DSN=your_sentry_dsn
```

### C. 알림 설정

```bash
# Telegram 봇 설정
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Webhook 설정
WEBHOOK_URL=https://your-webhook-url
```

---

## 🔄 9단계: 자동화 워크플로우

### A. 개발 → 스테이징 → 프로덕션

1. **개발**: `feature/*` 브랜치 → Preview 배포
2. **스테이징**: `staging` 브랜치 → Staging 배포
3. **프로덕션**: `master` 브랜치 → Production 배포

### B. 데이터 업데이트 워크플로우

1. **야간 배치**: Python 스크립트로 데이터 처리
2. **S3 업로드**: 새로운 DuckDB/Parquet 파일 업로드
3. **Presigned URL 갱신**: 새로운 다운로드 URL 생성
4. **자동 배포**: GitHub Actions로 새 데이터로 재배포

---

## 📈 10단계: KPI 모니터링

### A. 성능 지표

- **API 응답 시간**: p95 < 400ms 목표
- **배포 성공률**: 100% 목표
- **에러율**: < 0.5% 목표
- **캐시 히트율**: > 90% 목표

### B. 비즈니스 지표

- **데이터 정확도**: ≥ 99.0% 목표
- **사용자 만족도**: > 4.5/5.0 목표
- **시스템 가용성**: 99.9% 목표

---

## 🎯 배포 완료 체크리스트

- ✅ GitHub Actions CI/CD 파이프라인 구동
- ✅ Vercel 프로젝트 연결 및 환경 변수 설정
- ✅ DuckDB/Parquet 파일 S3 업로드 (MODE_A) 또는 로컬 배포 (MODE_B)
- ✅ API 엔드포인트 정상 응답 확인
- ✅ 캐시 헤더 및 성능 최적화 적용
- ✅ 모니터링 및 알림 시스템 구축
- ✅ 자동화 워크플로우 테스트

---

## 🚀 다음 단계

1. **실제 데이터 연동**: HVDC 프로젝트 데이터와 연결
2. **사용자 인증**: 로그인/권한 관리 시스템 추가
3. **고급 분석**: 머신러닝 기반 예측 기능 추가
4. **모바일 앱**: React Native 기반 모바일 앱 개발

---

**🎉 축하합니다! HVDC Dashboard v2.0이 완전 자동화된 배포 시스템으로 구축되었습니다!**

**"누르면 바로 배포·안전하게 굴러가는" 시스템이 완성되었습니다!** 🚀

---

**문서 작성일**: 2025년 9월 20일  
**버전**: v2.0  
**작성자**: MACHO-GPT v3.4-mini  
**프로젝트**: HVDC SKU Master Dashboard  

---

*이 문서는 HVDC Dashboard v2.0의 완전 자동화된 배포 시스템 구축을 위한 종합 가이드입니다.*
