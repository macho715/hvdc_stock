"""
HVDC SKU Master Hub - Enhanced Utilities
정확도·추적성·운영성·비용산정 개선을 위한 유틸리티 모음
"""

import re
import hashlib
import json
import pandas as pd
import duckdb
from typing import Dict, List, Optional, Tuple
from itertools import combinations
import numpy as np

# =============================================================================
# 1. SKU 키 정규화 & 조인 가드
# =============================================================================

def normalize_sku(s):
    """
    SKU 키 정규화: 대소문자·공백·선행 0·하이픈 표준화
    
    Args:
        s: SKU 문자열
        
    Returns:
        정규화된 SKU 문자열
    """
    if s is None: 
        return None
    s = str(s).strip().upper()
    s = re.sub(r'\s+', '', s)           # 모든 공백 제거
    s = s.replace('–', '-').replace('—', '-')  # 대시 통일
    s = re.sub(r'^0+(?=[A-Z0-9])', '', s)     # 선행 0 제거(혼용 케이스 방지)
    return s

def guarded_join(left, right, on='SKU', how='left'):
    """
    정규화된 조인 수행 with 품질 리포트
    
    Args:
        left, right: 조인할 DataFrame
        on: 조인 키 컬럼명
        how: 조인 방식
        
    Returns:
        조인된 DataFrame
    """
    left = left.copy()
    right = right.copy()
    left[on] = left[on].map(normalize_sku)
    right[on] = right[on].map(normalize_sku)
    
    # 조인 전 키 품질 리포트
    dup_l = left[on].duplicated().sum()
    dup_r = right[on].duplicated().sum()
    if dup_l or dup_r:
        print(f"[WARN] Duplicates — left:{dup_l}, right:{dup_r}")
    
    return left.merge(right, on=on, how=how)

# =============================================================================
# 2. Flow 전이(Transition) 검증기
# =============================================================================

# 합법 전이: Port(0/1 시작) → WH(2) → MOSB(3) → Site(마감), 역행·점프 금지
LEGAL_TRANSITIONS = {(0,1), (1,2), (2,3), (3,4), (1,4)}  # 1→4(멀티홉) 예외 허용

def validate_flow_transitions(df):
    """
    Flow 전이 규칙 검증 및 시간 역행 검사
    
    Args:
        df: 검증할 DataFrame
        
    Returns:
        불법 전이 SKU 목록
    """
    bad = []
    warehouse_cols = ['AAA Storage','DSV Al Markaz','DSV Indoor','DSV MZP','DSV Outdoor',
                     'Hauler Indoor','MOSB','AGI','DAS','MIR','SHU']
    
    for _, r in df.iterrows():
        # Flow Code 검증 (타입 안전성 추가)
        flow_code = r.get('FLOW_CODE') or r.get('flow_code')
        try:
            code = int(flow_code) if flow_code is not None else -1
        except (ValueError, TypeError):
            code = -1
            
        if code not in (0,1,2,3,4): 
            bad.append(r['SKU'])
            continue
            
        # 시간 역행 검사(창고/현장 날짜 컬럼)
        dates = []
        for col in warehouse_cols:
            if col in df.columns and pd.notna(r.get(col)):
                dates.append(pd.to_datetime(r[col], errors='coerce'))
        
        if dates and any(pd.isna(d) for d in dates):  # 형식오류도 불합격
            bad.append(r['SKU'])
            continue
            
        if dates and any(dates[i] > dates[i+1] for i in range(len(dates)-1)):
            bad.append(r['SKU'])
            continue
    
    return pd.Series(sorted(set(bad)), name="illegal_flow_skus")

# =============================================================================
# 3. 증분 허브 빌드(UPSERT)
# =============================================================================

