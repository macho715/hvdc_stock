// HVDC Dashboard Types

export interface KpiData {
  total: number;
  mismatch_pct: number;
  flow_coverage: number;
  stock_coverage: number;
  sqm_coverage: number;
  location_count: number;
}

export interface ThreeWayData {
  SKU: string;
  inv_match_status: string;
  stock_qty: number;
  err_gw: number;
  err_cbm: number;
  GW: number;
  CBM: number;
  Final_Location: string;
  flow_code: number;
  verdict: string;
  tolerance_status: string;
}

export interface HeatmapData {
  loc: string;
  ym: string;
  stock: number;
  sqm: number;
  sku_count: number;
  active_months: number;
  total_stock: number;
  total_sqm: number;
  avg_stock: number;
  avg_sqm: number;
}

export interface CaseFlowData {
  SKU: string;
  Status_Location: string;
  Flow_Code: number;
  ts: string;
  source_type: string;
}

export interface ExceptionData {
  SKU: string;
  hvdc_code_norm: string;
  Invoice_RAW_CODE: string;
  Err_GW: number;
  Err_CBM: number;
  Match_Status: string;
  GW_SumPicked: number;
  CBM_SumPicked: number;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  loading?: boolean;
}

export interface DashboardConfig {
  mode: 'A' | 'B';
  parquetUrls?: {
    sku: string;
    events: string;
    exceptions: string;
  };
  apiBase?: string;
  defaultTolerance?: number;
}

export interface FlowCode {
  code: number;
  description: string;
  color: string;
}

export const FLOW_CODES: FlowCode[] = [
  { code: 0, description: "Pre-Arrival (도착 전)", color: "bg-gray-500" },
  { code: 1, description: "Port Arrival (항만 도착)", color: "bg-blue-500" },
  { code: 2, description: "Warehouse (창고 입고)", color: "bg-green-500" },
  { code: 3, description: "MOSB (MOSB 경유)", color: "bg-yellow-500" },
  { code: 4, description: "Site Delivery (현장 배송)", color: "bg-red-500" }
];

export interface ToleranceLevel {
  level: string;
  threshold: number;
  color: string;
}

export const TOLERANCE_LEVELS: ToleranceLevel[] = [
  { level: "Low", threshold: 5, color: "text-green-600" },
  { level: "Medium", threshold: 10, color: "text-yellow-600" },
  { level: "High", threshold: 20, color: "text-orange-600" },
  { level: "Very High", threshold: 50, color: "text-red-600" }
];

export interface DashboardStats {
  totalRecords: number;
  processingTime: number;
  lastUpdated: string;
  dataQuality: {
    completeness: number;
    accuracy: number;
    consistency: number;
  };
}
