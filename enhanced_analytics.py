"""
HVDC SKU Master Hub - Enhanced Analytics
이상치 감지 및 품질 관리 모듈
"""

import sys
import os
import pandas as pd
import duckdb
import numpy as np
from typing import Dict, List, Optional, Tuple

# Enhanced utilities import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enhanced_sku_utils import robust_outliers, validate_sku_master_quality

class HVDCAnalyticsEngine:
    """HVDC SKU Master Hub Analytics Engine"""
    
    def __init__(self, db_path: str = "out/sku_master.duckdb"):
        """
        Analytics Engine 초기화
        
        Args:
            db_path: DuckDB 데이터베이스 경로
        """
        self.db_path = db_path
        self.con = None
        
    def connect(self):
        """DuckDB 연결"""
        self.con = duckdb.connect(self.db_path)
        
    def disconnect(self):
        """DuckDB 연결 해제"""
        if self.con:
            self.con.close()
            
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def detect_weight_outliers(self, z_threshold: float = 3.5) -> pd.DataFrame:
        """
        중량(GW) 이상치 감지
        
        Args:
            z_threshold: Z-스코어 임계값
            
        Returns:
            이상치 DataFrame
        """
        if not self.con:
            raise RuntimeError("Database not connected")
            
        # SKU Master 데이터 로드
        sku_df = self.con.execute("SELECT * FROM sku_master").df()
        
        if sku_df.empty:
            print("[WARN] No data in sku_master table")
            return pd.DataFrame()
        
        # 중량 이상치 감지
        outliers = robust_outliers(sku_df, key='GW', by=['Vendor', 'Final_Location'], z=z_threshold)
        
        if not outliers.empty:
            print(f"[INFO] Detected {len(outliers)} GW outliers with Z-score > {z_threshold}")
            # 이상치를 DuckDB 뷰로 저장
            self.con.register('gw_outliers', outliers)
            self.con.execute("""
                CREATE OR REPLACE VIEW v_outliers_gw AS 
                SELECT * FROM gw_outliers
            """)
        else:
            print("[INFO] No GW outliers detected")
            
        return outliers

    def detect_volume_outliers(self, z_threshold: float = 3.5) -> pd.DataFrame:
        """
        부피(CBM) 이상치 감지
        
        Args:
            z_threshold: Z-스코어 임계값
            
        Returns:
            이상치 DataFrame
        """
        if not self.con:
            raise RuntimeError("Database not connected")
            
        # SKU Master 데이터 로드
        sku_df = self.con.execute("SELECT * FROM sku_master").df()
        
        if sku_df.empty:
            print("[WARN] No data in sku_master table")
            return pd.DataFrame()
        
        # 부피 이상치 감지
        outliers = robust_outliers(sku_df, key='CBM', by=['Vendor', 'Final_Location'], z=z_threshold)
        
        if not outliers.empty:
            print(f"[INFO] Detected {len(outliers)} CBM outliers with Z-score > {z_threshold}")
            # 이상치를 DuckDB 뷰로 저장
            self.con.register('cbm_outliers', outliers)
            self.con.execute("""
                CREATE OR REPLACE VIEW v_outliers_cbm AS 
                SELECT * FROM cbm_outliers
            """)
        else:
            print("[INFO] No CBM outliers detected")
            
        return outliers

    def comprehensive_quality_check(self) -> Dict:
        """
        종합 품질 검사
        
        Returns:
            품질 검사 결과 딕셔너리
        """
        if not self.con:
            raise RuntimeError("Database not connected")
            
        # SKU Master 데이터 로드
        sku_df = self.con.execute("SELECT * FROM sku_master").df()
        
        if sku_df.empty:
            return {"error": "No data in sku_master table"}
        
        # 기본 품질 검증
        quality_results = validate_sku_master_quality(sku_df)
        
        # 추가 분석
        additional_checks = {
            "total_records": len(sku_df),
            "unique_skus": sku_df['SKU'].nunique(),
            "duplicate_skus": sku_df['SKU'].duplicated().sum(),
            "null_gw_count": sku_df['GW'].isna().sum(),
            "null_cbm_count": sku_df['CBM'].isna().sum(),
            "null_vendor_count": sku_df['Vendor'].isna().sum(),
            "null_location_count": sku_df['Final_Location'].isna().sum(),
            "flow_code_distribution": sku_df['flow_code'].value_counts().to_dict(),
            "vendor_distribution": sku_df['Vendor'].value_counts().to_dict(),
            "location_distribution": sku_df['Final_Location'].value_counts().head(10).to_dict()
        }
        
        # 이상치 검사
        gw_outliers = self.detect_weight_outliers()
        cbm_outliers = self.detect_volume_outliers()
        
        additional_checks.update({
            "gw_outliers_count": len(gw_outliers),
            "cbm_outliers_count": len(cbm_outliers),
            "gw_outliers_skus": gw_outliers['SKU'].tolist() if not gw_outliers.empty else [],
            "cbm_outliers_skus": cbm_outliers['SKU'].tolist() if not cbm_outliers.empty else []
        })
        
        return {
            "basic_quality": quality_results,
            "detailed_analysis": additional_checks
        }

    def generate_quality_report(self) -> str:
        """
        품질 리포트 생성
        
        Returns:
            포맷된 리포트 문자열
        """
        results = self.comprehensive_quality_check()
        
        if "error" in results:
            return f"❌ Error: {results['error']}"
        
        report = []
        report.append("🔍 HVDC SKU Master Hub - Quality Report")
        report.append("=" * 50)
        
        # 기본 품질 검증 결과
        report.append("\n📊 Basic Quality Checks:")
        for metric, result in results["basic_quality"].items():
            status = "✅ PASS" if result else "❌ FAIL"
            report.append(f"  {metric}: {status}")
        
        # 상세 분석 결과
        details = results["detailed_analysis"]
        report.append(f"\n📈 Data Statistics:")
        report.append(f"  Total Records: {details['total_records']:,}")
        report.append(f"  Unique SKUs: {details['unique_skus']:,}")
        report.append(f"  Duplicate SKUs: {details['duplicate_skus']}")
        report.append(f"  Null GW Count: {details['null_gw_count']}")
        report.append(f"  Null CBM Count: {details['null_cbm_count']}")
        
        # 이상치 정보
        report.append(f"\n⚠️ Outlier Detection:")
        report.append(f"  GW Outliers: {details['gw_outliers_count']}")
        report.append(f"  CBM Outliers: {details['cbm_outliers_count']}")
        
        if details['gw_outliers_skus']:
            report.append(f"  GW Outlier SKUs: {', '.join(details['gw_outliers_skus'][:5])}{'...' if len(details['gw_outliers_skus']) > 5 else ''}")
        
        if details['cbm_outliers_skus']:
            report.append(f"  CBM Outlier SKUs: {', '.join(details['cbm_outliers_skus'][:5])}{'...' if len(details['cbm_outliers_skus']) > 5 else ''}")
        
        # Flow Code 분포
        report.append(f"\n🔄 Flow Code Distribution:")
        for flow_code, count in details['flow_code_distribution'].items():
            flow_desc = {
                0: "Pre Arrival",
                1: "Port → Site",
                2: "Port → WH → Site", 
                3: "Port → WH → MOSB → Site",
                4: "Multi-hop"
            }.get(flow_code, f"Unknown({flow_code})")
            report.append(f"  Flow {flow_code} ({flow_desc}): {count:,}")
        
        return "\n".join(report)

    def create_analytics_views(self):
        """분석용 뷰 생성"""
        if not self.con:
            raise RuntimeError("Database not connected")
        
        # 품질 지표 뷰
        self.con.execute("""
            CREATE OR REPLACE VIEW v_quality_metrics AS
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT SKU) as unique_skus,
                COUNT(*) - COUNT(DISTINCT SKU) as duplicate_skus,
                SUM(CASE WHEN GW IS NULL THEN 1 ELSE 0 END) as null_gw_count,
                SUM(CASE WHEN CBM IS NULL THEN 1 ELSE 0 END) as null_cbm_count,
                SUM(CASE WHEN Vendor IS NULL THEN 1 ELSE 0 END) as null_vendor_count,
                SUM(CASE WHEN Final_Location IS NULL THEN 1 ELSE 0 END) as null_location_count
            FROM sku_master
        """)
        
        # 벤더별 통계 뷰
        self.con.execute("""
            CREATE OR REPLACE VIEW v_vendor_stats AS
            SELECT 
                Vendor,
                COUNT(*) as sku_count,
                ROUND(AVG(GW), 2) as avg_weight,
                ROUND(AVG(CBM), 2) as avg_volume,
                ROUND(SUM(Pkg), 0) as total_packages
            FROM sku_master
            WHERE Vendor IS NOT NULL
            GROUP BY Vendor
            ORDER BY sku_count DESC
        """)
        
        # 창고별 통계 뷰
        self.con.execute("""
            CREATE OR REPLACE VIEW v_location_stats AS
            SELECT 
                Final_Location,
                COUNT(*) as sku_count,
                ROUND(AVG(GW), 2) as avg_weight,
                ROUND(AVG(CBM), 2) as avg_volume,
                ROUND(SUM(Pkg), 0) as total_packages
            FROM sku_master
            WHERE Final_Location IS NOT NULL
            GROUP BY Final_Location
            ORDER BY sku_count DESC
        """)
        
        print("[SUCCESS] Analytics views created successfully")

def run_analytics_pipeline(db_path: str = "out/sku_master.duckdb") -> str:
    """
    분석 파이프라인 실행
    
    Args:
        db_path: DuckDB 데이터베이스 경로
        
    Returns:
        품질 리포트
    """
    with HVDCAnalyticsEngine(db_path) as engine:
        # 분석 뷰 생성
        engine.create_analytics_views()
        
        # 품질 리포트 생성
        report = engine.generate_quality_report()
        
        return report

if __name__ == "__main__":
    # 분석 파이프라인 실행
    report = run_analytics_pipeline()
    print(report)
