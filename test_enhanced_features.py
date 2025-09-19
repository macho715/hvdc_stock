"""
HVDC SKU Master Hub - Enhanced Features Test Suite
pytest 기반 테스트 스위트 for 전이·톨러런스·일자과금 검증
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# Enhanced utilities import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from enhanced_sku_utils import (
    normalize_sku, guarded_join, validate_flow_transitions,
    get_tolerance, topn_alternatives, daily_occupancy,
    add_provenance, robust_outliers, validate_sku_master_quality
)

# Test data fixtures
@pytest.fixture
def sample_sku_data():
    """샘플 SKU 데이터"""
    return pd.DataFrame({
        'SKU': ['SKU001', 'sku-002', '  SKU003  ', '000SKU004', 'SKU005'],
        'Vendor': ['HITACHI', 'HITACHI', 'SIEMENS', 'HITACHI', 'SIEMENS'],
        'GW': [100.5, 200.0, 150.3, 300.7, 250.0],
        'CBM': [2.5, 4.0, 3.2, 6.1, 5.0],
        'Final_Location': ['DSV Indoor', 'MOSB', 'DSV Indoor', 'DSV Outdoor', 'MOSB']
    })

@pytest.fixture
def sample_flow_data():
    """샘플 Flow 데이터 (시간 역행 포함)"""
    return pd.DataFrame({
        'SKU': ['SKU001', 'SKU002', 'SKU003', 'SKU004'],
        'FLOW_CODE': [1, 1, 2, 3],  # SKU001을 정상 Flow Code로 변경
        'AAA Storage': ['2024-01-01', '2024-01-02', None, None],
        'DSV Indoor': ['2024-01-03', '2024-01-01', '2024-01-05', None],  # SKU002 시간 역행
        'MOSB': [None, '2024-01-04', '2024-01-04', '2024-01-06'],  # SKU003 시간 역행
        'DAS': [None, None, None, '2024-01-07']
    })

@pytest.fixture
def sample_units_data():
    """샘플 유닛 데이터 (대안 제안용)"""
    return pd.DataFrame({
        'index': range(10),
        'G.W(kgs)': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        'CBM': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    })

@pytest.fixture
def sample_occupancy_data():
    """샘플 점유 데이터"""
    return pd.DataFrame({
        'SKU': ['SKU001', 'SKU002', 'SKU003'],
        'Pkg': [2, 3, 1],
        'DSV Indoor': ['2024-01-01', '2024-01-02', None],
        'MOSB': ['2024-01-03', '2024-01-05', '2024-01-04'],
        'DAS': [None, None, '2024-01-06']
    })

# =============================================================================
# SKU 정규화 테스트
# =============================================================================

class TestSKUNormalization:
    """SKU 정규화 기능 테스트"""
    
    def test_normalize_sku_basic(self):
        """기본 SKU 정규화 테스트"""
        assert normalize_sku('SKU001') == 'SKU001'
        assert normalize_sku('sku-002') == 'SKU-002'
        assert normalize_sku('  SKU003  ') == 'SKU003'
        assert normalize_sku('000SKU004') == 'SKU004'
        assert normalize_sku(None) is None
    
    def test_normalize_sku_dash_variants(self):
        """대시 변형 정규화 테스트"""
        assert normalize_sku('SKU–001') == 'SKU-001'
        assert normalize_sku('SKU—001') == 'SKU-001'
        assert normalize_sku('SKU-001') == 'SKU-001'
    
    def test_normalize_sku_whitespace(self):
        """공백 제거 테스트"""
        assert normalize_sku('SKU 001') == 'SKU001'
        assert normalize_sku('SKU\t001') == 'SKU001'
        assert normalize_sku('SKU\n001') == 'SKU001'
    
    def test_guarded_join_duplicates(self, sample_sku_data):
        """중복 키 조인 테스트"""
        left = sample_sku_data[['SKU', 'Vendor']].copy()
        right = sample_sku_data[['SKU', 'GW']].copy()
        
        # 중복 추가
        left = pd.concat([left, pd.DataFrame({'SKU': ['SKU001'], 'Vendor': ['DUPLICATE']})])
        
        result = guarded_join(left, right, on='SKU')
        assert len(result) > 0  # 조인은 성공해야 함

# =============================================================================
# Flow 전이 검증 테스트
# =============================================================================

class TestFlowTransitions:
    """Flow 전이 검증 테스트"""
    
    def test_validate_flow_transitions_basic(self, sample_flow_data):
        """기본 Flow 전이 검증 테스트"""
        illegal_flows = validate_flow_transitions(sample_flow_data)
        
        # SKU002와 SKU003이 시간 역행으로 인해 불법 전이로 감지되어야 함
        assert 'SKU002' in illegal_flows.values
        assert 'SKU003' in illegal_flows.values
        # SKU001과 SKU004는 정상 케이스이므로 불법 전이 목록에 없어야 함
        assert 'SKU001' not in illegal_flows.values
        assert 'SKU004' not in illegal_flows.values
    
    def test_validate_flow_transitions_invalid_codes(self):
        """잘못된 Flow Code 테스트"""
        df = pd.DataFrame({
            'SKU': ['SKU001', 'SKU002'],
            'FLOW_CODE': [5, -1],  # 잘못된 코드
            'AAA Storage': ['2024-01-01', '2024-01-02']
        })
        
        illegal_flows = validate_flow_transitions(df)
        assert 'SKU001' in illegal_flows.values
        assert 'SKU002' in illegal_flows.values

# =============================================================================
# 톨러런스 프로파일 테스트
# =============================================================================

class TestToleranceProfiles:
    """톨러런스 프로파일 테스트"""
    
    def test_get_tolerance_basic(self):
        """기본 톨러런스 테스트"""
        # HITACHI DSV Indoor
        tol = get_tolerance('HE', 'DSV Indoor')
        assert tol['gw'] == 0.15
        assert tol['cbm'] == 0.12
        
        # HITACHI MOSB
        tol = get_tolerance('HE', 'MOSB')
        assert tol['gw'] == 0.20
        assert tol['cbm'] == 0.15
        
        # SIEMENS DSV Indoor
        tol = get_tolerance('SIM', 'DSV Indoor')
        assert tol['gw'] == 0.10
        assert tol['cbm'] == 0.10
        
        # 기본값
        tol = get_tolerance('UNKNOWN', 'UNKNOWN')
        assert tol['gw'] == 0.10
        assert tol['cbm'] == 0.10
    
    def test_get_tolerance_wildcard(self):
        """와일드카드 톨러런스 테스트"""
        # 벤더 와일드카드
        tol = get_tolerance('HE', 'UNKNOWN')
        assert tol['gw'] == 0.10
        assert tol['cbm'] == 0.10
        
        # 창고 와일드카드
        tol = get_tolerance('UNKNOWN', 'DSV Indoor')
        assert tol['gw'] == 0.10
        assert tol['cbm'] == 0.10

# =============================================================================
# 대안 조합 제안 테스트
# =============================================================================

class TestAlternativeSuggestions:
    """대안 조합 제안 테스트"""
    
    def test_topn_alternatives_basic(self, sample_units_data):
        """기본 대안 조합 제안 테스트"""
        alternatives = topn_alternatives(sample_units_data, k=2, gw_tgt=30, cbm_tgt=0.3, n=3)
        
        assert len(alternatives) <= 3
        for alt in alternatives:
            assert 'err' in alt
            assert 'pick' in alt
            assert 'gw' in alt
            assert 'cbm' in alt
            assert isinstance(alt['pick'], list)
    
    def test_topn_alternatives_empty_input(self):
        """빈 입력 데이터 테스트"""
        empty_df = pd.DataFrame(columns=['G.W(kgs)', 'CBM'])
        alternatives = topn_alternatives(empty_df, k=1, gw_tgt=10, cbm_tgt=0.1, n=3)
        assert len(alternatives) == 0
    
    def test_topn_alternatives_large_k(self, sample_units_data):
        """큰 k 값 테스트"""
        alternatives = topn_alternatives(sample_units_data, k=20, gw_tgt=100, cbm_tgt=1.0, n=3)
        # k가 데이터 크기보다 클 때도 처리되어야 함
        assert len(alternatives) <= 3

# =============================================================================
# 일자별 점유 테스트
# =============================================================================

class TestDailyOccupancy:
    """일자별 점유 계산 테스트"""
    
    def test_daily_occupancy_basic(self, sample_occupancy_data):
        """기본 일자별 점유 테스트"""
        warehouses = ['DSV Indoor', 'MOSB', 'DAS']
        daily_occ = daily_occupancy(sample_occupancy_data, warehouses)
        
        assert not daily_occ.empty
        assert 'date' in daily_occ.columns
        assert 'pkg' in daily_occ.columns
        
        # 날짜가 올바른 형식인지 확인
        for date_str in daily_occ['date']:
            datetime.strptime(date_str, '%Y-%m-%d')
    
    def test_daily_occupancy_empty_data(self):
        """빈 데이터 테스트"""
        empty_df = pd.DataFrame(columns=['SKU', 'Pkg'])
        warehouses = ['DSV Indoor']
        daily_occ = daily_occupancy(empty_df, warehouses)
        assert daily_occ.empty
    
    def test_daily_occupancy_no_warehouses(self, sample_occupancy_data):
        """창고 컬럼이 없는 경우 테스트"""
        warehouses = ['NONEXISTENT']
        daily_occ = daily_occupancy(sample_occupancy_data, warehouses)
        assert daily_occ.empty

# =============================================================================
# 프로비넌스 테스트
# =============================================================================

class TestProvenance:
    """프로비넌스 추적 테스트"""
    
    def test_add_provenance_basic(self, sample_sku_data):
        """기본 프로비넌스 추가 테스트"""
        result = add_provenance(sample_sku_data, "test_file.xlsx", "test_sheet")
        
        assert 'prov_source_file' in result.columns
        assert 'prov_sheet' in result.columns
        assert 'row_id' in result.columns
        
        assert all(result['prov_source_file'] == "test_file.xlsx")
        assert all(result['prov_sheet'] == "test_sheet")
        assert list(result['row_id']) == list(range(1, len(sample_sku_data) + 1))
    
    def test_add_provenance_no_sheet(self, sample_sku_data):
        """시트 없는 프로비넌스 테스트"""
        result = add_provenance(sample_sku_data, "test_file.xlsx")
        
        assert 'prov_source_file' in result.columns
        assert 'prov_sheet' not in result.columns
        assert 'row_id' in result.columns

# =============================================================================
# 이상치 감지 테스트
# =============================================================================

class TestOutlierDetection:
    """이상치 감지 테스트"""
    
    def test_robust_outliers_normal_data(self):
        """정상 데이터 이상치 테스트"""
        df = pd.DataFrame({
            'SKU': [f'SKU{i:03d}' for i in range(100)],
            'GW': np.random.normal(100, 10, 100),  # 정상 분포
            'Vendor': ['HITACHI'] * 100,
            'Final_Location': ['DSV Indoor'] * 100
        })
        
        outliers = robust_outliers(df, key='GW', by=['Vendor', 'Final_Location'], z=3.5)
        # 정상 분포에서는 이상치가 거의 없어야 함
        assert len(outliers) < 5
    
    def test_robust_outliers_with_outliers(self):
        """이상치가 포함된 데이터 테스트"""
        normal_data = pd.DataFrame({
            'SKU': [f'SKU{i:03d}' for i in range(95)],
            'GW': np.random.normal(100, 10, 95),
            'Vendor': ['HITACHI'] * 95,
            'Final_Location': ['DSV Indoor'] * 95
        })
        
        outlier_data = pd.DataFrame({
            'SKU': ['SKU996', 'SKU997', 'SKU998', 'SKU999', 'SKU1000'],
            'GW': [500, 600, 700, 800, 900],  # 명백한 이상치
            'Vendor': ['HITACHI'] * 5,
            'Final_Location': ['DSV Indoor'] * 5
        })
        
        df = pd.concat([normal_data, outlier_data])
        outliers = robust_outliers(df, key='GW', by=['Vendor', 'Final_Location'], z=3.5)
        
        # 이상치가 감지되어야 함
        assert len(outliers) >= 3
        assert any('SKU99' in sku for sku in outliers['SKU'].values)

# =============================================================================
# SKU Master 품질 검증 테스트
# =============================================================================

class TestSKUMasterQuality:
    """SKU Master 품질 검증 테스트"""
    
    def test_validate_sku_master_quality_good_data(self):
        """좋은 데이터 품질 검증 테스트"""
        df = pd.DataFrame({
            'SKU': [f'SKU{i:03d}' for i in range(100)],
            'pkg': [1] * 100,
            'flow_code': [0, 1, 2, 3, 4] * 20,
            'final_location': ['DSV Indoor', 'MOSB', 'DAS'] * 33 + ['DAS']
        })
        
        results = validate_sku_master_quality(df)
        
        assert results['flow_coverage'] == True  # 0-4 모든 Flow Code 존재
        assert results['pkg_accuracy'] == 1.0    # 100% 완전성
        assert results['sku_integrity'] == True  # 중복 없음
        assert results['location_coverage'] == 1.0  # 100% 완전성
    
    def test_validate_sku_master_quality_poor_data(self):
        """나쁜 데이터 품질 검증 테스트"""
        df = pd.DataFrame({
            'SKU': ['SKU001', 'SKU001', 'SKU003'],  # 중복 있음
            'pkg': [1, 2, None],  # 누락 있음
            'flow_code': [0, 1, 5],  # 잘못된 Flow Code
            'final_location': ['DSV Indoor', None, 'MOSB']  # 누락 있음
        })
        
        results = validate_sku_master_quality(df)
        
        assert results['flow_coverage'] == False  # Flow Code 불완전
        assert results['pkg_accuracy'] < 1.0      # 완전성 부족
        assert results['sku_integrity'] == False  # 중복 있음
        assert results['location_coverage'] < 1.0  # 완전성 부족

# =============================================================================
# 통합 테스트
# =============================================================================

class TestIntegration:
    """통합 테스트"""
    
    def test_end_to_end_pipeline(self, sample_sku_data, sample_flow_data):
        """End-to-End 파이프라인 테스트"""
        # 1. SKU 정규화
        normalized_skus = sample_sku_data['SKU'].map(normalize_sku)
        assert all(sku == sku.upper() for sku in normalized_skus)
        
        # 2. Flow 전이 검증
        illegal_flows = validate_flow_transitions(sample_flow_data)
        assert len(illegal_flows) > 0
        
        # 3. 프로비넌스 추가
        with_provenance = add_provenance(sample_sku_data, "test_source")
        assert 'prov_source_file' in with_provenance.columns
        
        # 4. 품질 검증 (flow_code 컬럼 추가)
        with_provenance['flow_code'] = [0, 1, 2, 3, 4]  # 테스트용 flow_code 추가
        quality = validate_sku_master_quality(with_provenance)
        assert isinstance(quality, dict)
        assert 'flow_coverage' in quality

# =============================================================================
# 성능 테스트
# =============================================================================

class TestPerformance:
    """성능 테스트"""
    
    def test_normalize_sku_performance(self):
        """SKU 정규화 성능 테스트"""
        large_sku_list = [f'SKU{i:06d}' for i in range(10000)]
        
        start_time = datetime.now()
        normalized = [normalize_sku(sku) for sku in large_sku_list]
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        assert duration < 1.0  # 1초 이내 완료
        assert len(normalized) == 10000
    
    def test_robust_outliers_performance(self):
        """이상치 감지 성능 테스트"""
        large_df = pd.DataFrame({
            'SKU': [f'SKU{i:06d}' for i in range(10000)],
            'GW': np.random.normal(100, 10, 10000),
            'Vendor': ['HITACHI'] * 10000,
            'Final_Location': ['DSV Indoor'] * 10000
        })
        
        start_time = datetime.now()
        outliers = robust_outliers(large_df, key='GW', by=['Vendor', 'Final_Location'])
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        assert duration < 5.0  # 5초 이내 완료

if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v", "--tb=short"])
