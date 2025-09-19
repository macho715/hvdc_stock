# config/recon_settings.py
"""
Tri-Source Reconciliation 설정 파일
인보이스 매칭 톨러런스, 전략, Flow 검증 규칙 등을 중앙 관리
"""

# 인보이스 매칭 설정
INVOICE_MATCHING = {
    "tolerance": {           # ± 허용치 (kg/m3)
        "default": 0.10,
        "HE": 0.10,          # HITACHI
        "SIM": 0.15,         # SIEMENS
        "monthly_adjustment": {
            # 월별 톨러런스 조정 (예시)
            "2024-01": 0.12,
            "2024-02": 0.08,
        }
    },
    "method": {              # 매칭 전략
        "small_exact_threshold": 18,   # N<=18이면 exact
        "prefer_exact": True,
        "max_combinations": 1000000,   # 조합 수 제한
        "timeout_seconds": 300         # 타임아웃 (5분)
    },
    "validation": {
        "min_gw_threshold": 0.1,       # 최소 GW 임계값
        "min_cbm_threshold": 0.001,    # 최소 CBM 임계값
        "max_error_ratio": 0.5         # 최대 오차 비율 (50%)
    }
}

# Flow 전이 검증 규칙
FLOW_VALIDATION = {
    "legal_transitions": {
        (0, 1): "Pre-Arrival → Port Arrival",
        (1, 2): "Port → Warehouse", 
        (2, 3): "Warehouse → MOSB",
        (3, 4): "MOSB → Site",
        (1, 4): "Direct Port → Site",
        (2, 4): "Warehouse → Site"
    },
    "pre_arrival_rules": {
        "flow_code": 0,
        "description": "Pre-Arrival 상태",
        "warehouse_required": False,
        "max_duration_days": 30
    },
    "time_validation": {
        "max_time_reversal_hours": 24,  # 시간 역행 최대 허용 (24시간)
        "same_day_transfer_allowed": True,  # 동일일자 창고간 이동 허용
        "future_date_tolerance_days": 7     # 미래 날짜 허용 오차 (7일)
    }
}

# 재고 불변식 검증
INVENTORY_INVARIANTS = {
    "inbound_outbound": {
        "rule": "inbound >= outbound",
        "tolerance_percent": 5.0,      # 5% 허용 오차
        "check_monthly": True,
        "check_warehouse": True
    },
    "balance_check": {
        "rule": "inventory = inbound - outbound",
        "tolerance_percent": 5.0,
        "alert_threshold": 10.0        # 10% 이상 차이시 알림
    },
    "sku_consistency": {
        "sqm_validation": True,        # SKU별 SQM 일관성 검사
        "flow_code_validation": True,  # Flow Code 일관성 검사
        "location_validation": True    # 위치 정보 일관성 검사
    }
}

# 데이터 품질 임계값
DATA_QUALITY_THRESHOLDS = {
    "completeness": {
        "min_sku_coverage": 0.95,     # SKU 커버리지 최소 95%
        "min_flow_coverage": 0.90,    # Flow 커버리지 최소 90%
        "min_location_coverage": 0.95 # 위치 커버리지 최소 95%
    },
    "accuracy": {
        "max_duplicate_skus": 0.01,   # 중복 SKU 최대 1%
        "max_null_gw_ratio": 0.05,    # Null GW 최대 5%
        "max_null_cbm_ratio": 0.05,   # Null CBM 최대 5%
        "max_invoice_fail_ratio": 0.20 # Invoice 실패 최대 20%
    },
    "consistency": {
        "max_flow_transition_errors": 0.02,  # Flow 전이 오류 최대 2%
        "max_inventory_discrepancy": 0.05,   # 재고 불일치 최대 5%
        "max_time_reversal_ratio": 0.01      # 시간 역행 최대 1%
    }
}

