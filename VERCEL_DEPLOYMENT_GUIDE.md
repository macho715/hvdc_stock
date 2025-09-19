# HVDC Stock Dashboard - Vercel 배포 가이드

## 🚀 배포 현황
- **프로젝트**: hvdc-stock  
- **저장소**: macho715/hvdc_stock
- **프레임워크**: Next.js (자동 감지)
- **상태**: 배포 진행중

## ⚙️ 필수 환경 변수 설정

배포 완료 후 Vercel 대시보드에서 다음 환경 변수를 설정하세요:

### 🔧 기본 설정
```env
NEXT_PUBLIC_MODE=B
DUCKDB_PATH=out_recon/sku_master_v2.duckdb
DEFAULT_TOLERANCE_PCT=10
DEBUG=false
```

### 🛡️ 보안 설정
```env
ALLOWED_ORIGINS=https://hvdc-stock.vercel.app
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW=60000
```

### 📊 데이터 설정
```env
DATA_REFRESH_INTERVAL=60
MAX_DATA_AGE=120
ENABLE_DATA_VALIDATION=true
```

## 🔄 배포 후 체크리스트

- [ ] 대시보드 로딩 확인
- [ ] KPI 카드 데이터 표시 확인  
- [ ] 3-way 테이블 기능 테스트
- [ ] 히트맵 차트 렌더링 확인
- [ ] API 엔드포인트 응답 테스트

## 🐛 문제 해결

### 빌드 실패 시
1. `package.json` 의존성 확인
2. TypeScript 오류 수정
3. 환경 변수 설정 확인

### 데이터 로딩 실패 시
1. DuckDB 파일 경로 확인
2. 파일 권한 설정
3. MODE 설정 검증

## 📞 지원

배포 중 문제 발생 시:
- Vercel 빌드 로그 확인
- 환경 변수 재설정
- GitHub 저장소 동기화 확인

---
**MACHO-GPT v3.4-mini | HVDC Project Deployment Guide**