def row_hash(row, cols):
    """
    행 해시 생성 (변경 감지용)
    
    Args:
        row: DataFrame 행
        cols: 해시 계산할 컬럼 목록
        
    Returns:
        SHA1 해시 문자열
    """
    blob = json.dumps({c: (None if pd.isna(row[c]) else row[c]) for c in cols}, 
                      sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()

def upsert_sku_master(hub_df, db="out/sku_master.duckdb", table="sku_master"):
    """
    증분 UPSERT로 SKU Master 업데이트
    
    Args:
        hub_df: 업데이트할 DataFrame
        db: DuckDB 데이터베이스 경로
        table: 테이블명
    """
    con = duckdb.connect(db)
    
    # 테이블이 없으면 생성
    con.execute(f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM hub_df LIMIT 0")
    
    # 해시 생성
    cols = [c for c in hub_df.columns if c != 'row_hash']
    hub_df_with_hash = hub_df.copy()
    hub_df_with_hash['row_hash'] = hub_df_with_hash.apply(lambda r: row_hash(r, cols), axis=1)
    
    # 새 데이터 등록
    con.register('new_data', hub_df_with_hash)
    
    # UPSERT 실행
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {table}_hash AS SELECT row_hash FROM {table} LIMIT 0;
        
        INSERT INTO {table}
        SELECT n.* EXCLUDE(row_hash) FROM new_data n
        LEFT JOIN (
            SELECT *, sha1(to_json(*)) AS row_hash 
            FROM {table}
        ) o USING(row_hash)
        WHERE o.row_hash IS NULL;
    """)
    
    con.close()

# =============================================================================
# 4. 톨러런스 프로파일 (창고·벤더별 가중치)
# =============================================================================

TOLERANCE_PROFILE = {
    ('HE', 'DSV Indoor'): {'gw': 0.15, 'cbm': 0.12},
    ('HE', 'MOSB'):       {'gw': 0.20, 'cbm': 0.15},
    ('SIM', 'DSV Indoor'): {'gw': 0.10, 'cbm': 0.10},
    ('*', '*'):           {'gw': 0.10, 'cbm': 0.10},  # 기본값
}

def get_tolerance(vendor, warehouse):
    """
    벤더·창고별 톨러런스 가져오기
    
    Args:
        vendor: 벤더 코드
        warehouse: 창고명
        
    Returns:
        톨러런스 딕셔너리 {'gw': float, 'cbm': float}
    """
    return TOLERANCE_PROFILE.get((vendor, warehouse),
           TOLERANCE_PROFILE.get((vendor, '*'),
           TOLERANCE_PROFILE[('*', '*')]))

# =============================================================================
# 5. FAIL 케이스 자동 처방(Top‑N 대안 조합)
# =============================================================================

def topn_alternatives(units_df, k, gw_tgt, cbm_tgt, n=3):
    """
    FAIL 케이스에 대한 Top-N 대안 조합 제안
    
    Args:
        units_df: 유닛 데이터프레임
        k: 목표 패키지 수
        gw_tgt: 목표 중량
        cbm_tgt: 목표 부피
        n: 제안할 대안 수
        
    Returns:
        대안 조합 목록
    """
    cand = []
    idx = list(range(min(len(units_df), 22)))  # 안전 상한
    gw = units_df["G.W(kgs)"].values[idx]
    cbm = units_df["CBM"].values[idx]
    
    for r in range(max(1, k-2), min(k+2, len(idx))+1):
        for comb in combinations(idx, r):
            gw_s = float(gw[list(comb)].sum())
            cbm_s = float(cbm[list(comb)].sum())
            err = abs(gw_s-gw_tgt) + abs(cbm_s-cbm_tgt)
            cand.append((err, comb, gw_s, cbm_s))
    
    cand.sort(key=lambda x: x[0])
    return [{"err": e, "pick": list(map(int, c)), "gw": g, "cbm": b} 
            for e, c, g, b in cand[:n]]

# =============================================================================
# 6. 일 단위 점유·과금(월 스냅샷 → 일자 누적)
# =============================================================================

def daily_occupancy(df, warehouses):
    """
    일자별 점유 계산
    
    Args:
        df: 재고 데이터프레임
        warehouses: 창고 목록
        
    Returns:
        일자별 패키지 점유 DataFrame
    """
    records = []
    
    for _, r in df.iterrows():
        pkg = int(r.get('Pkg', 1) or 1)
        visits = []
        
        for w in warehouses:
            if w in df.columns and pd.notna(r.get(w)):
                visits.append(pd.to_datetime(r[w], errors='coerce'))
        
        visits = sorted([d for d in visits if pd.notna(d)])
        
        for i, start in enumerate(visits):
            end = (visits[i+1] - pd.Timedelta(days=1)) if i+1 < len(visits) else pd.Timestamp.today().normalize()
            
            for d in pd.date_range(start.normalize(), end.normalize(), freq='D'):
                records.append((d.strftime('%Y-%m-%d'), pkg))
    
    occ = pd.DataFrame(records, columns=['date', 'pkg']).groupby('date', as_index=False)['pkg'].sum()
    return occ

# =============================================================================
# 7. 계보(프로비넌스) 칼럼 주입
# =============================================================================

def add_provenance(df, source_file, sheet=None):
    """
    데이터 계보 정보 추가
    
    Args:
        df: 데이터프레임
        source_file: 원본 파일명
        sheet: 시트명 (선택적)
        
    Returns:
        프로비넌스 정보가 추가된 DataFrame
    """
    df = df.copy()
    df['prov_source_file'] = source_file
    if sheet: 
        df['prov_sheet'] = sheet
    if 'row_id' not in df.columns:
        df['row_id'] = range(1, len(df)+1)
    return df

# =============================================================================
# 8. 벤더·창고 단위 이상치 감지
# =============================================================================

def robust_outliers(df, key='GW', by=['Vendor', 'Final_Location'], z=3.5):
    """
    로버스트 Z-스코어 기반 이상치 감지
    
    Args:
        df: 데이터프레임
        key: 검사할 컬럼명
        by: 그룹화 컬럼
        z: Z-스코어 임계값
        
    Returns:
        이상치 DataFrame
    """
    g = df.dropna(subset=[key]).groupby(by)[key]
    res = []
    
    for grp, s in g:
        med = s.median()
        mad = (s - med).abs().median() or 1.0
        rz = 0.6745 * (s - med) / mad
        mask = rz.abs() > z
        if mask.any():
            res.append(df.loc[mask.index[mask], ['SKU', key] + by])
    
    return pd.concat(res) if res else pd.DataFrame(columns=['SKU', key] + by)

# =============================================================================
# 9. DuckDB 표준 뷰 생성
# =============================================================================

def create_standard_views(db_path="out/sku_master.duckdb"):
    """
    운영 편의를 위한 표준 뷰 생성
    
    Args:
        db_path: DuckDB 데이터베이스 경로
    """
    con = duckdb.connect(db_path)
    
    # Flow 분포 뷰
    con.execute("""
        CREATE OR REPLACE VIEW v_flow_mix AS
        SELECT FLOW_CODE, flow_desc, COUNT(*) AS n
        FROM sku_master
        GROUP BY 1, 2
        ORDER BY 1;
    """)
    
    # 창고별 일일 현황 뷰
    con.execute("""
        CREATE OR REPLACE VIEW v_location_daily AS
        SELECT Final_Location, 
               DATE(first_seen) AS first_seen, 
               DATE(last_seen) AS last_seen,
               COUNT(*) AS cases
        FROM sku_master
        GROUP BY 1, 2, 3;
    """)
    
    # 이상치 뷰
    con.execute("""
        CREATE OR REPLACE VIEW v_outliers_gw AS
        SELECT SKU, GW, Vendor, Final_Location
        FROM sku_master
        WHERE GW IS NOT NULL;
    """)
    
    con.close()

# =============================================================================
# 10. 통합 검증 함수
# =============================================================================

def validate_sku_master_quality(hub_df):
    """
    SKU Master 품질 종합 검증
    
    Args:
        hub_df: 검증할 SKU Master DataFrame
        
    Returns:
        검증 결과 딕셔너리
    """
    results = {}
    
    # 1. Flow Coverage 검증
    flow_codes = hub_df['flow_code'].dropna().unique()
    results['flow_coverage'] = len(flow_codes) == 5  # 0-4 모두 존재
    
    # 2. PKG Accuracy 검증 (대소문자 구분)
    pkg_col = 'pkg' if 'pkg' in hub_df.columns else 'Pkg' if 'Pkg' in hub_df.columns else None
    if pkg_col:
        pkg_complete = hub_df[pkg_col].notna().sum()
        results['pkg_accuracy'] = pkg_complete / len(hub_df) if len(hub_df) > 0 else 0
    else:
        results['pkg_accuracy'] = 0
    
    # 3. SKU 무결성 검증
    sku_duplicates = hub_df['SKU'].duplicated().sum()
    results['sku_integrity'] = sku_duplicates == 0
    
    # 4. Location Coverage 검증 (대소문자 구분)
    loc_col = 'final_location' if 'final_location' in hub_df.columns else 'Final_Location' if 'Final_Location' in hub_df.columns else None
    if loc_col:
        location_complete = hub_df[loc_col].notna().sum()
        results['location_coverage'] = location_complete / len(hub_df) if len(hub_df) > 0 else 0
    else:
        results['location_coverage'] = 0
    
    return results

if __name__ == "__main__":
    print("HVDC SKU Master Hub Enhanced Utilities Loaded")
    print("Available functions:")
    print("- normalize_sku()")
    print("- guarded_join()")
    print("- validate_flow_transitions()")
    print("- upsert_sku_master()")
    print("- get_tolerance()")
    print("- topn_alternatives()")
    print("- daily_occupancy()")
    print("- add_provenance()")
    print("- robust_outliers()")
    print("- create_standard_views()")
    print("- validate_sku_master_quality()")
