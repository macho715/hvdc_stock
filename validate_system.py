#!/usr/bin/env python3
"""
HVDC SKU Master Hub v2.0 - 시스템 검증 스크립트
"""
import os
import json
from pathlib import Path

def main():
    print("=== HVDC SKU Master Hub v2.0 - 최종 검증 ===")
    print()

    # 핵심 파일 존재 확인
    core_files = [
        'enhanced_sku_utils.py',
        'run_recon_pipeline.py',
        'recon/reconciliation_engine.py',
        'hub (1)/sku_master_v2.py',
        'adapters (1)/reporter_adapter_v2.py',
        'adapters (1)/stock_adapter_v2.py',
        'config/recon_settings.py',
        'SYSTEM_ARCHITECTURE.md',
        'DEPLOYMENT_GUIDE.md'
    ]

    print("📁 핵심 파일 검증:")
    all_files_exist = True
    for file in core_files:
        exists = os.path.exists(file)
        status = '✅' if exists else '❌'
        print(f"  {status} {file}")
        if not exists:
            all_files_exist = False

    print()

    # 출력 디렉토리 확인
    output_dirs = ['out_recon', 'out']
    print("📊 출력 디렉토리:")
    for dir_name in output_dirs:
        if os.path.exists(dir_name):
            files = os.listdir(dir_name)
            total_size = 0
            for f in files:
                file_path = os.path.join(dir_name, f)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
            print(f"  ✅ {dir_name}/ ({len(files)} files, {total_size/1024/1024:.1f} MB)")
        else:
            print(f"  ❌ {dir_name}/ (없음)")

    print()

    # 실행 로그 확인
    log_file = 'out_recon/pipeline_execution_log.json'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            print("📈 최근 실행 결과:")
            kpi = log_data.get('kpi', {})
            print(f"  - 총 레코드: {kpi.get('total_records', 0):,}")
            print(f"  - 실행 시간: {kpi.get('execution_time', 0):.2f}초")
            print(f"  - Flow 커버리지: {kpi.get('flow_coverage', 0)}개")
            print(f"  - 위치 커버리지: {kpi.get('location_coverage', 0)}개")
            print(f"  - SQM 커버리지: {kpi.get('sqm_coverage', 0):.1%}")
        except Exception as e:
            print(f"  ⚠️ 로그 파일 읽기 실패: {e}")
    else:
        print("  ❌ 실행 로그 없음")

    print()

    # 모듈 Import 테스트
    print("🐍 모듈 Import 테스트:")
    try:
        from enhanced_sku_utils import normalize_sku
        print("  ✅ enhanced_sku_utils")
    except Exception as e:
        print(f"  ❌ enhanced_sku_utils: {e}")

    try:
        from config.recon_settings import get_config
        print("  ✅ config.recon_settings")
    except Exception as e:
        print(f"  ❌ config.recon_settings: {e}")

    try:
        from recon.reconciliation_engine import validate_reconciliation_inputs
        print("  ✅ recon.reconciliation_engine")
    except Exception as e:
        print(f"  ❌ recon.reconciliation_engine: {e}")

    print()

    # 최종 결과
    if all_files_exist:
        print("🎉 시스템 검증 완료! 모든 핵심 파일이 존재합니다.")
        print()
        print("🚀 사용 가능한 명령어:")
        print("  python run_recon_pipeline.py                    # 빠른 테스트")
        print("  python run_recon_pipeline.py --help             # 도움말")
        print("  python test_enhanced_features.py                # 테스트 실행")
        print("  duckdb out_recon/sku_master_v2.duckdb           # DB 접근")
        print()
        print("📚 문서:")
        print("  - SYSTEM_ARCHITECTURE.md                        # 시스템 아키텍처")
        print("  - DEPLOYMENT_GUIDE.md                           # 배포 가이드")
        print("  - ENHANCED_FEATURES_SUMMARY.md                  # 기능 요약")
    else:
        print("⚠️ 일부 파일이 누락되었습니다. 설치를 다시 확인해주세요.")

if __name__ == "__main__":
    main()
