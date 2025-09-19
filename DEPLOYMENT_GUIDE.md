# HVDC SKU Master Hub - 배포 가이드

## 📋 개요

이 가이드는 HVDC SKU Master Hub v2.0 시스템의 설치, 설정, 운영 방법을 상세히 설명합니다.

## 🛠️ 시스템 요구사항

### 1. 하드웨어 요구사항
```
💻 최소 요구사항:
├── CPU: Intel i5 또는 동등한 성능
├── RAM: 8GB (권장 16GB)
├── Storage: 10GB 여유 공간
└── Network: 인터넷 연결 (AWS 배포시)

💻 권장 요구사항:
├── CPU: Intel i7 또는 동등한 성능
├── RAM: 16GB (권장 32GB)
├── Storage: 50GB SSD 여유 공간
└── Network: 안정적인 인터넷 연결
```

### 2. 소프트웨어 요구사항
```
🐍 Python 환경:
├── Python: 3.11+ (테스트: 3.12.4)
├── pip: 최신 버전
└── 가상환경 권장 (venv, conda)

📦 필수 패키지:
├── pandas: 2.3.2+
├── duckdb: 1.4.0+
├── openpyxl: 최신 버전
├── numpy: 최신 버전
└── pytest: 테스트용 (선택적)
```

## 📦 설치 방법

### 1. 환경 설정

#### 1.1 Python 가상환경 생성
```bash
# Windows
python -m venv hvdc_env
hvdc_env\Scripts\activate

# Linux/Mac
python3 -m venv hvdc_env
source hvdc_env/bin/activate
```

#### 1.2 필수 패키지 설치
```bash
# 기본 패키지 설치
pip install pandas duckdb openpyxl numpy pytest

# 또는 requirements.txt 사용 (생성 예정)
pip install -r requirements.txt
```

### 2. 프로젝트 구조 확인

```
📁 프로젝트 구조:
Stock/
├── adapters (1)/                    # 데이터 어댑터
│   ├── invoice_adapter (1).py       # Invoice 처리
│   ├── reporter_adapter_v2.py       # Reporter v2 (새로움)
│   └── stock_adapter_v2.py          # Stock v2 (새로움)
├── hub (1)/                         # SKU Master Hub
│   ├── sku_master (1).py            # 원본 Hub
│   └── sku_master_v2.py             # Hub v2 (새로움)
├── recon/                           # Reconciliation 엔진
│   ├── reconciliation_engine.py     # 삼중 대조 엔진
│   └── exceptions_bridge.py         # 예외 브리지
├── config/                          # 설정 파일
│   └── recon_settings.py            # 통합 설정
├── enhanced_sku_utils.py            # 핵심 유틸리티
├── run_recon_pipeline.py            # 메인 실행 스크립트
├── test_enhanced_features.py        # 테스트 스위트
└── 데이터 파일들...
```

### 3. 데이터 파일 준비

#### 3.1 필수 데이터 파일
```
📊 필수 파일:
├── HVDC_excel_reporter_final_sqm_rev.xlsx    # HITACHI/SIEMENS 데이터
├── HVDC_Stock On Hand Report (1).xlsx        # Stock 데이터
└── HVDC_Invoice.xlsx                         # Invoice 데이터 (선택적)
```

#### 3.2 파일 검증
```bash
# 파일 존재 확인
python -c "
import os
files = [
    'HVDC_excel_reporter_final_sqm_rev.xlsx',
    'HVDC_Stock On Hand Report (1).xlsx'
]
for f in files:
    print(f'✅ {f}: {os.path.exists(f)}')
"
```

## 🚀 실행 방법

### 1. 빠른 시작

#### 1.1 기본 실행 (테스트)
```bash
# 빠른 테스트 실행
python run_recon_pipeline.py

# 결과 확인
ls -la out_recon/
```

#### 1.2 전체 파이프라인 실행
```bash
# 전체 Tri-Source Reconciliation 실행
python run_recon_pipeline.py \
  --hitachi "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --siemens "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --stock "HVDC_Stock On Hand Report (1).xlsx" \
  --out-dir "out_recon"
```

