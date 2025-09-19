import { NextResponse } from "next/server";
import { getConn } from "@/lib/duck-server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const tolerance = Number(searchParams.get("tol") ?? process.env.DEFAULT_TOLERANCE_PCT ?? 10);
    
    const conn = getConn();
    
    const sql = `
      WITH base AS (
        SELECT 
          s.SKU, 
          s.inv_match_status, 
          s.stock_qty,
          COALESCE(s.err_gw, 0) AS err_gw, 
          COALESCE(s.err_cbm, 0) AS err_cbm,
          s.GW,
          s.CBM,
          s.Final_Location,
          s.flow_code
        FROM sku_master s
      ),
      filtered AS (
        SELECT *,
          CASE 
            WHEN inv_match_status != 'PASS' THEN 'FAIL' 
            ELSE 'PASS' 
          END AS verdict,
          -- 톨러런스 기반 필터링 (실제 구현에서는 더 복잡한 로직 필요)
          CASE 
            WHEN ABS(err_gw) > (GW * ${tolerance} / 100) THEN 'GW_TOLERANCE_EXCEEDED'
            WHEN ABS(err_cbm) > (CBM * ${tolerance} / 100) THEN 'CBM_TOLERANCE_EXCEEDED'
            ELSE 'WITHIN_TOLERANCE'
          END AS tolerance_status
        FROM base
      )
      SELECT 
        SKU, 
        inv_match_status, 
        stock_qty, 
        err_gw, 
        err_cbm,
        GW,
        CBM,
        Final_Location,
        flow_code,
        verdict,
        tolerance_status
      FROM filtered
      ORDER BY ABS(err_gw) DESC, ABS(err_cbm) DESC
      LIMIT 5000
    `;
    
    const rows = conn.prepare(sql).all();
    
    return NextResponse.json({ 
      tolerance,
      rows,
      total_count: rows.length,
      fail_count: rows.filter(r => r.verdict === 'FAIL').length,
      pass_count: rows.filter(r => r.verdict === 'PASS').length
    });
  } catch (error) {
    console.error("3-Way API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch 3-way reconciliation data" },
      { status: 500 }
    );
  }
}
