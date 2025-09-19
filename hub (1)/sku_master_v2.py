# hub/sku_master_v2.py
"""
HVDC SKU Master Hub v2 - 허브 데이터 채움 (수량/면적/정규코드)
기존 구현과 100% 호환되며, stock_qty, sku_sqm, hvdc_code_norm을 채워 저장
"""
import sys
import os
from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd
import duckdb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_sku_utils import add_provenance, validate_sku_master_quality

@dataclass
class SkuMasterRow:
    """SKU Master 행 구조 정의"""
    SKU: str
    hvdc_code_norm: Optional[str]
    vendor: Optional[str]
    pkg: Optional[float]
    gw: Optional[float]
    cbm: Optional[float]
    first_seen: Optional[str]
    last_seen: Optional[str]
    final_location: Optional[str]
    flow_code: Optional[int]
    flow_desc: Optional[str]
    stock_qty: Optional[float]        # 신규: 현재 재고 수량
    sku_sqm: Optional[float]          # 신규: SKU별 면적
    inv_match_status: Optional[str]
    err_gw: Optional[float]
    err_cbm: Optional[float]

def _norm_code(s: Optional[str]) -> Optional[str]:
    """
    HVDC 코드 정규화 (기존 enhanced_sku_utils.normalize_sku와 동일 로직)
    """
    if s is None: 
        return None
    s = str(s).strip().upper()
    s = s.replace(' ', '')
    while '--' in s: 
        s = s.replace('--', '-')
    return s

