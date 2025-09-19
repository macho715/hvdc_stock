import { NextResponse } from "next/server";
import { getConn } from "@/lib/duck-server";

export const runtime = "nodejs";

export async function GET() {
  try {
    const conn = getConn();
    
    const stmt = conn.prepare(`
      SELECT 
        COUNT(*) AS total,
        ROUND(
          COUNT(*) FILTER(WHERE inv_match_status != 'PASS') * 100.0 / NULLIF(COUNT(*), 0), 
          2
        ) AS mismatch_pct,
        ROUND(COUNT(DISTINCT flow_code) / 5.0 * 100, 2) AS flow_coverage,
        ROUND(
          COUNT(*) FILTER(WHERE stock_qty IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0), 
          2
        ) AS stock_coverage,
        ROUND(
          COUNT(*) FILTER(WHERE sku_sqm IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0), 
          2
        ) AS sqm_coverage,
        COUNT(DISTINCT Final_Location) AS location_count
      FROM sku_master
    `);
    
    const rows = stmt.all();
    const result = rows[0] || { 
      total: 0, 
      mismatch_pct: 0, 
      flow_coverage: 0, 
      stock_coverage: 0, 
      sqm_coverage: 0,
      location_count: 0
    };
    
    return NextResponse.json(result);
  } catch (error) {
    console.error("KPI API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch KPI data" },
      { status: 500 }
    );
  }
}
