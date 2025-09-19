import { NextResponse } from "next/server";
import { getConn } from "@/lib/duck-server";

export const runtime = "nodejs";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const sku = searchParams.get("sku") ?? "";
    
    const conn = getConn();
    
    // events 테이블이 있는지 확인하고, 없으면 sku_master에서 시뮬레이션
    let sql: string;
    let params: any[] = [];
    
    try {
      // events 테이블 존재 확인
      conn.prepare("SELECT COUNT(*) FROM events LIMIT 1").all();
      
      sql = `
        SELECT 
          SKU, 
          Status_Location, 
          Flow_Code, 
          ts,
          'event' as source_type
        FROM events
        ${sku ? `WHERE SKU = ?` : ""}
        ORDER BY SKU, ts
        LIMIT 10000
      `;
      if (sku) params = [sku];
      
    } catch (eventsError) {
      // events 테이블이 없으면 sku_master에서 시뮬레이션
      sql = `
        WITH simulated_events AS (
          SELECT 
            SKU,
            Final_Location as Status_Location,
            flow_code as Flow_Code,
            first_seen as ts,
            'simulated' as source_type
          FROM sku_master
          WHERE first_seen IS NOT NULL
          ${sku ? `AND SKU = ?` : ""}
          
          UNION ALL
          
          SELECT 
            SKU,
            Final_Location as Status_Location,
            flow_code as Flow_Code,
            last_seen as ts,
            'simulated' as source_type
          FROM sku_master
          WHERE last_seen IS NOT NULL 
            AND last_seen != first_seen
          ${sku ? `AND SKU = ?` : ""}
        )
        SELECT 
          SKU, 
          Status_Location, 
          Flow_Code, 
          ts,
          source_type
        FROM simulated_events
        ORDER BY SKU, ts
        LIMIT 10000
      `;
      if (sku) params = [sku, sku];
    }
    
    const rows = params.length > 0 ? conn.prepare(sql).all(...params) : conn.prepare(sql).all();
    
    // SKU별 그룹화 및 통계
    const groupedBySku = rows.reduce((acc, row) => {
      if (!acc[row.SKU]) {
        acc[row.SKU] = [];
      }
      acc[row.SKU].push(row);
      return acc;
    }, {} as Record<string, any[]>);
    
    // 각 SKU별로 시간순 정렬
    Object.keys(groupedBySku).forEach(skuKey => {
      groupedBySku[skuKey].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());
    });
    
    const stats = {
      total_events: rows.length,
      unique_skus: Object.keys(groupedBySku).length,
      completed_flows: Object.values(groupedBySku).filter(flows => 
        flows.some(f => f.Flow_Code === 4)
      ).length,
      avg_events_per_sku: Object.keys(groupedBySku).length > 0 
        ? rows.length / Object.keys(groupedBySku).length 
        : 0
    };
    
    return NextResponse.json({ 
      sku,
      rows,
      grouped_by_sku: groupedBySku,
      stats
    });
  } catch (error) {
    console.error("Case Flow API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch case flow data" },
      { status: 500 }
    );
  }
}
