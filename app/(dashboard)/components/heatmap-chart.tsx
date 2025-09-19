"use client";
import { getMode } from "../hooks/use-config";
import { useDuck } from "../hooks/use-duck";
import { useHeatmap } from "../hooks/use-api";
import { useEffect, useState } from "react";

interface HeatmapData {
  loc: string;
  ym: string;
  stock: number;
  sqm: number;
}

export default function HeatmapChart() {
  const mode = getMode();
  const { conn, loading: duckLoading, error: duckError } = useDuck();
  const { data: apiData, error: apiError } = mode === "B" ? useHeatmap() : { data: null, error: null };
  const [localData, setLocalData] = useState<HeatmapData[]>([]);

  useEffect(() => {
    (async () => {
      if (!conn || mode !== "A") return;
      
      try {
        const result = await conn.query(`
          WITH monthly_data AS (
            SELECT 
              COALESCE(Final_Location, 'Unknown') AS loc,
              strftime(first_seen, '%Y-%m-01') AS ym,
              SUM(COALESCE(stock_qty, 0)) AS stock,
              SUM(COALESCE(sku_sqm, 0)) AS sqm
            FROM sku_master
            WHERE first_seen IS NOT NULL
            GROUP BY 1, 2
          )
          SELECT loc, ym, stock, sqm
          FROM monthly_data
          ORDER BY loc, ym
        `);
        
        setLocalData(result.toArray() as HeatmapData[]);
      } catch (err) {
        console.error("Failed to fetch heatmap data:", err);
      }
    })();
  }, [conn, mode]);

  const data = mode === "A" ? localData : (apiData?.rows || []);
  const loading = mode === "A" ? duckLoading : !apiData && !apiError;
  const error = mode === "A" ? duckError : apiError;

  // 데이터 전처리
  const locations = [...new Set(data.map(d => d.loc))].sort();
  const months = [...new Set(data.map(d => d.ym))].sort();
  
  const maxStock = Math.max(...data.map(d => d.stock), 1);
  const maxSqm = Math.max(...data.map(d => d.sqm), 1);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-gray-300 rounded w-64 animate-pulse"></div>
        <div className="grid grid-cols-12 gap-2">
          {[...Array(60)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-300 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <h3 className="text-red-800 font-medium">히트맵 데이터 오류</h3>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : "데이터를 로드할 수 없습니다."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">재고 위치별 월별 히트맵</h3>
          <p className="text-sm text-gray-600">Stock Quantity (상단) / SQM (하단)</p>
        </div>
        <div className="text-sm text-gray-500">
          {locations.length}개 위치 × {months.length}개월
        </div>
      </div>

      {/* 범례 */}
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-600">낮음</span>
          <div className="flex gap-1">
            {[0, 0.25, 0.5, 0.75, 1].map(intensity => (
              <div
                key={intensity}
                className="w-4 h-4 rounded"
                style={{
                  backgroundColor: `rgba(59, 130, 246, ${intensity})`
                }}
              ></div>
            ))}
          </div>
          <span className="text-gray-600">높음</span>
        </div>
        <div className="text-gray-500">
          최대값: Stock {maxStock.toLocaleString()}, SQM {maxSqm.toLocaleString()}
        </div>
      </div>

      {/* 히트맵 테이블 */}
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          <table className="min-w-full">
            <thead>
              <tr>
                <th className="px-4 py-2 text-left text-sm font-medium text-gray-700 bg-gray-50 border">
                  위치
                </th>
                {months.map(month => (
                  <th key={month} className="px-2 py-2 text-center text-xs text-gray-600 bg-gray-50 border">
                    {month.slice(5)}월
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {locations.map(location => (
                <tr key={location}>
                  <td className="px-4 py-2 text-sm font-medium text-gray-900 bg-gray-50 border">
                    {location}
                  </td>
                  {months.map(month => {
                    const cellData = data.find(d => d.loc === location && d.ym === month);
                    const stockIntensity = cellData ? cellData.stock / maxStock : 0;
                    const sqmIntensity = cellData ? cellData.sqm / maxSqm : 0;
                    
                    return (
                      <td key={`${location}-${month}`} className="border">
                        <div className="flex flex-col">
                          {/* Stock */}
                          <div 
                            className="h-6 flex items-center justify-center text-xs font-medium"
                            style={{
                              backgroundColor: `rgba(59, 130, 246, ${stockIntensity})`,
                              color: stockIntensity > 0.5 ? 'white' : 'black'
                            }}
                          >
                            {cellData?.stock ? cellData.stock.toLocaleString() : '-'}
                          </div>
                          {/* SQM */}
                          <div 
                            className="h-6 flex items-center justify-center text-xs font-medium"
                            style={{
                              backgroundColor: `rgba(34, 197, 94, ${sqmIntensity})`,
                              color: sqmIntensity > 0.5 ? 'white' : 'black'
                            }}
                          >
                            {cellData?.sqm ? cellData.sqm.toFixed(0) : '-'}
                          </div>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 요약 통계 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-sm text-blue-600">총 재고량</div>
          <div className="text-2xl font-bold text-blue-900">
            {data.reduce((sum, d) => sum + d.stock, 0).toLocaleString()}
          </div>
        </div>
        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
          <div className="text-sm text-green-600">총 면적</div>
          <div className="text-2xl font-bold text-green-900">
            {data.reduce((sum, d) => sum + d.sqm, 0).toFixed(0)} m²
          </div>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-600">활성 위치</div>
          <div className="text-2xl font-bold text-gray-900">
            {locations.length}개
          </div>
        </div>
      </div>
    </div>
  );
}
