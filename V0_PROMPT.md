# v0.app 프롬프트 (복사해서 붙여넣기)

```
You are v0. Build a Next.js (App Router) dashboard with shadcn/ui + Tailwind.
Tabs: (1) Overview KPI cards, (2) 3-Way Match table with tolerance slider,
(3) Inventory Heatmap (Location × Month), (4) Case Flow timeline/route,
(5) Exceptions table.

Provide a pluggable data layer:
MODE_A = client-only duckdb-wasm reading Parquet URLs (S3/public).
MODE_B = server API routes (/api/kpi, /api/3way, /api/heatmap, /api/caseflow)
that query a local DuckDB file (out_recon/sku_master_v2.duckdb).

Add:
- env-based config (NEXT_PUBLIC_MODE=A|B, PARQUET_URL_* or DUCKDB_PATH)
- reusable fetch hooks, skeletons, error boundaries
- accessible tables (sticky header, column filters) and charts (heatmap, timeline)
- shadcn/ui components and clean layout with tabs

Data source: HVDC SKU Master Hub v2.0 with 6,791 SKU records, Flow codes (0-4), 
Location data, Invoice matching status, Stock quantities, and SQM measurements.
The dashboard should show real-time reconciliation results and exception handling.
```

## 사용법:
1. https://v0.app 에 접속
2. 위 프롬프트를 복사해서 붙여넣기
3. 생성된 코드를 프로젝트에 적용
