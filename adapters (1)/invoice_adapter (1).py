
import importlib.util
import sys
import os
import json
from types import ModuleType
from pathlib import Path
import pandas as pd

# Enhanced utilities import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_sku_utils import get_tolerance, topn_alternatives

def run_invoice_validation_as_module(invoice_py_path: str) -> None:
    """
    Enhanced Invoice Validation with Tolerance Profiles and Auto-treatment
    
    Args:
        invoice_py_path: Invoice 스크립트 경로
    """
    p = Path(invoice_py_path)
    if not p.exists():
        raise FileNotFoundError(f"Invoice script not found: {p}")
    
    spec = importlib.util.spec_from_file_location("invoice_mod", p)
    mod = importlib.util.module_from_spec(spec)  # type: ModuleType
    spec.loader.exec_module(mod)
    
    # 원본 검증 완료 후 Enhanced 처리가 필요한 경우
    print("[INFO] Invoice validation completed, applying enhanced processing...")

def apply_tolerance_profile_to_matching(units_df, vendor_code, warehouse_hint):
    """
    톨러런스 프로파일을 적용한 매칭
    
    Args:
        units_df: 유닛 데이터프레임
        vendor_code: 벤더 코드
        warehouse_hint: 창고 힌트
        
    Returns:
        톨러런스 적용 결과
    """
    # 벤더 코드 정규화 (HITACHI -> HE, SIEMENS -> SIM)
    vendor_map = {'HITACHI': 'HE', 'SIEMENS': 'SIM'}
    vendor_code3 = vendor_map.get(vendor_code, vendor_code[:3].upper())
    
    # 톨러런스 가져오기
    tol = get_tolerance(vendor_code3, warehouse_hint)
    
    print(f"[INFO] Applying tolerance profile for {vendor_code3}/{warehouse_hint}: GW±{tol['gw']}, CBM±{tol['cbm']}")
    
    return tol

def suggest_alternatives_for_failures(exceptions_df, units_df):
    """
    FAIL 케이스에 대한 대안 조합 제안
    
    Args:
        exceptions_df: 예외 케이스 DataFrame
        units_df: 유닛 데이터프레임
        
    Returns:
        대안 제안이 추가된 DataFrame
    """
    if exceptions_df.empty:
        return exceptions_df
    
    print(f"[INFO] Analyzing {len(exceptions_df)} exception cases for alternative suggestions...")
    
    suggestions = []
    for _, row in exceptions_df.iterrows():
        if pd.isna(row.get('G.W(kgs)')) or pd.isna(row.get('CBM')):
            suggestions.append({"SKU": row.get('SKU'), "alternatives": []})
            continue
            
        gw_tgt = float(row['G.W(kgs)'])
        cbm_tgt = float(row['CBM'])
        k = int(row.get('Pkg', 1))
        
        # Top-3 대안 조합 제안
        alternatives = topn_alternatives(units_df, k, gw_tgt, cbm_tgt, n=3)
        suggestions.append({
            "SKU": row.get('SKU'),
            "alternatives": alternatives
        })
    
    # 대안 제안을 JSON 문자열로 변환하여 추가
    exceptions_with_alternatives = exceptions_df.copy()
    exceptions_with_alternatives['alternative_suggestions'] = [
        json.dumps(sugg['alternatives']) for sugg in suggestions
    ]
    
    print(f"[SUCCESS] Generated alternative suggestions for {len(suggestions)} cases")
    return exceptions_with_alternatives

def enhanced_invoice_processing(invoice_py_path: str, apply_enhancements: bool = True):
    """
    Enhanced Invoice Processing with 모든 개선사항 적용
    
    Args:
        invoice_py_path: Invoice 스크립트 경로
        apply_enhancements: 개선사항 적용 여부
        
    Returns:
        처리 결과 딕셔너리
    """
    # 1. 원본 Invoice 검증 실행
    run_invoice_validation_as_module(invoice_py_path)
    
    result = {"status": "completed", "enhancements_applied": apply_enhancements}
    
    if apply_enhancements:
        # 2. 톨러런스 프로파일 적용 (예시)
        result["tolerance_profiles"] = {
            "HE_DSV_Indoor": get_tolerance("HE", "DSV Indoor"),
            "HE_MOSB": get_tolerance("HE", "MOSB"),
            "SIM_DSV_Indoor": get_tolerance("SIM", "DSV Indoor"),
            "default": get_tolerance("*", "*")
        }
        
        # 3. 예외 처리 개선 로직 (실제 구현시 예외 파일 로드 필요)
        result["exception_processing"] = "Enhanced with alternative suggestions"
        
        print("[SUCCESS] Enhanced invoice processing completed")
    
    return result