### 2. 고급 실행 옵션

#### 2.1 환경별 실행
```bash
# 개발 환경
python run_recon_pipeline.py \
  --hitachi "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --siemens "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --stock "HVDC_Stock On Hand Report (1).xlsx" \
  --environment dev \
  --out-dir "out_dev"

# 운영 환경
python run_recon_pipeline.py \
  --hitachi "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --siemens "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --stock "HVDC_Stock On Hand Report (1).xlsx" \
  --environment prod \
  --out-dir "out_prod"
```

#### 2.2 Invoice 데이터 포함 실행
```bash
# Invoice 데이터 포함
python run_recon_pipeline.py \
  --hitachi "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --siemens "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --stock "HVDC_Stock On Hand Report (1).xlsx" \
  --invoice "HVDC_Invoice_Validation_Dashboard.xlsx" \
  --out-dir "out_full"
```

### 3. 개별 컴포넌트 실행

#### 3.1 예외 브리지 실행
```bash
# 예외→SKU 브리지 실행
python recon/exceptions_bridge.py

# 또는 파이프라인에서 자동 실행
python run_recon_pipeline.py --skip-exceptions=false
```

#### 3.2 향상된 파이프라인 실행
```bash
# 기존 Enhanced Pipeline 실행
python run_enhanced_pipeline.py

# 테스트 실행
python test_enhanced_features.py
```

## ⚙️ 설정 및 구성

### 1. 설정 파일 수정

#### 1.1 기본 설정 (config/recon_settings.py)
```python
# 톨러런스 설정 수정
INVOICE_MATCHING = {
    "tolerance": {
        "default": 0.10,    # 기본 ±10% → 필요시 조정
        "HE": 0.10,         # HITACHI 톨러런스
        "SIM": 0.15         # SIEMENS 톨러런스
    }
}

# 환경별 설정
ENVIRONMENT_CONFIGS = {
    "prod": {
        "debug": False,              # 운영시 False
        "save_intermediate": False,   # 중간 파일 저장 안함
        "notification_enabled": True  # 알림 활성화
    }
}
```

#### 1.2 사용자 정의 설정 파일
```bash
# 사용자 설정 파일 생성
cp config/recon_settings.py config/my_settings.py

# 사용자 설정으로 실행
python run_recon_pipeline.py \
  --config-file "config/my_settings.py" \
  [기타 옵션들...]
```

### 2. 데이터베이스 설정

#### 2.1 DuckDB 설정
```python
# config/recon_settings.py
DUCKDB_CONFIG = {
    "memory_limit": "2GB",      # 메모리 제한
    "threads": 4,               # 스레드 수
    "max_memory": "4GB",        # 최대 메모리
    "temp_directory": "out/temp" # 임시 디렉토리
}
```

#### 2.2 출력 설정
```python
OUTPUT_CONFIG = {
    "parquet_compression": "snappy",  # 압축 방식
    "include_metadata": True,         # 메타데이터 포함
    "save_intermediate": True,        # 중간 파일 저장
    "backup_previous": True,          # 이전 버전 백업
    "max_backup_files": 5             # 최대 백업 파일 수
}
```

## 📊 모니터링 및 로깅

### 1. 실행 로그 확인

#### 1.1 로그 파일 위치
```
📁 로그 파일:
├── out_recon/pipeline_execution_log.json    # 실행 로그
├── console output                           # 콘솔 출력
└── DuckDB 내부 로그                         # 데이터베이스 로그
```

#### 1.2 로그 분석
```bash
# 실행 로그 확인
cat out_recon/pipeline_execution_log.json | jq '.'

# 특정 정보 추출
cat out_recon/pipeline_execution_log.json | jq '.kpi.total_records'
cat out_recon/pipeline_execution_log.json | jq '.kpi.execution_time'
```

### 2. 성능 모니터링

#### 2.1 실행 시간 측정
```bash
# 시간 측정 실행
time python run_recon_pipeline.py \
  --hitachi "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --siemens "HVDC_excel_reporter_final_sqm_rev.xlsx" \
  --stock "HVDC_Stock On Hand Report (1).xlsx"
```

