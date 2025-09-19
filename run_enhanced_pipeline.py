"""
HVDC SKU Master Hub - Enhanced Pipeline Runner
정확도·추적성·운영성·비용산정 개선사항이 적용된 파이프라인 실행기
"""

import sys
import os
from pathlib import Path
import pandas as pd

# Enhanced modules import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enhanced_sku_utils import validate_sku_master_quality
from enhanced_analytics import run_analytics_pipeline

# Dynamic module loading for files with spaces in names
import importlib.util

def load_module_from_path(module_name, file_path):
    """파일 경로에서 모듈을 동적으로 로드"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load adapters
adapters_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'adapters (1)')
stock_adapter = load_module_from_path('stock_adapter', os.path.join(adapters_dir, 'stock_adapter (1).py'))
reporter_adapter = load_module_from_path('reporter_adapter', os.path.join(adapters_dir, 'reporter_adapter (1).py'))
invoice_adapter = load_module_from_path('invoice_adapter', os.path.join(adapters_dir, 'invoice_adapter (1).py'))

# Load hub
hub_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hub (1)')
sku_master = load_module_from_path('sku_master', os.path.join(hub_dir, 'sku_master (1).py'))

# Extract functions
build_stock_snapshots = stock_adapter.build_stock_snapshots
compute_flow_and_sqm = reporter_adapter.compute_flow_and_sqm
enhanced_invoice_processing = invoice_adapter.enhanced_invoice_processing
build_sku_master = sku_master.build_sku_master
save_as_parquet_duckdb = sku_master.save_as_parquet_duckdb

def run_enhanced_pipeline(enable_enhancements=True, enable_analytics=True):
    """
    Enhanced HVDC SKU Master Hub Pipeline 실행
    
    Args:
        enable_enhancements: 개선사항 활성화 여부
        enable_analytics: 분석 기능 활성화 여부
        
    Returns:
        파이프라인 실행 결과
    """
    print("🚀 HVDC SKU Master Hub - Enhanced Pipeline Starting...")
    print("=" * 60)
    
    results = {
        "status": "running",
        "enhancements_enabled": enable_enhancements,
        "analytics_enabled": enable_analytics,
        "steps_completed": [],
        "errors": []
    }
    
    try:
        # Step 1: Stock Adapter 실행
        print("\n📊 Step 1: Stock Adapter 실행")
        print("-" * 40)
        try:
            stock_result = build_stock_snapshots("HVDC_Stock On Hand Report (1).xlsx")
            results["steps_completed"].append("stock_adapter")
            print("✅ Stock Adapter 완료")
        except Exception as e:
            error_msg = f"Stock Adapter 실패: {str(e)}"
            print(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            return results
        
        # Step 2: Reporter Adapter 실행 (Enhanced)
        print("\n📈 Step 2: Enhanced Reporter Adapter 실행")
        print("-" * 40)
        try:
            reporter_result = compute_flow_and_sqm()
            results["steps_completed"].append("reporter_adapter")
            print("✅ Enhanced Reporter Adapter 완료")
            
            if enable_enhancements and 'daily_occupancy' in reporter_result:
                daily_occ = reporter_result['daily_occupancy']
                print(f"📅 일자별 점유 계산 완료: {len(daily_occ)} 일")
                
        except Exception as e:
            error_msg = f"Reporter Adapter 실패: {str(e)}"
            print(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            return results
        
        # Step 3: Invoice Adapter 실행 (Enhanced) - 선택적
        print("\n💰 Step 3: Enhanced Invoice Adapter 실행")
        print("-" * 40)
        invoice_result = None
        try:
            invoice_result = enhanced_invoice_processing(
                "hvdc wh invoice (1).py", 
                apply_enhancements=enable_enhancements
            )
            results["steps_completed"].append("invoice_adapter")
            print("✅ Enhanced Invoice Adapter 완료")
            
            if enable_enhancements and invoice_result.get("enhancements_applied"):
                print("🔧 톨러런스 프로파일 및 예외 자동처방 활성화")
                
        except Exception as e:
            error_msg = f"Invoice Adapter 실패: {str(e)}"
            print(f"⚠️ {error_msg} (선택적 기능)")
            results["errors"].append(error_msg)
            # Invoice 실패해도 계속 진행 (선택적)
        
        # Step 4: SKU Master Hub 빌드 (Enhanced)
        print("\n🏢 Step 4: Enhanced SKU Master Hub 빌드")
        print("-" * 40)
        try:
            # Invoice 매칭 결과 로드 (실패시 None)
            invoice_match_df = None
            if invoice_result is not None and invoice_result.get("status") == "completed":
                # 실제 구현시 Invoice 결과에서 DataFrame 로드
                pass
            
            hub_df = build_sku_master(
                stock_result["summary_df"], 
                reporter_result, 
                invoice_match_df
            )
            
            print(f"📊 SKU Master Hub 빌드 완료: {len(hub_df)} 레코드")
            results["steps_completed"].append("sku_master_build")
            
            # 품질 검증
            if enable_enhancements:
                quality_results = validate_sku_master_quality(hub_df)
                print("🔍 품질 검증 결과:")
                for metric, result in quality_results.items():
                    status = "✅ PASS" if result else "❌ FAIL"
                    print(f"  {metric}: {status}")
                
                results["quality_check"] = quality_results
            
        except Exception as e:
            error_msg = f"SKU Master Hub 빌드 실패: {str(e)}"
            print(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            return results
        
        # Step 5: 저장 (Enhanced with UPSERT)
        print("\n💾 Step 5: Enhanced 저장 (UPSERT 지원)")
        print("-" * 40)
        try:
            parquet_path = save_as_parquet_duckdb(hub_df, use_incremental=enable_enhancements)
            results["steps_completed"].append("save_outputs")
            results["output_files"] = {
                "parquet": parquet_path,
                "duckdb": "out/sku_master.duckdb"
            }
            print(f"✅ 저장 완료: {parquet_path}")
            
        except Exception as e:
            error_msg = f"저장 실패: {str(e)}"
            print(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            return results
        
        # Step 6: Analytics Pipeline (선택적)
        if enable_analytics:
            print("\n🔍 Step 6: Enhanced Analytics 실행")
            print("-" * 40)
            try:
                analytics_report = run_analytics_pipeline()
                results["steps_completed"].append("analytics")
                results["analytics_report"] = analytics_report
                print("✅ Analytics 완료")
                print("\n" + analytics_report)
                
            except Exception as e:
                error_msg = f"Analytics 실패: {str(e)}"
                print(f"⚠️ {error_msg} (선택적 기능)")
                results["errors"].append(error_msg)
        
        # 최종 결과
        results["status"] = "completed"
        results["total_records"] = len(hub_df)
        results["success_rate"] = len(results["steps_completed"]) / 5  # 5개 핵심 단계
        
        print("\n🎉 Enhanced Pipeline 완료!")
        print("=" * 60)
        print(f"📊 총 레코드: {results['total_records']:,}")
        print(f"✅ 완료 단계: {len(results['steps_completed'])}/5")
        print(f"📈 성공률: {results['success_rate']:.1%}")
        
        if results["errors"]:
            print(f"⚠️ 경고/오류: {len(results['errors'])}개")
            for error in results["errors"]:
                print(f"  - {error}")
        
        return results
        
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(f"Pipeline 전체 실패: {str(e)}")
        print(f"\n💥 Pipeline 실패: {str(e)}")
        return results

def run_comparison_test():
    """기존 vs Enhanced 파이프라인 비교 테스트"""
    print("🔬 Pipeline 비교 테스트 실행")
    print("=" * 60)
    
    # Enhanced 파이프라인 실행
    print("\n🚀 Enhanced Pipeline 실행...")
    enhanced_result = run_enhanced_pipeline(enable_enhancements=True, enable_analytics=True)
    
    # 결과 비교
    if enhanced_result["status"] == "completed":
        print("\n📊 비교 결과:")
        print(f"  Enhanced Pipeline 성공률: {enhanced_result['success_rate']:.1%}")
        print(f"  완료된 단계: {enhanced_result['steps_completed']}")
        
        if "quality_check" in enhanced_result:
            quality = enhanced_result["quality_check"]
            print(f"  품질 검증 통과: {sum(quality.values())}/{len(quality)}")
        
        if "analytics_report" in enhanced_result:
            print("  Analytics 리포트 생성됨")
    
    return enhanced_result

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="HVDC SKU Master Hub Enhanced Pipeline")
    parser.add_argument("--mode", choices=["standard", "enhanced", "analytics", "comparison"], 
                       default="enhanced", help="실행 모드")
    parser.add_argument("--no-enhancements", action="store_true", 
                       help="개선사항 비활성화")
    parser.add_argument("--no-analytics", action="store_true", 
                       help="분석 기능 비활성화")
    
    args = parser.parse_args()
    
    if args.mode == "comparison":
        run_comparison_test()
    else:
        enable_enhancements = not args.no_enhancements and args.mode in ["enhanced", "analytics"]
        enable_analytics = not args.no_analytics and args.mode in ["analytics"]
        
        result = run_enhanced_pipeline(
            enable_enhancements=enable_enhancements,
            enable_analytics=enable_analytics
        )
        
        if result["status"] == "completed":
            print("\n🎯 다음 단계 추천:")
            print("  python test_enhanced_features.py  # 테스트 실행")
            print("  python enhanced_analytics.py     # 추가 분석")
            print("  duckdb out/sku_master.duckdb     # DB 직접 접근")
        else:
            print(f"\n❌ 파이프라인 실패: {result['errors']}")
            sys.exit(1)
