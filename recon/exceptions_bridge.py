# recon/exceptions_bridge.py
"""
예외→SKU 브리지 영구화
인보이스 엔진이 만든 Exceptions_Only를 SKU 키에 얹어 exceptions_by_sku 테이블·파케 저장
"""
import sys
import os
from pathlib import Path
import pandas as pd
import duckdb
from typing import Optional, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def exceptions_to_sku(
    invoice_dashboard_xlsx: str, 
    all_master_parquet: str, 
    out_dir: str = "out"
) -> pd.DataFrame:
    """
    Invoice Exceptions를 SKU 단위로 매핑하여 영구 테이블 생성
    
    Args:
        invoice_dashboard_xlsx: Invoice 대시보드 Excel 파일
        all_master_parquet: SKU Master Parquet 파일 (HVDC CODE→SKU 매핑용)
        out_dir: 출력 디렉토리
    
    Returns:
        pd.DataFrame: SKU 매핑된 예외 데이터
    """
    print(f"[INFO] Processing exceptions to SKU bridge...")
    print(f"[INFO] Invoice dashboard: {invoice_dashboard_xlsx}")
    print(f"[INFO] SKU master: {all_master_parquet}")
    
    try:
        # 1) Invoice 대시보드에서 Exceptions_Only 읽기
        xl = pd.ExcelFile(invoice_dashboard_xlsx)
        print(f"[INFO] Available sheets: {xl.sheet_names}")
        
        ex = pd.DataFrame()
        if "Exceptions_Only" in xl.sheet_names:
            ex = xl.parse("Exceptions_Only")
            print(f"[INFO] Exceptions_Only loaded: {ex.shape}")
        else:
            print("[WARN] Exceptions_Only sheet not found")
            return pd.DataFrame()
        
        # 2) SKU Master에서 HVDC CODE→SKU 매핑 읽기
        if not Path(all_master_parquet).exists():
            print(f"[ERROR] SKU Master parquet not found: {all_master_parquet}")
            return pd.DataFrame()
        
        # DuckDB를 통해 SKU Master 읽기
        con = duckdb.connect()
        sku_mapping = con.execute(f"SELECT SKU, hvdc_code_norm FROM read_parquet('{all_master_parquet}')").df()
        con.close()
        
        print(f"[INFO] SKU mapping loaded: {sku_mapping.shape}")
        
        # 3) Invoice RAW CODE 정규화 및 매핑
        if "Invoice_RAW_CODE" in ex.columns:
            ex["hvdc_code_norm"] = ex["Invoice_RAW_CODE"].astype(str).str.upper().str.replace(" ", "")
        elif "HVDC_CODE" in ex.columns:
            ex["hvdc_code_norm"] = ex["HVDC_CODE"].astype(str).str.upper().str.replace(" ", "")
        else:
            print("[WARN] No HVDC code column found in exceptions")
            ex["hvdc_code_norm"] = None
        
        # 4) SKU 매핑
        out = ex.merge(sku_mapping, on="hvdc_code_norm", how="left")
        
        # 5) 매핑 결과 통계
        mapped_count = out["SKU"].notna().sum()
        total_count = len(out)
        mapping_rate = mapped_count / total_count if total_count > 0 else 0
        
        print(f"[INFO] SKU mapping results:")
        print(f"  - Total exceptions: {total_count}")
        print(f"  - Mapped to SKU: {mapped_count}")
        print(f"  - Mapping rate: {mapping_rate:.1%}")
        
        # 6) 출력 디렉토리 생성 및 저장
        Path(out_dir).mkdir(exist_ok=True)
        
        # Parquet 저장
        output_file = f"{out_dir}/exceptions_by_sku.parquet"
        out.to_parquet(output_file, index=False)
        print(f"[INFO] Parquet saved: {output_file}")
        
        # DuckDB 저장
        db_file = f"{out_dir}/exceptions_by_sku.duckdb"
        con = duckdb.connect(db_file)
        con.execute("DROP TABLE IF EXISTS exceptions_by_sku")
        con.execute(f"CREATE TABLE exceptions_by_sku AS SELECT * FROM read_parquet('{output_file}')")
        
        # 인덱스 생성
        con.execute("CREATE INDEX IF NOT EXISTS idx_exceptions_sku ON exceptions_by_sku(SKU)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_exceptions_hvdc ON exceptions_by_sku(hvdc_code_norm)")
        
        # 요약 뷰 생성
        con.execute("""
            CREATE OR REPLACE VIEW v_exceptions_summary AS
            SELECT 
                CASE 
                    WHEN SKU IS NOT NULL THEN 'Mapped'
                    ELSE 'Unmapped'
                END AS mapping_status,
                COUNT(*) AS count,
                COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS percentage
            FROM exceptions_by_sku
            GROUP BY 1
        """)
        
        con.execute("""
            CREATE OR REPLACE VIEW v_exceptions_by_sku AS
            SELECT 
                SKU,
                hvdc_code_norm,
                COUNT(*) AS exception_count,
                STRING_AGG(DISTINCT Invoice_RAW_CODE, ', ') AS raw_codes,
                MIN(CASE WHEN Match_Status IS NOT NULL THEN Match_Status END) AS match_status
            FROM exceptions_by_sku
            WHERE SKU IS NOT NULL
            GROUP BY SKU, hvdc_code_norm
            ORDER BY exception_count DESC
        """)
        
        con.close()
        print(f"[INFO] DuckDB saved: {db_file}")
        
        return out
        
    except Exception as e:
        print(f"[ERROR] Failed to process exceptions to SKU: {e}")
        return pd.DataFrame()