#### 2.2 메모리 사용량 확인
```python
# 메모리 사용량 모니터링
import psutil
import time

def monitor_memory():
    process = psutil.Process()
    while True:
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"Memory usage: {memory_mb:.1f} MB")
        time.sleep(5)

# 백그라운드에서 실행
monitor_memory()
```

## 🧪 테스트 및 검증

### 1. 단위 테스트 실행

#### 1.1 전체 테스트 스위트
```bash
# 모든 테스트 실행
python -m pytest test_enhanced_features.py -v

# 특정 테스트만 실행
python -m pytest test_enhanced_features.py::TestFlowTransitions -v
```

#### 1.2 개별 컴포넌트 테스트
```bash
# SKU 정규화 테스트
python -c "
from enhanced_sku_utils import normalize_sku
test_cases = ['sku-001', 'SKU 002', 'sku003']
for case in test_cases:
    print(f'{case} -> {normalize_sku(case)}')
"

# Flow 전이 검증 테스트
python -c "
from enhanced_sku_utils import validate_flow_transitions
import pandas as pd
# 테스트 데이터 생성 및 검증
"
```

### 2. 데이터 품질 검증

#### 2.1 데이터 무결성 확인
```bash
# DuckDB를 통한 데이터 확인
duckdb out_recon/sku_master_v2.duckdb

# SQL 쿼리 실행
SELECT COUNT(*) as total_records FROM sku_master;
SELECT flow_code, COUNT(*) FROM sku_master GROUP BY flow_code;
SELECT Final_Location, COUNT(*) FROM sku_master GROUP BY Final_Location;
```

#### 2.2 데이터 품질 리포트
```python
# 품질 검증 스크립트
python -c "
from hub.sku_master_v2 import get_hub_statistics
import pandas as pd

# 데이터 로드
df = pd.read_parquet('out_recon/SKU_MASTER_v2.parquet')

# 통계 생성
stats = get_hub_statistics(df)
print('Data Quality Report:')
for key, value in stats.items():
    print(f'  {key}: {value}')
"
```

## 🔧 문제 해결

### 1. 일반적인 문제

#### 1.1 모듈 Import 오류
```bash
# 문제: ModuleNotFoundError
# 해결: Python 경로 확인
python -c "import sys; print('\\n'.join(sys.path))"

# 해결: 현재 디렉토리에서 실행
cd /path/to/Stock
python run_recon_pipeline.py
```

#### 1.2 파일 경로 문제
```bash
# 문제: FileNotFoundError
# 해결: 파일 존재 확인
ls -la *.xlsx

# 해결: 절대 경로 사용
python run_recon_pipeline.py \
  --hitachi "/full/path/to/HVDC_excel_reporter_final_sqm_rev.xlsx" \
  [기타 옵션들...]
```

#### 1.3 메모리 부족
```bash
# 문제: MemoryError
# 해결: 배치 크기 줄이기
# config/recon_settings.py 수정
DUCKDB_CONFIG = {
    "memory_limit": "1GB",  # 2GB → 1GB로 줄이기
    "threads": 2            # 4 → 2로 줄이기
}
```

### 2. 성능 최적화

#### 2.1 처리 속도 개선
```python
# config/recon_settings.py
OUTPUT_CONFIG = {
    "parquet_compression": "zstd",  # snappy → zstd (더 빠름)
    "save_intermediate": False,     # 중간 파일 저장 안함
}

DUCKDB_CONFIG = {
    "threads": 8,              # CPU 코어 수에 맞춰 조정
    "memory_limit": "4GB",     # 시스템 메모리의 50% 정도
}
```

#### 2.2 메모리 사용량 최적화
```python
# 대용량 데이터 처리시
import gc

def process_large_dataset():
    # 데이터 처리
    result = process_data()
    
    # 메모리 정리
    gc.collect()
    
    return result
```

## 📈 운영 모드

### 1. 스케줄링 실행