def build_sku_master_v2(
    stock_summary_df: pd.DataFrame,
    reporter_stats: Dict,
    invoice_match_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    SKU Master Hub v2 - 수량/면적/정규코드 채움
    
    Args:
        stock_summary_df: Stock 요약 데이터
        reporter_stats: Reporter 통계 결과
        invoice_match_df: Invoice 매칭 결과 (선택적)
    
    Returns:
        pd.DataFrame: 보강된 SKU Master Hub
    """
    print("[INFO] Building SKU Master Hub v2...")
    
    # 1) Reporter 기반 컬럼 매핑 (기존 구현과 호환)
    dfp = reporter_stats.get("processed_data")
    if dfp is None or dfp.empty:
        raise RuntimeError("Reporter processed_data is empty")
    
    print(f"[DEBUG] Reporter processed_data shape: {dfp.shape}")
    print(f"[DEBUG] Available columns: {list(dfp.columns)}")
    
    cols_map = {
        "Case No.":"SKU", 
        "Pkg":"Pkg", 
        "G.W(kgs)":"GW", 
        "CBM":"CBM", 
        "Vendor":"Vendor",
        "FLOW_CODE":"flow_code", 
        "FLOW_DESCRIPTION":"flow_desc",
        "Final_Location":"Final_Location", 
        "SQM":"SQM"
    }
    
    exist_cols = {k:v for k,v in cols_map.items() if k in dfp.columns}
    print(f"[DEBUG] Columns mapping: {exist_cols}")
    
    base = dfp[list(exist_cols.keys())].rename(columns=exist_cols).drop_duplicates(subset=["SKU"]).copy()
    base = add_provenance(base, "hvdc_excel_reporter_final_sqm_rev.py", "processed_data")
    
    print(f"[DEBUG] Base data shape after mapping: {base.shape}")

    # 2) Stock 요약과 결합 (최초/최종 관측 및 현재 수량)
    s1 = stock_summary_df.copy()
    
    # Stock 컬럼 정규화
    stock_rename_map = {
        "First_Seen": "first_seen",
        "Last_Seen": "last_seen", 
        "Warehouse": "current_warehouse",
        "Status": "current_status"
    }
    
    for old_col, new_col in stock_rename_map.items():
        if old_col in s1.columns:
            s1 = s1.rename(columns={old_col: new_col})
        else:
            s1[new_col] = None
    
    # QTY 컬럼 찾기 (다양한 이름 지원)
    qty_col = None
    for col in ["QTY", "Quantity", "Pkg", "Package"]:
        if col in s1.columns:
            qty_col = col
            break
    
    if qty_col:
        s1 = s1.rename(columns={qty_col: "stock_qty"})
    else:
        s1["stock_qty"] = None
    
    # Stock 데이터와 결합 (SKU 컬럼 확인)
    if "SKU" in s1.columns:
        stock_pick = ["SKU", "first_seen", "last_seen", "stock_qty", "current_warehouse", "current_status"]
        stock_pick = [col for col in stock_pick if col in s1.columns]
        
        print(f"[DEBUG] Stock columns to merge: {stock_pick}")
        base = base.merge(s1[stock_pick], on="SKU", how="left")
    else:
        print(f"[WARN] SKU column not found in stock data. Available columns: {list(s1.columns)}")
        # Stock 데이터에 SKU가 없으면 기본값 설정
        base["first_seen"] = None
        base["last_seen"] = None
        base["stock_qty"] = None
        base["current_warehouse"] = None
        base["current_status"] = None

    # 3) Invoice 결합 (매치 상태/오차)
    if invoice_match_df is not None and not invoice_match_df.empty:
        print(f"[INFO] Merging invoice data: {invoice_match_df.shape}")
        
        # Invoice 컬럼 정규화
        inv_rename_map = {
            "Match_Status": "inv_match_status",
            "Err_GW": "err_gw", 
            "Err_CBM": "err_cbm"
        }
        
        inv = invoice_match_df.copy()
        for old_col, new_col in inv_rename_map.items():
            if old_col in inv.columns:
                inv = inv.rename(columns={old_col: new_col})
            else:
                inv[new_col] = None
        
        inv_pick = ["SKU", "inv_match_status", "err_gw", "err_cbm"]
        inv_pick = [col for col in inv_pick if col in inv.columns]
        
        base = base.merge(inv[inv_pick], on="SKU", how="left")
    else:
        print("[INFO] No invoice data provided, setting defaults")
        base["inv_match_status"] = None
        base["err_gw"] = None
        base["err_cbm"] = None

    # 4) HVDC 정규 코드/면적 채움
    # HVDC 코드 컬럼 찾기
    hvdc_code_col = None
    for col in ["HVDC CODE", "HVDC_CODE", "hvdc_code", "Code"]:
        if col in dfp.columns:
            hvdc_code_col = col
            break
    
    if hvdc_code_col:
        print(f"[INFO] Using HVDC code column: {hvdc_code_col}")
        base["hvdc_code_norm"] = dfp[hvdc_code_col].map(_norm_code)
    else:
        print("[WARN] No HVDC code column found")
        base["hvdc_code_norm"] = None
    
    # Reporter가 제공하는 SKU별 면적(SQM)을 보존
    if "SQM" in base.columns:
        base["sku_sqm"] = base["SQM"]
        print(f"[INFO] SQM data available: {base['sku_sqm'].notna().sum()} records")
    else:
        base["sku_sqm"] = None
        print("[WARN] No SQM data available")

    # 5) 출력 컬럼 정리 (기존 구조와 호환)
    want = [
        "SKU", "hvdc_code_norm", "Vendor", "Pkg", "GW", "CBM",
        "first_seen", "last_seen", "Final_Location", "flow_code", "flow_desc",
        "stock_qty", "sku_sqm", "inv_match_status", "err_gw", "err_cbm",
        "prov_source_file", "prov_sheet", "row_id"
    ]
    
    for c in want:
        if c not in base.columns:
            print(f"[DEBUG] Adding missing column: {c}")
            base[c] = None
    
    hub = base[want].copy()
    
    # 6) 품질 검증
    quality_results = validate_sku_master_quality(hub)
    print(f"[INFO] SKU Master v2 Quality Check:")
    for metric, result in quality_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {metric}: {status}")
    
    print(f"[SUCCESS] SKU Master Hub v2 built: {hub.shape[0]} records, {hub.shape[1]} columns")
    return hub

def save_hub_v2(hub_df: pd.DataFrame, out_dir: str = "out", use_incremental: bool = True):
    """
    SKU Master Hub v2 저장 (DuckDB + Parquet + 인덱스)
    
    Args:
        hub_df: SKU Master Hub DataFrame
        out_dir: 출력 디렉토리
        use_incremental: 증분 저장 사용 여부
    """
    import pathlib
    
    p = pathlib.Path(out_dir)
    p.mkdir(exist_ok=True)
    
    hub_df = hub_df.copy()
    hub_df["SKU"] = hub_df["SKU"].astype(str)
    
    # Parquet 저장
    pq = f"{out_dir}/SKU_MASTER_v2.parquet"
    hub_df.to_parquet(pq, index=False)
    print(f"[INFO] Parquet saved: {pq}")
    
    # DuckDB 저장
    db = f"{out_dir}/sku_master_v2.duckdb"
    
    if use_incremental and pathlib.Path(db).exists():
        print("[INFO] Using incremental UPSERT for SKU Master v2 update")
        from enhanced_sku_utils import upsert_sku_master
        upsert_sku_master(hub_df, db, "sku_master")
    else:
        print("[INFO] Creating new SKU Master v2 database")
        con = duckdb.connect(db)
        con.execute("DROP TABLE IF EXISTS sku_master")
        con.execute("CREATE TABLE sku_master AS SELECT * FROM read_parquet(?)", [pq])
        
        # 보조 인덱스 생성
        con.execute("CREATE INDEX IF NOT EXISTS idx_sku ON sku_master(SKU)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_flow ON sku_master(flow_code)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_location ON sku_master(Final_Location)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_inv_status ON sku_master(inv_match_status)")
        
        # 표준 뷰 생성
        con.execute("""
            CREATE OR REPLACE VIEW v_flow_mix AS
            SELECT flow_code, flow_desc, COUNT(*) AS n
            FROM sku_master
            GROUP BY 1,2
            ORDER BY 1
        """)
        
        con.execute("""
            CREATE OR REPLACE VIEW v_location_daily AS
            SELECT Final_Location, DATE(first_seen) AS first_seen, DATE(last_seen) AS last_seen,
                   COUNT(*) AS cases
            FROM sku_master
            GROUP BY 1,2,3
        """)
        
        con.execute("""
            CREATE OR REPLACE VIEW v_invoice_failures AS
            SELECT SKU, inv_match_status, err_gw, err_cbm, GW, CBM
            FROM sku_master
            WHERE inv_match_status <> 'PASS' OR inv_match_status IS NULL
            ORDER BY COALESCE(ABS(err_gw),0) + COALESCE(ABS(err_cbm),0) DESC
        """)
        
        con.close()
    
    print(f"[SUCCESS] SKU Master v2 saved: {pq} and {db}")
    return pq

def get_hub_statistics(hub_df: pd.DataFrame) -> dict:
    """
    SKU Master Hub 통계 정보 생성
    
    Returns:
        dict: 통계 정보
    """
    stats = {
        "total_records": len(hub_df),
        "unique_skus": hub_df["SKU"].nunique(),
        "duplicate_skus": hub_df["SKU"].duplicated().sum(),
        "flow_coverage": hub_df["flow_code"].nunique() if "flow_code" in hub_df.columns else 0,
        "location_coverage": hub_df["Final_Location"].nunique() if "Final_Location" in hub_df.columns else 0,
        "vendor_distribution": hub_df["Vendor"].value_counts().to_dict() if "Vendor" in hub_df.columns else {},
        "invoice_pass_rate": None,
        "stock_qty_coverage": None,
        "sqm_coverage": None
    }
    
    # Invoice 통과율
    if "inv_match_status" in hub_df.columns:
        total_inv = hub_df["inv_match_status"].notna().sum()
        pass_inv = (hub_df["inv_match_status"] == "PASS").sum()
        stats["invoice_pass_rate"] = pass_inv / total_inv if total_inv > 0 else 0
    
    # Stock 수량 커버리지
    if "stock_qty" in hub_df.columns:
        stats["stock_qty_coverage"] = hub_df["stock_qty"].notna().sum() / len(hub_df)
    
    # SQM 커버리지
    if "sku_sqm" in hub_df.columns:
        stats["sqm_coverage"] = hub_df["sku_sqm"].notna().sum() / len(hub_df)
    
    return stats

if __name__ == "__main__":
    # 테스트 실행
    print("SKU Master Hub v2 - 테스트 모드")
    print("실제 사용시에는 build_sku_master_v2() 함수를 호출하세요.")
