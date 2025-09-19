# adapters/reporter_adapter_v2.py
"""
HVDC Reporter Adapter v2 - 벤더 파일을 명시 경로로 받기
기존 구현과 100% 호환되며, 운영 환경에서 각 벤더 파일 경로를 명시적으로 지정
"""
import sys
import os
from pathlib import Path
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 기존 HVDC Excel Reporter 모듈 동적 로드
import importlib.util
spec = importlib.util.spec_from_file_location("hvdc_excel_reporter_final_sqm_rev",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hvdc_excel_reporter_final_sqm_rev (1).py"))
reporter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter_module)
HVDCExcelReporterFinal = reporter_module.HVDCExcelReporterFinal

def compute_flow_and_sqm_v2(hitachi_path: str, siemens_path: str) -> dict:
    """
    벤더별 파일 경로를 명시적으로 받는 Reporter 어댑터 v2
    
    Args:
        hitachi_path: HITACHI 파일 경로
        siemens_path: SIEMENS 파일 경로 (기존 "simense" 오타 호환 유지)
    
    Returns:
        dict: Reporter 통계 결과 (기존 구조와 동일)
    """
    print(f"[INFO] Reporter v2 - HITACHI: {hitachi_path}")
    print(f"[INFO] Reporter v2 - SIEMENS: {siemens_path}")
    
    # 기존 HVDCExcelReporterFinal 클래스 사용
    rep = HVDCExcelReporterFinal()
    
    # 파일 경로 설정 (기존 calculator 구조 활용)
    rep.calculator.data_path = Path(hitachi_path).parent
    
    # 원 코드의 필드명/오탈자 호환 유지: hitachi_file / simense_file
    rep.calculator.hitachi_file = Path(hitachi_path)
    rep.calculator.simense_file = Path(siemens_path)  # "simense" 그대로 호환
    
    print(f"[INFO] HITACHI 파일 존재: {rep.calculator.hitachi_file.exists()}")
    print(f"[INFO] SIEMENS 파일 존재: {rep.calculator.simense_file.exists()}")
    
    # 기존 calculate_warehouse_statistics() 메서드 호출
    stats = rep.calculate_warehouse_statistics()
    
    print(f"[SUCCESS] Reporter v2 완료 - {stats.get('total_records', 0)} 건 처리")
    return stats

def validate_file_paths(hitachi_path: str, siemens_path: str) -> dict:
    """
    파일 경로 검증 및 통계
    
    Returns:
        dict: 파일 검증 결과
    """
    hitachi_exists = Path(hitachi_path).exists()
    siemens_exists = Path(siemens_path).exists()
    
    return {
        "hitachi_file": {
            "path": hitachi_path,
            "exists": hitachi_exists,
            "size_mb": Path(hitachi_path).stat().st_size / (1024*1024) if hitachi_exists else 0
        },
        "siemens_file": {
            "path": siemens_path, 
            "exists": siemens_exists,
            "size_mb": Path(siemens_path).stat().st_size / (1024*1024) if siemens_exists else 0
        },
        "both_exist": hitachi_exists and siemens_exists
    }

if __name__ == "__main__":
    # 테스트 실행
    hitachi_file = "HVDC_excel_reporter_final_sqm_rev.xlsx"
    siemens_file = "HVDC_excel_reporter_final_sqm_rev.xlsx"  # 동일 파일 사용
    
    validation = validate_file_paths(hitachi_file, siemens_file)
    print("파일 검증 결과:", validation)
    
    if validation["both_exist"]:
        stats = compute_flow_and_sqm_v2(hitachi_file, siemens_file)
        print("통계 결과:", stats.keys())
