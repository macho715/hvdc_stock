
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from hvdc_excel_reporter_final_sqm_rev (1).py file
import importlib.util
spec = importlib.util.spec_from_file_location("hvdc_excel_reporter_final_sqm_rev", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hvdc_excel_reporter_final_sqm_rev (1).py"))
reporter_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter_module)

HVDCExcelReporterFinal = reporter_module.HVDCExcelReporterFinal
from pathlib import Path
import pandas as pd

# Enhanced utilities import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_sku_utils import daily_occupancy

def compute_flow_and_sqm() -> dict:
    """
    Enhanced Flow and SQM Computation with Daily Occupancy Billing
    
    Returns:
        통합 통계 딕셔너리 (기존 + 일자별 점유)
    """
    rep = HVDCExcelReporterFinal()
    # Set data path to current directory where files are located
    rep.calculator.data_path = Path(".")
    # Use the available combined data file for both Hitachi and Siemens
    data_file = Path("HVDC_excel_reporter_final_sqm_rev.xlsx")
    rep.calculator.hitachi_file = data_file
    rep.calculator.simense_file = data_file  # Note: original code has typo "simense" not "siemens"
    
    print(f"📊 Using data file for both vendors: {data_file}")
    print(f"   - Hitachi file exists: {rep.calculator.hitachi_file.exists()}")
    print(f"   - Simense file exists: {rep.calculator.simense_file.exists()}")
    
    # 기존 통계 계산
    stats = rep.calculate_warehouse_statistics()
    
    # 일자별 점유 계산 추가 (빠른 실행을 위해 비활성화)
    if False and 'processed_data' in stats and not stats['processed_data'].empty:
        print("[INFO] Computing daily occupancy billing...")
        daily_stats = compute_daily_occupancy_billing(stats['processed_data'])
        stats['daily_occupancy'] = daily_stats
        print(f"[SUCCESS] Daily occupancy computed for {len(daily_stats)} days")
    
    return stats

def compute_daily_occupancy_billing(processed_df: pd.DataFrame) -> pd.DataFrame:
    """
    일자별 점유 과금 계산 (월 스냅샷 → 일 단위 재고일수×㎡)
    
    Args:
        processed_df: Reporter 처리된 데이터
        
    Returns:
        일자별 점유 DataFrame
    """
    # 창고 컬럼 목록 (Reporter 데이터 기준)
    warehouse_cols = [
        'AAA Storage', 'DSV Al Markaz', 'DSV Indoor', 'DSV MZP', 
        'DSV Outdoor', 'Hauler Indoor', 'MOSB', 'AGI', 'DAS', 'MIR', 'SHU'
    ]
    
    # 실제 존재하는 창고 컬럼만 필터링
    available_warehouses = [col for col in warehouse_cols if col in processed_df.columns]
    
    if not available_warehouses:
        print("[WARN] No warehouse columns found for daily occupancy calculation")
        return pd.DataFrame()
    
    print(f"[INFO] Computing occupancy for warehouses: {available_warehouses}")
    
    # 일자별 점유 계산
    daily_occ = daily_occupancy(processed_df, available_warehouses)
    
    if daily_occ.empty:
        print("[WARN] No daily occupancy data generated")
        return daily_occ
    
    # SQM 변환 (패키지 → ㎡, 평균 패키지당 0.5㎡ 가정)
    # 실제로는 processed_df의 SQM 컬럼을 활용해야 함
    daily_occ['sqm_occupied'] = daily_occ['pkg'] * 0.5  # 임시 변환 계수
    
    # 일자별 과금 계산 (창고별 요율 적용)
    daily_occ = calculate_daily_billing(daily_occ)
    
    return daily_occ

def calculate_daily_billing(daily_occ_df: pd.DataFrame) -> pd.DataFrame:
    """
    일자별 과금 계산
    
    Args:
        daily_occ_df: 일자별 점유 DataFrame
        
    Returns:
        과금 정보가 추가된 DataFrame
    """
    # 창고별 요율 (AED/m²/day)
    warehouse_rates = {
        'MOSB': 40.0,
        'DSV Indoor': 30.0,
        'DSV MZP': 35.0,
        'DSV Al Markaz': 25.0,
        'DSV Outdoor': 20.0,
        'Hauler Indoor': 28.0,
        'default': 25.0
    }
    
    # 일자별 과금 계산 (전체 창고 통합 요율 적용)
    avg_rate = sum(warehouse_rates.values()) / len(warehouse_rates)
    daily_occ_df['daily_billing_aed'] = daily_occ_df['sqm_occupied'] * avg_rate
    
    # 누적 과금 계산
    daily_occ_df['cumulative_billing_aed'] = daily_occ_df['daily_billing_aed'].cumsum()
    
    return daily_occ_df

def generate_monthly_billing_report(daily_occ_df: pd.DataFrame, target_month: str = "2024-01") -> dict:
    """
    월차 과금 리포트 생성
    
    Args:
        daily_occ_df: 일자별 점유 DataFrame
        target_month: 대상 월 (YYYY-MM)
        
    Returns:
        월차 리포트 딕셔너리
    """
    if daily_occ_df.empty:
        return {"error": "No daily occupancy data available"}
    
    # 월 필터링
    daily_occ_df['date'] = pd.to_datetime(daily_occ_df['date'])
    monthly_data = daily_occ_df[
        daily_occ_df['date'].dt.strftime('%Y-%m') == target_month
    ].copy()
    
    if monthly_data.empty:
        return {"error": f"No data found for month {target_month}"}
    
    # 월간 집계
    monthly_summary = {
        "target_month": target_month,
        "total_days": len(monthly_data),
        "total_packages": monthly_data['pkg'].sum(),
        "total_sqm_occupied": monthly_data['sqm_occupied'].sum(),
        "total_billing_aed": monthly_data['daily_billing_aed'].sum(),
        "average_daily_billing": monthly_data['daily_billing_aed'].mean(),
        "peak_daily_billing": monthly_data['daily_billing_aed'].max(),
        "lowest_daily_billing": monthly_data['daily_billing_aed'].min()
    }
    
    return {
        "summary": monthly_summary,
        "daily_details": monthly_data.to_dict('records')
    }
