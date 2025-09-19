# GitHub 저장소 설정 완료

## 📍 저장소 정보
- **URL**: https://github.com/macho715/stock
- **브랜치**: main
- **마지막 커밋**: 5155767 - Initial commit: HVDC SKU Master Dashboard v2.0

## 🚀 다음 단계

### 1. Vercel 배포
```bash
# Vercel CLI 설치
npm i -g vercel

# 프로젝트 디렉토리에서 배포
vercel

# 환경 변수 설정
vercel env add DUCKDB_PATH
vercel env add DEFAULT_TOLERANCE_PCT
vercel env add NEXT_PUBLIC_MODE
```

### 2. GitHub Pages 설정 (선택적)
1. GitHub 저장소 → Settings → Pages
2. Source: Deploy from a branch
3. Branch: main / folder: / (root)
4. Save

### 3. 환경 변수 설정
GitHub 저장소 → Settings → Secrets and variables → Actions에서:
- `DUCKDB_PATH`: out_recon/sku_master_v2.duckdb
- `DEFAULT_TOLERANCE_PCT`: 10
- `NEXT_PUBLIC_MODE`: B

## 📁 업로드된 파일 구조
```
stock/
├── app/                    # Next.js App Router
│   ├── (dashboard)/       # 대시보드 페이지
│   └── api/              # API 엔드포인트
├── lib/                   # 유틸리티 함수
├── out_recon/            # 데이터 파일
├── .vercel/              # Vercel 설정
├── vercel.json           # 배포 설정
├── package.json          # 의존성
├── README.md             # 프로젝트 문서
└── V0_PROMPT.md          # v0.app 프롬프트
```

## 🔗 링크
- **저장소**: https://github.com/macho715/stock
- **v0 프롬프트**: V0_PROMPT.md 파일 참조
- **배포 가이드**: README.md 참조

## ✅ 완료된 작업
- [x] Git 저장소 초기화
- [x] 모든 파일 커밋
- [x] GitHub 원격 저장소 연결
- [x] 메인 브랜치 푸시
- [x] 데이터 파일 포함 (DuckDB + Parquet)

## 🎯 배포 준비 완료!
GitHub 저장소에 HVDC SKU Master Dashboard v2.0이 성공적으로 업로드되었습니다.
Vercel 또는 다른 플랫폼에서 바로 배포할 수 있습니다.
