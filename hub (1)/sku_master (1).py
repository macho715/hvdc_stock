
from dataclasses import dataclass
from typing import Optional
import pandas as pd
import duckdb
import sys
import os

# Enhanced utilities import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enhanced_sku_utils import (
    normalize_sku, guarded_join, validate_flow_transitions, 
    upsert_sku_master, add_provenance, validate_sku_master_quality
)

@dataclass
class SkuMasterRow:
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
    stock_qty: Optional[float]
    sqm_cum: Optional[float]
    inv_match_status: Optional[str]
    err_gw: Optional[float]
    err_cbm: Optional[float]

def build_sku_master(stock_summary_df: pd.DataFrame, reporter_stats: dict,
                     invoice_match_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Enhanced SKU Master Builder with normalization and validation
    
    Args:
        stock_summary_df: Stock adapter 결과
        reporter_stats: Reporter adapter 결과
        invoice_match_df: Invoice adapter 결과 (선택적)
        
    Returns:
        통합된 SKU Master DataFrame
    """
    # 1. Stock 데이터 전처리 및 프로비넌스 추가
    s1 = stock_summary_df.rename(columns={
        "Warehouse": "last_wh",
        "First_Seen": "first_seen", "Last_Seen": "last_seen"
    })
    pick1 = [c for c in ["SKU","Status","first_seen","last_seen","Warehouse","Warehouse_Full_Name","Note"] if c in s1.columns]
    s1 = s1[pick1].copy() if pick1 else stock_summary_df.copy()
    s1 = add_provenance(s1, "STOCK.py", "stock_summary")

    # 2. Reporter 데이터 처리
    dfp = reporter_stats.get("processed_data")
    if dfp is None or dfp.empty:
        raise RuntimeError("Reporter processed_data is empty")

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
    
    # 실제 컬럼명 확인 및 매핑
    print(f"[DEBUG] Available columns in processed_data: {list(dfp.columns)}")
    print(f"[DEBUG] Columns mapping: {cols_map}")
    exist_cols = {k:v for k,v in cols_map.items() if k in dfp.columns}
    print(f"[DEBUG] Existing columns after mapping: {exist_cols}")
    dfp2 = dfp[list(exist_cols.keys())].rename(columns=exist_cols)
    print(f"[DEBUG] dfp2 columns after rename: {list(dfp2.columns)}")
    
    if "SKU" not in dfp2.columns:
        if "SKU" in dfp.columns:
            dfp2 = dfp.rename(columns={"G.W(kgs)":"GW"})
        else:
            raise RuntimeError("processed_data missing SKU/Case No. column.")
    
    dfp2 = add_provenance(dfp2, "hvdc_excel_reporter_final_sqm_rev.py", "processed_data")

    # 3. Invoice 매칭 데이터 처리
    inv = None
    if invoice_match_df is not None and not invoice_match_df.empty:
        inv = invoice_match_df.rename(columns={
            "Match_Status":"inv_match_status","Err_GW":"err_gw","Err_CBM":"err_cbm"
        })
        inv = add_provenance(inv, "hvdc wh invoice.py", "invoice_matching")

    # 4. SKU 정규화 및 조인
    base = dfp2.drop_duplicates(subset=["SKU"]).copy()
    base["hvdc_code_norm"] = None
    
    # 정규화된 조인 수행
    if set(["first_seen","last_seen"]).issubset(s1.columns):
        base = guarded_join(
            base, s1[["SKU","first_seen","last_seen"]], on="SKU", how="left"
        )
    
    if inv is not None:
        base = guarded_join(
            base, inv[["SKU","inv_match_status","err_gw","err_cbm"]], on="SKU", how="left"
        )

    # 5. Flow 전이 검증 (flow_code 컬럼이 있는 경우만)
    if 'flow_code' in base.columns:
        illegal_flows = validate_flow_transitions(base)
        if not illegal_flows.empty:
            print(f"[WARN] Found {len(illegal_flows)} SKUs with illegal flow transitions:")
            print(illegal_flows.head())
    else:
        print("[INFO] Flow code column not found, skipping flow validation")

    base["sqm_cum"] = None

    # 6. 최종 컬럼 정리
    want = ["SKU","hvdc_code_norm","Vendor","Pkg","GW","CBM","first_seen","last_seen",
            "Final_Location","flow_code","flow_desc","sqm_cum","inv_match_status","err_gw","err_cbm",
            "prov_source_file","prov_sheet","row_id"]
    
    print(f"[DEBUG] Available columns in base: {list(base.columns)}")
    print(f"[DEBUG] Required columns: {want}")
    
    for c in want:
        if c not in base.columns:
            print(f"[DEBUG] Adding missing column: {c}")
            base[c] = None
    
    hub = base[want].copy()
    print(f"[DEBUG] Final hub shape: {hub.shape}")
    
    # 7. 품질 검증
    quality_results = validate_sku_master_quality(hub)
    print(f"[INFO] SKU Master Quality Check:")
    for metric, result in quality_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {metric}: {status}")
    
    return hub

def save_as_parquet_duckdb(hub_df: pd.DataFrame, out_dir="out", use_incremental=True):
    """
    Enhanced 저장 함수 with 증분 UPSERT 지원
    
    Args:
        hub_df: 저장할 SKU Master DataFrame
        out_dir: 출력 디렉토리
        use_incremental: 증분 업데이트 사용 여부
        
    Returns:
        Parquet 파일 경로
    """
    import os, pathlib
    pathlib.Path(out_dir).mkdir(exist_ok=True)
    
    # Ensure SKU column is string type to prevent conversion errors
    hub_df_copy = hub_df.copy()
    if 'SKU' in hub_df_copy.columns:
        hub_df_copy['SKU'] = hub_df_copy['SKU'].astype(str)
    
    pq = f"{out_dir}/SKU_MASTER.parquet"
    db = f"{out_dir}/sku_master.duckdb"
    
    if use_incremental and os.path.exists(db):
        # 증분 UPSERT 사용
        print("[INFO] Using incremental UPSERT for SKU Master update")
        upsert_sku_master(hub_df_copy, db, "sku_master")
        # Parquet은 전체 덮어쓰기 (성능상 이유)
        hub_df_copy.to_parquet(pq, index=False)
    else:
        # 전체 재생성
        print("[INFO] Creating new SKU Master database")
        hub_df_copy.to_parquet(pq, index=False)
        con = duckdb.connect(database=db)
        con.execute("DROP TABLE IF EXISTS sku_master")
        con.execute("CREATE TABLE sku_master AS SELECT * FROM read_parquet(?)", [pq])
        con.close()
    
    # 표준 뷰 생성
    from enhanced_sku_utils import create_standard_views
    create_standard_views(db)
    
    print(f"[SUCCESS] SKU Master saved to {pq} and {db}")
    return pq