# DuckDB 설정
DUCKDB_CONFIG = {
    "memory_limit": "2GB",
    "threads": 4,
    "max_memory": "4GB",
    "temp_directory": "out/temp",
    "indexes": {
        "sku_master": ["SKU", "flow_code", "Final_Location", "inv_match_status"],
        "run_log": ["timestamp"],
        "changeset": ["timestamp", "change_type"]
    }
}

# 출력 설정
OUTPUT_CONFIG = {
    "parquet_compression": "snappy",
    "include_metadata": True,
    "save_intermediate": True,
    "backup_previous": True,
    "max_backup_files": 5
}

# 알림 설정
NOTIFICATION_CONFIG = {
    "email_alerts": {
        "enabled": False,
        "recipients": [],
        "thresholds": {
            "execution_time_minutes": 30,
            "error_rate_percent": 10,
            "data_quality_score": 0.80
        }
    },
    "slack_alerts": {
        "enabled": False,
        "webhook_url": "",
        "channels": ["#hvdc-alerts"]
    }
}

# 환경별 설정 오버라이드
ENVIRONMENT_CONFIGS = {
    "dev": {
        "debug": True,
        "save_intermediate": True,
        "notification_enabled": False
    },
    "staging": {
        "debug": True,
        "save_intermediate": True,
        "notification_enabled": True
    },
    "prod": {
        "debug": False,
        "save_intermediate": False,
        "notification_enabled": True,
        "backup_previous": True
    }
}

def get_config(environment: str = "dev") -> dict:
    """
    환경별 설정 반환
    
    Args:
        environment: 환경명 (dev/staging/prod)
    
    Returns:
        dict: 통합 설정
    """
    base_config = {
        "invoice_matching": INVOICE_MATCHING,
        "flow_validation": FLOW_VALIDATION,
        "inventory_invariants": INVENTORY_INVARIANTS,
        "data_quality_thresholds": DATA_QUALITY_THRESHOLDS,
        "duckdb_config": DUCKDB_CONFIG,
        "output_config": OUTPUT_CONFIG,
        "notification_config": NOTIFICATION_CONFIG
    }
    
    # 환경별 오버라이드
    env_config = ENVIRONMENT_CONFIGS.get(environment, ENVIRONMENT_CONFIGS["dev"])
    base_config.update(env_config)
    
    return base_config

def validate_config(config: dict) -> dict:
    """
    설정 검증
    
    Args:
        config: 설정 딕셔너리
    
    Returns:
        dict: 검증 결과
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # 필수 설정 확인
    required_sections = ["invoice_matching", "flow_validation", "data_quality_thresholds"]
    for section in required_sections:
        if section not in config:
            validation_result["errors"].append(f"Missing required section: {section}")
            validation_result["valid"] = False
    
    # 톨러런스 값 검증
    if "invoice_matching" in config:
        tolerance = config["invoice_matching"].get("tolerance", {})
        if tolerance.get("default", 0) <= 0:
            validation_result["errors"].append("Default tolerance must be positive")
            validation_result["valid"] = False
    
    # 임계값 검증
    if "data_quality_thresholds" in config:
        thresholds = config["data_quality_thresholds"]
        for category, values in thresholds.items():
            for key, value in values.items():
                if isinstance(value, (int, float)) and (value < 0 or value > 1):
                    validation_result["warnings"].append(f"{category}.{key} should be between 0 and 1")
    
    return validation_result

if __name__ == "__main__":
    # 설정 테스트
    config = get_config("dev")
    validation = validate_config(config)
    
    print("Configuration Test Results:")
    print(f"Valid: {validation['valid']}")
    if validation['errors']:
        print(f"Errors: {validation['errors']}")
    if validation['warnings']:
        print(f"Warnings: {validation['warnings']}")
    
    print(f"\nDefault tolerance: {config['invoice_matching']['tolerance']['default']}")
    print(f"Flow validation enabled: {bool(config['flow_validation'])}")
    print(f"Data quality thresholds: {len(config['data_quality_thresholds'])} categories")