def analyze_exceptions_patterns(exceptions_df: pd.DataFrame) -> Dict[str, Any]:
    """
    예외 패턴 분석
    
    Args:
        exceptions_df: 예외 데이터 DataFrame
    
    Returns:
        dict: 분석 결과
    """
    if exceptions_df.empty:
        return {"error": "Empty exceptions data"}
    
    analysis = {
        "total_exceptions": len(exceptions_df),
        "mapping_status": {},
        "top_error_patterns": {},
        "sku_coverage": {}
    }
    
    # 매핑 상태 분석
    if "SKU" in exceptions_df.columns:
        mapped = exceptions_df["SKU"].notna().sum()
        unmapped = exceptions_df["SKU"].isna().sum()
        analysis["mapping_status"] = {
            "mapped": int(mapped),
            "unmapped": int(unmapped),
            "mapping_rate": mapped / len(exceptions_df)
        }
    
    # 상위 오류 패턴
    if "Match_Status" in exceptions_df.columns:
        error_patterns = exceptions_df["Match_Status"].value_counts().head(10)
        analysis["top_error_patterns"] = error_patterns.to_dict()
    
    # SKU별 예외 분포
    if "SKU" in exceptions_df.columns:
        sku_exceptions = exceptions_df["SKU"].value_counts()
        analysis["sku_coverage"] = {
            "unique_skus_with_exceptions": sku_exceptions.nunique(),
            "max_exceptions_per_sku": int(sku_exceptions.max()) if not sku_exceptions.empty else 0,
            "avg_exceptions_per_sku": float(sku_exceptions.mean()) if not sku_exceptions.empty else 0
        }
    
    return analysis

