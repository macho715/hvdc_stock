# recon/reconciliation_engine.py
"""
Tri-Source Reconciliation Engine - 삼중 대조 & DuckDB 적재
Invoice ↔ HVDC Excel(Flow/SQM) ↔ Stock On-Hand(스냅샷) 삼자 대조 테이블 생성
"""
import sys
import os
from pathlib import Path
import pandas as pd
import duckdb
from datetime import datetime
from typing import Dict, Any, Optional

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 기존 어댑터들 import (동적 로드)
import importlib.util

def load_adapter_module(module_name, file_path):
    """동적 모듈 로드"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 어댑터 모듈 로드
adapters_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'adapters (1)')
hub_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'hub (1)')

try:
    # v2 어댑터들 시도
    reporter_adapter_v2 = load_adapter_module('reporter_adapter_v2', 
        os.path.join(adapters_dir, 'reporter_adapter_v2.py'))
    stock_adapter_v2 = load_adapter_module('stock_adapter_v2', 
        os.path.join(adapters_dir, 'stock_adapter_v2.py'))
    sku_master_v2 = load_adapter_module('sku_master_v2', 
        os.path.join(hub_dir, 'sku_master_v2.py'))
    
    compute_flow_and_sqm_v2 = reporter_adapter_v2.compute_flow_and_sqm_v2
    build_stock_snapshots_v2 = stock_adapter_v2.build_stock_snapshots_v2
    build_sku_master_v2 = sku_master_v2.build_sku_master_v2
    save_hub_v2 = sku_master_v2.save_hub_v2
    get_hub_statistics = sku_master_v2.get_hub_statistics
    
    print("[INFO] v2 adapters loaded successfully")
except Exception as e:
    print(f"[WARN] v2 adapters failed, using original: {e}")
    # fallback to original adapters
    reporter_adapter = load_adapter_module('reporter_adapter', 
        os.path.join(adapters_dir, 'reporter_adapter (1).py'))
    stock_adapter = load_adapter_module('stock_adapter', 
        os.path.join(adapters_dir, 'stock_adapter (1).py'))
    sku_master = load_adapter_module('sku_master', 
        os.path.join(hub_dir, 'sku_master (1).py'))
    
    compute_flow_and_sqm = reporter_adapter.compute_flow_and_sqm
    build_stock_snapshots = stock_adapter.build_stock_snapshots
    build_sku_master = sku_master.build_sku_master
    save_as_parquet_duckdb = sku_master.save_as_parquet_duckdb
    
    # v2 함수들을 원본으로 설정 (fallback)
    compute_flow_and_sqm_v2 = compute_flow_and_sqm
    build_stock_snapshots_v2 = build_stock_snapshots
    build_sku_master_v2 = build_sku_master
    save_hub_v2 = save_as_parquet_duckdb
    get_hub_statistics = lambda df: {"total_records": len(df)}

def _read_invoice_dashboard(excel_path: str) -> pd.DataFrame:
    """
    인보이스 검증 엑셀(HVDC_Invoice_Validation_Dashboard.xlsx)에서
    Exceptions_Only + Invoice_Original_Order를 읽어 SKU 매핑 테이블 생성
    
    Args:
        excel_path: Invoice 대시보드 Excel 파일 경로
    
    Returns:
        pd.DataFrame: Invoice 매칭 결과
    """
    print(f"[INFO] Reading invoice dashboard: {excel_path}")
    
    try:
        xl = pd.ExcelFile(excel_path)
        print(f"[INFO] Available sheets: {xl.sheet_names}")
        
        # Exceptions_Only 시트 읽기
        ex = pd.DataFrame()
        if "Exceptions_Only" in xl.sheet_names:
            ex = xl.parse("Exceptions_Only")
            print(f"[INFO] Exceptions_Only: {ex.shape}")
        
        # Invoice_Original_Order 시트 읽기 (주요 데이터)
        io = pd.DataFrame()
        if "Invoice_Original_Order" in xl.sheet_names:
            io = xl.parse("Invoice_Original_Order")
            print(f"[INFO] Invoice_Original_Order: {io.shape}")
        elif "Invoice_Original" in xl.sheet_names:
            io = xl.parse("Invoice_Original")
            print(f"[INFO] Invoice_Original: {io.shape}")
        
        # SKU 컬럼 찾기
        sku_col = None
        for c in ["Case No.", "SKU", "CaseNo", "Case_no", "HVDC CODE"]:
            if c in io.columns:
                sku_col = c
                break
        
        if sku_col is None:
            print("[WARN] No SKU column found in invoice data")
            io["SKU"] = None
        else:
            io = io.rename(columns={sku_col: "SKU"})
            print(f"[INFO] Using SKU column: {sku_col}")
        
        # 필요한 컬럼 정리
        pick = ["SKU", "Match_Status", "GW_SumPicked", "CBM_SumPicked", "Err_GW", "Err_CBM"]
        for c in pick:
            if c not in io.columns:
                io[c] = None
        
        inv = io[pick].copy().drop_duplicates(subset=["SKU"])
        print(f"[INFO] Invoice data processed: {inv.shape}")
        
        return inv
        
    except Exception as e:
        print(f"[ERROR] Failed to read invoice dashboard: {e}")
        # 빈 DataFrame 반환
        return pd.DataFrame(columns=["SKU", "Match_Status", "GW_SumPicked", "CBM_SumPicked", "Err_GW", "Err_CBM"])

def run_reconciliation(
    hitachi_file: str,
    siemens_file: str,
    stock_file: str,
    invoice_dashboard_xlsx: Optional[str] = None,
    out_dir: str = "out"
) -> tuple:
    """
    Tri-Source Reconciliation 실행
    
    Args:
        hitachi_file: HITACHI 파일 경로
        siemens_file: SIEMENS 파일 경로
        stock_file: Stock 파일 경로
        invoice_dashboard_xlsx: Invoice 대시보드 Excel 파일 (선택적)
        out_dir: 출력 디렉토리
    
    Returns:
        tuple: (parquet_path, kpi_dict)
    """
    print("=" * 60)
    print("🚀 HVDC Tri-Source Reconciliation Engine Starting...")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # 1) Reporter 통계 (Flow/SQM 등)
    print("\n📊 Step 1: Reporter 통계 계산")
    print("-" * 40)
    try:
        rep_stats = compute_flow_and_sqm_v2(hitachi_file, siemens_file)
        print(f"✅ Reporter 완료: {rep_stats.get('total_records', 0)} 건")
    except Exception as e:
        print(f"⚠️ Reporter v2 실패, 원본 사용: {e}")
        rep_stats = compute_flow_and_sqm(hitachi_file, siemens_file)
        print(f"✅ Reporter 완료: {rep_stats.get('total_records', 0)} 건")

    # 2) Stock 스냅샷 (최신일·타임라인·요약)
    print("\n📦 Step 2: Stock 스냅샷 생성")
    print("-" * 40)
    try:
        stock = build_stock_snapshots_v2(stock_file)
        print(f"✅ Stock v2 완료: {stock['total_records']} 건, latest: {stock['latest_date']}")
    except Exception as e:
        print(f"⚠️ Stock v2 실패, 원본 사용: {e}")
        stock_result = build_stock_snapshots(stock_file)
        stock = {
            "summary_df": stock_result["summary_df"],
            "latest_date": None,
            "timeline": {},
            "total_records": len(stock_result["summary_df"])
        }
        print(f"✅ Stock 완료: {stock['total_records']} 건")

    # 3) Invoice 검증 결과 (선택적)
    print("\n💰 Step 3: Invoice 검증 결과 처리")
    print("-" * 40)
    inv_df = None
    if invoice_dashboard_xlsx and Path(invoice_dashboard_xlsx).exists():
        inv_df = _read_invoice_dashboard(invoice_dashboard_xlsx)
        print(f"✅ Invoice 완료: {len(inv_df)} 건")
    else:
        print("⚠️ Invoice 파일 없음, SKU만으로 진행")

    # 4) 허브 구축
    print("\n🏢 Step 4: SKU Master Hub 구축")
    print("-" * 40)
    try:
        hub = build_sku_master_v2(
            stock_summary_df=stock["summary_df"],
            reporter_stats=rep_stats,
            invoice_match_df=inv_df
        )
        print(f"✅ Hub v2 완료: {hub.shape}")
    except Exception as e:
        print(f"⚠️ Hub v2 실패, 원본 사용: {e}")
        hub = build_sku_master(
            stock["summary_df"], 
            rep_stats, 
            inv_df
        )
        print(f"✅ Hub 완료: {hub.shape}")

    # 5) 저장
    print("\n💾 Step 5: 데이터 저장")
    print("-" * 40)
    try:
        pq = save_hub_v2(hub, out_dir=out_dir, use_incremental=True)
        print(f"✅ 저장 완료: {pq}")
    except Exception as e:
        print(f"⚠️ Hub v2 저장 실패, 원본 사용: {e}")
        pq = save_as_parquet_duckdb(hub, out_dir=out_dir, use_incremental=True)
        print(f"✅ 저장 완료: {pq}")

    # 6) 삼중 대조 요약 (KPI)
    print("\n📈 Step 6: 삼중 대조 KPI 생성")
    print("-" * 40)
    kpi = {
        "execution_time": (datetime.now() - start_time).total_seconds(),
        "total_records": len(hub),
        "unique_skus": hub["SKU"].nunique(),
        "flow_coverage": hub["flow_code"].nunique() if "flow_code" in hub.columns else 0,
        "location_coverage": hub["Final_Location"].nunique() if "Final_Location" in hub.columns else 0,
        "vendor_distribution": hub["Vendor"].value_counts().to_dict() if "Vendor" in hub.columns else {},
        "data_sources": {
            "reporter_records": rep_stats.get("total_records", 0),
            "stock_records": stock["total_records"],
            "invoice_records": len(inv_df) if inv_df is not None else 0
        }
    }
    
    # Invoice 통과율
    if "inv_match_status" in hub.columns:
        total_inv = hub["inv_match_status"].notna().sum()
        pass_inv = (hub["inv_match_status"] == "PASS").sum()
        kpi["invoice_pass_rate"] = pass_inv / total_inv if total_inv > 0 else 0
        kpi["invoice_fail_count"] = total_inv - pass_inv
    
    # Stock 수량 커버리지
    if "stock_qty" in hub.columns:
        kpi["stock_qty_coverage"] = hub["stock_qty"].notna().sum() / len(hub)
    
    # SQM 커버리지
    if "sku_sqm" in hub.columns:
        kpi["sqm_coverage"] = hub["sku_sqm"].notna().sum() / len(hub)

    # 7) DuckDB 부가 테이블 기록
    print("\n🗄️ Step 7: DuckDB 부가 테이블 생성")
    print("-" * 40)
    try:
        db = f"{out_dir}/sku_master_v2.duckdb" if Path(f"{out_dir}/sku_master_v2.duckdb").exists() else f"{out_dir}/sku_master.duckdb"
        con = duckdb.connect(db)
        
        # 삼중 대조 요약 테이블
        con.execute("CREATE OR REPLACE TABLE recon_summary AS SELECT * FROM hub", {"hub": hub})
        
        # Flow x Location 뷰
        con.execute("""
            CREATE OR REPLACE VIEW v_flow_location AS 
            SELECT Final_Location, flow_code, COUNT(*) AS n 
            FROM recon_summary 
            GROUP BY 1,2 
            ORDER BY 1,2
        """)
        
        # Invoice 실패 상위 20 SKU
        con.execute("""
            CREATE OR REPLACE VIEW v_invoice_failures_top20 AS
            SELECT SKU, inv_match_status, err_gw, err_cbm, GW, CBM
            FROM recon_summary
            WHERE inv_match_status <> 'PASS' OR inv_match_status IS NULL
            ORDER BY COALESCE(ABS(err_gw),0) + COALESCE(ABS(err_cbm),0) DESC
            LIMIT 20
        """)
        
        # 실행 로그 테이블
        run_log = pd.DataFrame([{
            "timestamp": start_time.isoformat(),
            "hitachi_file": hitachi_file,
            "siemens_file": siemens_file,
            "stock_file": stock_file,
            "invoice_file": invoice_dashboard_xlsx,
            "total_records": len(hub),
            "execution_time_seconds": kpi["execution_time"]
        }])
        
        con.execute("CREATE TABLE IF NOT EXISTS run_log (timestamp VARCHAR, hitachi_file VARCHAR, siemens_file VARCHAR, stock_file VARCHAR, invoice_file VARCHAR, total_records INTEGER, execution_time_seconds FLOAT)")
        con.execute("INSERT INTO run_log SELECT * FROM run_log_df", {"run_log_df": run_log})
        
        con.close()
        print("✅ DuckDB 부가 테이블 생성 완료")
        
    except Exception as e:
        print(f"⚠️ DuckDB 부가 테이블 생성 실패: {e}")

    # 8) 최종 결과 출력
    print("\n" + "=" * 60)
    print("🎉 Tri-Source Reconciliation 완료!")
    print("=" * 60)
    print(f"📊 총 레코드: {kpi['total_records']:,}")
    print(f"🕒 실행 시간: {kpi['execution_time']:.2f}초")
    print(f"📈 Flow 커버리지: {kpi['flow_coverage']}개 코드")
    print(f"🏢 위치 커버리지: {kpi['location_coverage']}개 위치")
    
    if kpi.get("invoice_pass_rate") is not None:
        print(f"💰 Invoice 통과율: {kpi['invoice_pass_rate']:.1%}")
    
    if kpi.get("stock_qty_coverage") is not None:
        print(f"📦 Stock 수량 커버리지: {kpi['stock_qty_coverage']:.1%}")
    
    if kpi.get("sqm_coverage") is not None:
        print(f"📐 SQM 커버리지: {kpi['sqm_coverage']:.1%}")
    
    print(f"\n📁 출력 파일: {pq}")
    print(f"🗄️ DuckDB: {db}")
    
    return pq, kpi

def validate_reconciliation_inputs(
    hitachi_file: str,
    siemens_file: str, 
    stock_file: str,
    invoice_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reconciliation 입력 파일 검증
    
    Returns:
        dict: 검증 결과
    """
    validation = {
        "hitachi_file": {"path": hitachi_file, "exists": Path(hitachi_file).exists()},
        "siemens_file": {"path": siemens_file, "exists": Path(siemens_file).exists()},
        "stock_file": {"path": stock_file, "exists": Path(stock_file).exists()},
        "invoice_file": {"path": invoice_file, "exists": Path(invoice_file).exists() if invoice_file else False},
        "all_required_exist": True,
        "validation_passed": True
    }
    
    # 필수 파일 검증
    required_files = [hitachi_file, siemens_file, stock_file]
    for file_path in required_files:
        if not Path(file_path).exists():
            validation["all_required_exist"] = False
            validation["validation_passed"] = False
    
    return validation

if __name__ == "__main__":
    # 테스트 실행
    print("Tri-Source Reconciliation Engine - 테스트 모드")
    
    # 파일 경로 설정 (실제 환경에 맞게 수정)
    hitachi_file = "HVDC_excel_reporter_final_sqm_rev.xlsx"
    siemens_file = "HVDC_excel_reporter_final_sqm_rev.xlsx"
    stock_file = "HVDC_Stock On Hand Report (1).xlsx"
    invoice_file = None  # "HVDC_Invoice_Validation_Dashboard.xlsx"
    
    # 입력 검증
    validation = validate_reconciliation_inputs(hitachi_file, siemens_file, stock_file, invoice_file)
    print("입력 검증 결과:", validation)
    
    if validation["validation_passed"]:
        try:
            pq, kpi = run_reconciliation(hitachi_file, siemens_file, stock_file, invoice_file)
            print(f"\n✅ Reconciliation 완료: {pq}")
            print(f"📊 KPI: {kpi}")
        except Exception as e:
            print(f"❌ Reconciliation 실패: {e}")
    else:
        print("❌ 입력 파일 검증 실패")