#### 1.1 Windows Task Scheduler
```batch
@echo off
cd /d "C:\Stock"
python run_recon_pipeline.py ^
  --hitachi "HVDC_excel_reporter_final_sqm_rev.xlsx" ^
  --siemens "HVDC_excel_reporter_final_sqm_rev.xlsx" ^
  --stock "HVDC_Stock On Hand Report (1).xlsx" ^
  --environment prod ^
  --out-dir "out_prod"
```

#### 1.2 Linux Cron Job
```bash
# crontab -e
# 매일 오전 2시 실행
0 2 * * * cd /path/to/Stock && python run_recon_pipeline.py --hitachi "HVDC_excel_reporter_final_sqm_rev.xlsx" --siemens "HVDC_excel_reporter_final_sqm_rev.xlsx" --stock "HVDC_Stock On Hand Report (1).xlsx" --environment prod --out-dir "out_prod"
```

### 2. 백업 및 복구

#### 2.1 자동 백업 설정
```python
# config/recon_settings.py
OUTPUT_CONFIG = {
    "backup_previous": True,
    "max_backup_files": 7,  # 7일치 백업 유지
    "backup_location": "backups/"
}
```

#### 2.2 수동 백업
```bash
# 데이터 백업
cp -r out_recon/ backups/$(date +%Y%m%d)/

# 특정 날짜 복구
cp -r backups/20240920/ out_recon/
```

## 🚀 AWS 클라우드 배포 (선택적)

### 1. AWS SAM 배포

#### 1.1 SAM 설치
```bash
# AWS CLI 설치
aws --version

# SAM CLI 설치
pip install aws-sam-cli
sam --version
```

#### 1.2 배포 실행
```bash
# SAM 빌드
cd aws
sam build

# 배포 (가이드 모드)
sam deploy --guided

# 배포 (자동 모드)
sam deploy
```

### 2. Lambda 함수 배포

#### 2.1 컨테이너 이미지 빌드
```bash
# BERTopic Lambda
cd aws/lambda_bertopic
docker build -t bertopic-lambda .

# SKU Hub Lambda
cd aws/lambda_sku_hub
docker build -t sku-hub-lambda .
```

#### 2.2 ECR 푸시
```bash
# ECR 로그인
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin [account-id].dkr.ecr.us-east-1.amazonaws.com

# 이미지 푸시
docker tag bertopic-lambda:latest [account-id].dkr.ecr.us-east-1.amazonaws.com/bertopic-lambda:latest
docker push [account-id].dkr.ecr.us-east-1.amazonaws.com/bertopic-lambda:latest
```

## 📞 지원 및 문의

### 1. 로그 수집
```bash
# 문제 발생시 로그 수집
mkdir troubleshooting_logs
cp out_recon/pipeline_execution_log.json troubleshooting_logs/
cp out_recon/sku_master_v2.duckdb troubleshooting_logs/
python -c "import sys; print(sys.version)" > troubleshooting_logs/python_version.txt
```

### 2. 성능 리포트
```bash
# 성능 정보 수집
python -c "
import pandas as pd
import duckdb
import os

print('=== System Information ===')
print(f'Python version: {sys.version}')
print(f'Pandas version: {pd.__version__}')
print(f'DuckDB version: {duckdb.__version__}')

print('\\n=== File Sizes ===')
files = ['out_recon/SKU_MASTER_v2.parquet', 'out_recon/sku_master_v2.duckdb']
for f in files:
    if os.path.exists(f):
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f'{f}: {size_mb:.1f} MB')
"
```

---

## 📝 결론

이 배포 가이드를 따라하면 HVDC SKU Master Hub v2.0을 성공적으로 설치하고 운영할 수 있습니다. 

**주요 특징:**
- ✅ 간단한 설치 및 실행
- ✅ 유연한 설정 옵션
- ✅ 포괄적인 테스트 스위트
- ✅ 상세한 문제 해결 가이드
- ✅ AWS 클라우드 배포 지원

**지원되는 운영 모드:**
- 🖥️ 로컬 개발 환경
- 🏢 온프레미스 운영 환경
- ☁️ AWS 클라우드 환경

추가 질문이나 지원이 필요한 경우, 시스템 로그와 함께 문의해 주세요.
