# run_recon_pipeline.py
"""
Tri-Source Reconciliation Pipeline - 운영 배선 (엔트리 포인트)
HVDC SKU Master Hub Enhanced System의 통합 실행 스크립트
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
import json

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from recon.reconciliation_engine import run_reconciliation, validate_reconciliation_inputs
from recon.exceptions_bridge import run_exceptions_bridge_pipeline
from config.recon_settings import get_config, validate_config

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="HVDC Tri-Source Reconciliation Pipeline")
    
    # 필수 인자
    parser.add_argument("--hitachi", required=True, help="HITACHI 파일 경로")
    parser.add_argument("--siemens", required=True, help="SIEMENS 파일 경로") 
    parser.add_argument("--stock", required=True, help="Stock 파일 경로")
    
    # 선택 인자
    parser.add_argument("--invoice", help="Invoice 대시보드 Excel 파일 경로")
    parser.add_argument("--out-dir", default="out", help="출력 디렉토리 (기본: out)")
    parser.add_argument("--environment", default="dev", choices=["dev", "staging", "prod"], help="환경 설정")
    parser.add_argument("--skip-exceptions", action="store_true", help="예외 브리지 스킵")
    parser.add_argument("--config-file", help="설정 파일 경로 (JSON)")
    parser.add_argument("--validate-only", action="store_true", help="입력 검증만 수행")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🚀 HVDC Tri-Source Reconciliation Pipeline")
    print("=" * 70)
    print(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌍 환경: {args.environment}")
    print(f"📁 출력 디렉토리: {args.out_dir}")
    
    # 1) 설정 로드
    print(f"\n⚙️ Step 1: 설정 로드")
    print("-" * 40)
    
    if args.config_file and Path(args.config_file).exists():
        with open(args.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ 사용자 설정 로드: {args.config_file}")
    else:
        config = get_config(args.environment)
        print(f"✅ 기본 설정 로드: {args.environment}")
    
    # 설정 검증
    validation = validate_config(config)
    if not validation["valid"]:
        print(f"❌ 설정 검증 실패: {validation['errors']}")
        return 1
    
    if validation["warnings"]:
        print(f"⚠️ 설정 경고: {validation['warnings']}")
    
    # 2) 입력 파일 검증
    print(f"\n🔍 Step 2: 입력 파일 검증")
    print("-" * 40)
    
    input_validation = validate_reconciliation_inputs(
        args.hitachi, args.siemens, args.stock, args.invoice
    )
    
    print(f"📊 검증 결과:")
    for file_type, info in input_validation.items():
        if isinstance(info, dict) and "exists" in info:
            status = "✅" if info["exists"] else "❌"
            print(f"  {status} {file_type}: {info['path']}")
    
    if not input_validation["validation_passed"]:
        print("❌ 입력 파일 검증 실패")
        return 1
    
    if args.validate_only:
        print("✅ 입력 검증 완료 (검증만 수행)")
        return 0
    
    # 3) 출력 디렉토리 생성
    print(f"\n📁 Step 3: 출력 디렉토리 준비")
    print("-" * 40)
    
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    print(f"✅ 출력 디렉토리 생성: {args.out_dir}")
    
    # 4) Tri-Source Reconciliation 실행
    print(f"\n🔄 Step 4: Tri-Source Reconciliation 실행")
    print("-" * 40)
    
    try:
        pq, kpi = run_reconciliation(
            hitachi_file=args.hitachi,
            siemens_file=args.siemens,
            stock_file=args.stock,
            invoice_dashboard_xlsx=args.invoice,
            out_dir=args.out_dir
        )
        
        print(f"✅ Reconciliation 완료: {pq}")
        
    except Exception as e:
        print(f"❌ Reconciliation 실패: {e}")
        return 1
    
    # 5) 예외 브리지 실행 (선택적)
    if not args.skip_exceptions and args.invoice:
        print(f"\n🔗 Step 5: 예외→SKU 브리지 실행")
        print("-" * 40)
        
        try:
            exceptions_result = run_exceptions_bridge_pipeline(
                invoice_dashboard_xlsx=args.invoice,
                sku_master_parquet=pq,
                out_dir=args.out_dir
            )
            
            if exceptions_result["success"]:
                print(f"✅ 예외 브리지 완료")
            else:
                print(f"⚠️ 예외 브리지 실패: {exceptions_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"⚠️ 예외 브리지 실행 중 오류: {e}")
    
    # 6) 최종 결과 요약
    print(f"\n📊 Step 6: 최종 결과 요약")
    print("-" * 40)
    
    # KPI 요약
    print(f"📈 처리 통계:")
    print(f"  - 총 레코드: {kpi['total_records']:,}")
    print(f"  - 고유 SKU: {kpi['unique_skus']:,}")
    print(f"  - 실행 시간: {kpi['execution_time']:.2f}초")
    print(f"  - Flow 커버리지: {kpi['flow_coverage']}개 코드")
    print(f"  - 위치 커버리지: {kpi['location_coverage']}개 위치")
    
    if kpi.get("invoice_pass_rate") is not None:
        print(f"  - Invoice 통과율: {kpi['invoice_pass_rate']:.1%}")
    
    # 데이터 소스별 통계
    if "data_sources" in kpi:
        print(f"📊 데이터 소스별 통계:")
        for source, count in kpi["data_sources"].items():
            print(f"  - {source}: {count:,} 건")
    
    # 출력 파일 목록
    output_files = [
        ("SKU Master Parquet", pq),
        ("SKU Master DuckDB", pq.replace(".parquet", ".duckdb")),
    ]
    
    if not args.skip_exceptions and args.invoice:
        output_files.extend([
            ("Exceptions by SKU Parquet", f"{args.out_dir}/exceptions_by_sku.parquet"),
            ("Exceptions Report", f"{args.out_dir}/exceptions_report.xlsx")
        ])
    
    print(f"📁 생성된 파일:")
    for file_type, file_path in output_files:
        if Path(file_path).exists():
            size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            print(f"  ✅ {file_type}: {file_path} ({size_mb:.1f}MB)")
        else:
            print(f"  ❌ {file_type}: {file_path} (없음)")
    
    # 실행 로그 저장 (JSON 직렬화 가능하도록 변환)
    def convert_for_json(obj):
        """JSON 직렬화를 위해 numpy 타입 변환"""
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: convert_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_for_json(item) for item in obj]
        else:
            return obj
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "environment": args.environment,
        "input_files": {
            "hitachi": args.hitachi,
            "siemens": args.siemens,
            "stock": args.stock,
            "invoice": args.invoice
        },
        "output_directory": args.out_dir,
        "kpi": convert_for_json(kpi),
        "config": convert_for_json(config)
    }
    
    log_file = f"{args.out_dir}/pipeline_execution_log.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    print(f"📝 실행 로그: {log_file}")
    
    print("\n" + "=" * 70)
    print("🎉 HVDC Tri-Source Reconciliation Pipeline 완료!")
    print("=" * 70)
    
    return 0

def run_quick_test():
    """빠른 테스트 실행 (개발용)"""
    print("🧪 빠른 테스트 모드")
    
    # 기본 파일 경로 (현재 디렉토리 기준)
    test_files = {
        "hitachi": "HVDC_excel_reporter_final_sqm_rev.xlsx",
        "siemens": "HVDC_excel_reporter_final_sqm_rev.xlsx",
        "stock": "HVDC_Stock On Hand Report (1).xlsx",
        "invoice": None  # 선택적
    }
    
    # 파일 존재 확인
    for file_type, file_path in test_files.items():
        if file_path and Path(file_path).exists():
            print(f"✅ {file_type}: {file_path}")
        elif file_path:
            print(f"❌ {file_type}: {file_path} (없음)")
        else:
            print(f"⚠️ {file_type}: 선택적 (None)")
    
    # 입력 검증만 실행
    validation = validate_reconciliation_inputs(
        test_files["hitachi"], 
        test_files["siemens"], 
        test_files["stock"], 
        test_files["invoice"]
    )
    
    print(f"\n검증 결과: {'✅ 통과' if validation['validation_passed'] else '❌ 실패'}")
    return validation["validation_passed"]

if __name__ == "__main__":
    # 명령행 인자가 없으면 빠른 테스트 실행
    if len(sys.argv) == 1:
        success = run_quick_test()
        sys.exit(0 if success else 1)
    
    # 정상 실행
    exit_code = main()
    sys.exit(exit_code)
