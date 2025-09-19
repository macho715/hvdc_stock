import { NextResponse } from "next/server";
import { getConn } from "@/lib/duck-server";

export const runtime = "nodejs";

export async function GET() {
  try {
    const conn = getConn();
    
    const sql = `
      WITH monthly_data AS (
        SELECT 
          COALESCE(Final_Location, 'Unknown') AS loc,
          CASE 
            WHEN first_seen IS NOT NULL THEN strftime(first_seen, '%Y-%m-01')
            WHEN last_seen IS NOT NULL THEN strftime(last_seen, '%Y-%m-01')
            ELSE '2024-01-01'
          END AS ym,
          SUM(COALESCE(stock_qty, 0)) AS stock,
          SUM(COALESCE(sku_sqm, 0)) AS sqm,
          COUNT(*) AS sku_count
        FROM sku_master
        GROUP BY 1, 2
      ),
      summary_stats AS (
        SELECT 
          loc,
          COUNT(DISTINCT ym) AS active_months,
          SUM(stock) AS total_stock,
          SUM(sqm) AS total_sqm,
          AVG(stock) AS avg_stock,
          AVG(sqm) AS avg_sqm
        FROM monthly_data
        GROUP BY loc
      )
      SELECT 
        m.loc, 
        m.ym, 
        m.stock, 
        m.sqm,
        m.sku_count,
        s.active_months,
        s.total_stock,
        s.total_sqm,
        s.avg_stock,
        s.avg_sqm
      FROM monthly_data m
      LEFT JOIN summary_stats s ON m.loc = s.loc
      ORDER BY m.loc, m.ym
      LIMIT 10000
    `;
    
    const rows = conn.prepare(sql).all();
    
    // 통계 계산
    const totalStock = rows.reduce((sum, row) => sum + row.stock, 0);
    const totalSqm = rows.reduce((sum, row) => sum + row.sqm, 0);
    const uniqueLocations = new Set(rows.map(row => row.loc)).size;
    const uniqueMonths = new Set(rows.map(row => row.ym)).size;
    
    return NextResponse.json({ 
      rows,
      stats: {
        total_stock: totalStock,
        total_sqm: totalSqm,
        unique_locations: uniqueLocations,
        unique_months: uniqueMonths,
        total_records: rows.length
      }
    });
  } catch (error) {
    console.error("Heatmap API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch heatmap data" },
      { status: 500 }
    );
  }
}