def create_exceptions_report(exceptions_df: pd.DataFrame, output_path: str = "out/exceptions_report.xlsx"):
    """
    예외 분석 리포트 생성
    
    Args:
        exceptions_df: 예외 데이터 DataFrame
        output_path: 리포트 출력 경로
    """
    print(f"[INFO] Creating exceptions report: {output_path}")
    
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 원본 데이터
            exceptions_df.to_excel(writer, sheet_name='Exceptions_Data', index=False)
            
            # 매핑 상태 요약
            if "SKU" in exceptions_df.columns:
                mapping_summary = pd.DataFrame({
                    'Status': ['Mapped', 'Unmapped'],
                    'Count': [
                        exceptions_df["SKU"].notna().sum(),
                        exceptions_df["SKU"].isna().sum()
                    ]
                })
                mapping_summary.to_excel(writer, sheet_name='Mapping_Summary', index=False)
            
            # SKU별 예외 분포
            if "SKU" in exceptions_df.columns and exceptions_df["SKU"].notna().any():
                sku_distribution = exceptions_df["SKU"].value_counts().head(20).reset_index()
                sku_distribution.columns = ['SKU', 'Exception_Count']
                sku_distribution.to_excel(writer, sheet_name='SKU_Distribution', index=False)
            
            # 오류 패턴 분석
            if "Match_Status" in exceptions_df.columns:
                error_patterns = exceptions_df["Match_Status"].value_counts().reset_index()
                error_patterns.columns = ['Match_Status', 'Count']
                error_patterns.to_excel(writer, sheet_name='Error_Patterns', index=False)
        
        print(f"[SUCCESS] Exceptions report created: {output_path}")
        
    except Exception as e:
        print(f"[ERROR] Failed to create exceptions report: {e}")

def run_exceptions_bridge_pipeline(
    invoice_dashboard_xlsx: str,
    sku_master_parquet: str,
    out_dir: str = "out"
) -> Dict[str, Any]:
    """
    예외→SKU 브리지 전체 파이프라인 실행
    
    Args:
        invoice_dashboard_xlsx: Invoice 대시보드 Excel 파일
        sku_master_parquet: SKU Master Parquet 파일
        out_dir: 출력 디렉토리
    
    Returns:
        dict: 실행 결과
    """
    print("=" * 50)
    print("🔗 Exceptions → SKU Bridge Pipeline")
    print("=" * 50)
    
    # 1) 예외→SKU 매핑 실행
    exceptions_df = exceptions_to_sku(invoice_dashboard_xlsx, sku_master_parquet, out_dir)
    
    if exceptions_df.empty:
        return {"success": False, "error": "No exceptions data processed"}
    
    # 2) 패턴 분석
    analysis = analyze_exceptions_patterns(exceptions_df)
    
    # 3) 리포트 생성
    report_path = f"{out_dir}/exceptions_report.xlsx"
    create_exceptions_report(exceptions_df, report_path)
    
    # 4) 결과 요약
    result = {
        "success": True,
        "total_exceptions": len(exceptions_df),
        "mapping_rate": analysis.get("mapping_status", {}).get("mapping_rate", 0),
        "unique_skus_affected": analysis.get("sku_coverage", {}).get("unique_skus_with_exceptions", 0),
        "output_files": {
            "parquet": f"{out_dir}/exceptions_by_sku.parquet",
            "duckdb": f"{out_dir}/exceptions_by_sku.duckdb",
            "report": report_path
        },
        "analysis": analysis
    }
    
    print("\n" + "=" * 50)
    print("✅ Exceptions Bridge Pipeline 완료!")
    print("=" * 50)
    print(f"📊 총 예외: {result['total_exceptions']}")
    print(f"🔗 매핑율: {result['mapping_rate']:.1%}")
    print(f"🏷️ 영향받은 SKU: {result['unique_skus_affected']}")
    print(f"📁 출력 파일:")
    for file_type, path in result["output_files"].items():
        print(f"  - {file_type}: {path}")
    
    return result

if __name__ == "__main__":
    # 테스트 실행
    print("Exceptions Bridge - 테스트 모드")
    
    # 파일 경로 설정 (실제 환경에 맞게 수정)
    invoice_file = "HVDC_Invoice_Validation_Dashboard.xlsx"
    sku_master_file = "out/SKU_MASTER_v2.parquet"
    
    if Path(invoice_file).exists() and Path(sku_master_file).exists():
        result = run_exceptions_bridge_pipeline(invoice_file, sku_master_file)
        print(f"\n결과: {result}")
    else:
        print(f"❌ 파일 없음 - Invoice: {Path(invoice_file).exists()}, SKU Master: {Path(sku_master_file).exists()}")
