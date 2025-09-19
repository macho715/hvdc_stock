# adapters/stock_adapter_v2.py
"""
HVDC Stock Adapter v2 - 최신일자/타임라인 채워 돌려주기
기존 구현을 유지하면서 latest_date, timeline 정보를 보강
"""
import sys
import os
from typing import Dict, Any
from pathlib import Path
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 기존 STOCK.py 기반 분석 (있는 환경)
import importlib.util
spec = importlib.util.spec_from_file_location("stock", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stock (1).py"))
stock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock)

analyze_hvdc_inventory = stock.analyze_hvdc_inventory
InventoryTracker = stock.InventoryTracker

# REPORT_DATE 단일시트 통합 분석기 (없는 환경이면 생략)
try:
    # 환경에 맞는 통합 추적기 모듈이 있다면 로드
    # from HVDC_통합_추적기 import HVDCUnifiedStockTracker
    HVDCUnifiedStockTracker = None  # 현재는 None으로 설정
except Exception:
    HVDCUnifiedStockTracker = None

def build_stock_snapshots_v2(stock_excel_path: str) -> Dict[str, Any]:
    """
    Stock 스냅샷 v2 - 최신일자/타임라인 정보 보강
    
    Args:
        stock_excel_path: Stock Excel 파일 경로
    
    Returns:
        dict: {
            "latest_date": 최신 스냅샷 날짜,
            "timeline": 타임라인 정보,
            "summary_df": 요약 DataFrame
        }
    """
    print(f"[INFO] Stock Adapter v2 - Loading: {stock_excel_path}")
    
    # 1) 기존 파이프라인 유지 (analyze_hvdc_inventory + InventoryTracker)
    print("[INFO] Running HVDC inventory analysis...")
    analyze_hvdc_inventory(stock_excel_path, show_details=False)
    
    print("[INFO] Running inventory tracking analysis...")
    tr = InventoryTracker(stock_excel_path)
    tr.run_analysis()
    summary_df = tr.create_summary()
    
    print(f"[INFO] Stock summary created: {len(summary_df)} records")
    
    # 2) REPORT_DATE 기반 스냅샷 추가 (가능 시)
    latest_date, timeline = None, {}
    
    try:
        if HVDCUnifiedStockTracker:
            print("[INFO] Running unified stock tracker...")
            ut = HVDCUnifiedStockTracker(stock_excel_path)
            if ut.load_unified_data():
                ta = ut.analyze_inventory_timeline()
                latest_date = ta.get('latest_date')
                timeline = ta.get('timeline', {})
                print(f"[INFO] Unified tracker completed - latest: {latest_date}")
    except Exception as e:
        print(f"[WARN] Unified tracker not available: {e}")
    
    # 3) 기본 최신일자 추출 (summary_df에서)
    if latest_date is None and not summary_df.empty:
        # First_Seen, Last_Seen 컬럼에서 최신 날짜 추출
        date_columns = ['First_Seen', 'Last_Seen']
        latest_dates = []
        
        for col in date_columns:
            if col in summary_df.columns:
                try:
                    dates = pd.to_datetime(summary_df[col], errors='coerce')
                    valid_dates = dates.dropna()
                    if not valid_dates.empty:
                        latest_dates.append(valid_dates.max())
                except Exception:
                    continue
        
        if latest_dates:
            latest_date = max(latest_dates).strftime('%Y-%m-%d')
            print(f"[INFO] Extracted latest date from summary: {latest_date}")
    
    # 4) 기본 타임라인 생성 (월별 추이)
    if not timeline and not summary_df.empty:
        timeline = _create_basic_timeline(summary_df)
    
    result = {
        "latest_date": latest_date,
        "timeline": timeline,
        "summary_df": summary_df,
        "total_records": len(summary_df),
        "date_range": {
            "first_seen": summary_df['First_Seen'].min() if 'First_Seen' in summary_df.columns else None,
            "last_seen": summary_df['Last_Seen'].max() if 'Last_Seen' in summary_df.columns else None
        }
    }
    
    print(f"[SUCCESS] Stock v2 완료 - {result['total_records']} 건, latest: {latest_date}")
    return result

def _create_basic_timeline(summary_df: pd.DataFrame) -> dict:
    """
    기본 타임라인 생성 (월별 추이)
    """
    timeline = {}
    
    try:
        if 'First_Seen' in summary_df.columns:
            # 월별 입고 추이
            first_seen = pd.to_datetime(summary_df['First_Seen'], errors='coerce')
            monthly_in = first_seen.dt.to_period('M').value_counts().sort_index()
            timeline['monthly_inbound'] = {
                str(period): int(count) for period, count in monthly_in.items()
            }
        
        if 'Last_Seen' in summary_df.columns:
            # 월별 최종 관측 추이
            last_seen = pd.to_datetime(summary_df['Last_Seen'], errors='coerce')
            monthly_last = last_seen.dt.to_period('M').value_counts().sort_index()
            timeline['monthly_last_seen'] = {
                str(period): int(count) for period, count in monthly_last.items()
            }
        
        # 창고별 분포
        if 'Warehouse' in summary_df.columns:
            warehouse_dist = summary_df['Warehouse'].value_counts().to_dict()
            timeline['warehouse_distribution'] = warehouse_dist
            
        # 상태별 분포
        if 'Status' in summary_df.columns:
            status_dist = summary_df['Status'].value_counts().to_dict()
            timeline['status_distribution'] = status_dist
            
    except Exception as e:
        print(f"[WARN] Timeline creation failed: {e}")
    
    return timeline

def validate_stock_data(stock_excel_path: str) -> dict:
    """
    Stock 데이터 검증
    
    Returns:
        dict: 검증 결과
    """
    try:
        xl = pd.ExcelFile(stock_excel_path)
        sheets = xl.sheet_names
        
        # 주요 시트 확인
        required_sheets = ['종합_SKU요약', '날짜별_추이', '월별_분석']
        found_sheets = [s for s in required_sheets if s in sheets]
        
        # 시트별 레코드 수
        sheet_stats = {}
        for sheet in found_sheets:
            try:
                df = xl.parse(sheet)
                sheet_stats[sheet] = {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "columns_list": list(df.columns)
                }
            except Exception as e:
                sheet_stats[sheet] = {"error": str(e)}
        
        return {
            "file_exists": Path(stock_excel_path).exists(),
            "total_sheets": len(sheets),
            "found_required_sheets": found_sheets,
            "sheet_stats": sheet_stats,
            "validation_passed": len(found_sheets) >= 2
        }
        
    except Exception as e:
        return {
            "file_exists": Path(stock_excel_path).exists(),
            "error": str(e),
            "validation_passed": False
        }

if __name__ == "__main__":
    # 테스트 실행
    stock_file = "HVDC_Stock On Hand Report (1).xlsx"
    
    validation = validate_stock_data(stock_file)
    print("Stock 검증 결과:", validation)
    
    if validation.get("validation_passed"):
        result = build_stock_snapshots_v2(stock_file)
        print("Stock v2 결과:")
        print(f"  - 최신일자: {result['latest_date']}")
        print(f"  - 타임라인 키: {list(result['timeline'].keys())}")
        print(f"  - 총 레코드: {result['total_records']}")
