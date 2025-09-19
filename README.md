# HVDC SKU Master Dashboard

Tri-Source Reconciliation Dashboard for HVDC Project - Samsung C&T Logistics

## 🚀 Quick Start

### 1. Install Dependencies
```bash
npm install
# or
pnpm install
```

### 2. Environment Setup
```bash
cp env.example .env.local
```

Edit `.env.local`:
```env
# MODE_A = Client-side DuckDB-WASM (Parquet URLs)
# MODE_B = Server-side API (Local DuckDB)
NEXT_PUBLIC_MODE=B

# For MODE_A (optional)
NEXT_PUBLIC_PARQUET_URL_SKU=https://your-bucket.s3.amazonaws.com/out_recon/SKU_MASTER_v2.parquet
NEXT_PUBLIC_PARQUET_URL_EVENTS=https://your-bucket.s3.amazonaws.com/out_recon/events.parquet
NEXT_PUBLIC_PARQUET_URL_EXCEPTIONS=https://your-bucket.s3.amazonaws.com/out_recon/exceptions_by_sku.parquet

# For MODE_B (recommended)
DUCKDB_PATH=../out_recon/sku_master_v2.duckdb
DEFAULT_TOLERANCE_PCT=10
```

### 3. Run Development Server
```bash
npm run dev
# or
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000)

## 📊 Dashboard Features

### 1. Overview Tab
- **KPI Cards**: Total SKUs, Mismatch %, Flow Coverage, Stock Coverage, SQM Coverage
- **Real-time Statistics**: 6,791 SKU records with live reconciliation status

### 2. 3-Way Reconciliation Tab
- **Tolerance Slider**: Adjustable matching tolerance (0-50%)
- **Interactive Table**: Invoice ↔ HVDC Excel ↔ Stock On-Hand comparison
- **Error Analysis**: GW/CBM error tracking with color-coded severity

### 3. Inventory Heatmap Tab
- **Location × Month Matrix**: Visual stock quantity and SQM distribution
- **Color-coded Intensity**: Blue for stock, Green for SQM
- **Summary Statistics**: Total stock, total area, active locations

### 4. Case Flow Tab
- **SKU Timeline**: Visual flow progression (0→1→2→3→4)
- **Flow Code Legend**: Pre-Arrival → Port → Warehouse → MOSB → Site
- **Event Tracking**: First seen, last seen, location transitions

### 5. Exceptions & Audit Tab
- **Exception Filtering**: All/Fail/Pass cases with counts
- **Error Analysis**: GW/CBM error distribution and tolerance violations
- **Audit Trail**: Complete reconciliation history and status

## 🔧 Architecture

### Data Modes

#### MODE_A: Client-Side (DuckDB-WASM)
- **Pros**: No server required, direct Parquet access, fast queries
- **Cons**: Limited by browser memory, requires public Parquet URLs
- **Use Case**: Demo, internal sharing, public datasets

#### MODE_B: Server-Side API (Recommended)
- **Pros**: Full server resources, secure data access, complex queries
- **Cons**: Requires server infrastructure, API rate limits
- **Use Case**: Production, sensitive data, enterprise deployment

### Data Sources
- **SKU Master Hub**: `out_recon/SKU_MASTER_v2.parquet` (6,791 records)
- **Events Data**: `out_recon/events.parquet` (optional)
- **Exceptions**: `out_recon/exceptions_by_sku.parquet` (optional)

## 🚀 Deployment

### Vercel Deployment
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard:
# - DUCKDB_PATH=out_recon/sku_master_v2.duckdb
# - DEFAULT_TOLERANCE_PCT=10
# - NEXT_PUBLIC_MODE=B
```

### Data Upload
For MODE_B, ensure your DuckDB file is accessible:
```bash
# Option 1: Include in repository
git add out_recon/sku_master_v2.duckdb

# Option 2: Upload to Vercel storage
vercel env add DUCKDB_PATH
# Set value to your DuckDB file path
```

## 📁 Project Structure

```
hvdc-dashboard/
├── app/
│   ├── (dashboard)/
│   │   ├── components/          # Dashboard components
│   │   ├── hooks/              # Data fetching hooks
│   │   └── page.tsx            # Main dashboard
│   ├── api/                    # Server API routes
│   │   ├── kpi/route.ts        # KPI statistics
│   │   ├── 3way/route.ts       # 3-way reconciliation
│   │   ├── heatmap/route.ts    # Heatmap data
│   │   └── caseflow/route.ts   # Case flow timeline
│   └── layout.tsx              # Root layout
├── lib/
│   └── duck-server.ts          # DuckDB server utilities
├── public/                     # Static assets
├── .vercel/                    # Vercel configuration
├── vercel.json                 # Deployment config
└── README.md                   # This file
```

## 🔧 API Endpoints

### GET /api/kpi
Returns KPI statistics:
```json
{
  "total": 6791,
  "mismatch_pct": 15.2,
  "flow_coverage": 100.0,
  "stock_coverage": 85.5,
  "sqm_coverage": 100.0,
  "location_count": 12
}
```

### GET /api/3way?tol=10
Returns 3-way reconciliation data with tolerance:
```json
{
  "tolerance": 10,
  "rows": [...],
  "total_count": 1500,
  "fail_count": 228,
  "pass_count": 1272
}
```

### GET /api/heatmap
Returns location × month heatmap data:
```json
{
  "rows": [...],
  "stats": {
    "total_stock": 150000,
    "total_sqm": 2500.5,
    "unique_locations": 12,
    "unique_months": 6
  }
}
```

### GET /api/caseflow?sku=SKU-001
Returns case flow timeline for specific SKU:
```json
{
  "sku": "SKU-001",
  "rows": [...],
  "grouped_by_sku": {...},
  "stats": {
    "total_events": 500,
    "unique_skus": 100,
    "completed_flows": 85
  }
}
```

## 🎯 Performance

- **Data Size**: 6,791 SKU records, ~1.6MB DuckDB
- **Load Time**: <2 seconds for full dashboard
- **Memory Usage**: ~100MB for client-side mode
- **API Response**: <500ms for most queries

## 🔒 Security

- **Environment Variables**: Sensitive data in server environment
- **CORS**: Configured for cross-origin requests
- **Rate Limiting**: Built-in API rate limits
- **Data Privacy**: No PII exposure in client-side mode

## 🛠️ Development

### Adding New Components
1. Create component in `app/(dashboard)/components/`
2. Add to dashboard page tabs
3. Implement data fetching with appropriate hook
4. Add API endpoint if needed

### Customizing Queries
Edit SQL queries in:
- API routes (`app/api/*/route.ts`)
- DuckDB-WASM hooks (`app/(dashboard)/hooks/use-duck.ts`)

### Styling
Uses Tailwind CSS with custom components:
- Consistent color scheme (blue/green/red/orange)
- Responsive design (mobile-first)
- Accessible tables and forms

## 📞 Support

For issues or questions:
1. Check the [System Architecture](./SYSTEM_ARCHITECTURE.md)
2. Review the [Deployment Guide](./DEPLOYMENT_GUIDE.md)
3. Run the validation script: `python validate_system.py`

---

**Built with Next.js 14, DuckDB, and Tailwind CSS** 🚀
