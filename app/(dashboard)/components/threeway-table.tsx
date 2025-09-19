"use client";
import { getMode } from "../hooks/use-config";
import { useDuck } from "../hooks/use-duck";
import { useThreeWay } from "../hooks/use-api";
import { useEffect, useState } from "react";

interface ThreeWayData {
  SKU: string;
  inv_match_status: string;
  stock_qty: number;
  err_gw: number;
  err_cbm: number;
  verdict: string;
}

export default function ThreeWayTable() {
  const [tolerance, setTolerance] = useState(10);
  const mode = getMode();
  const { conn, loading: duckLoading, error: duckError } = useDuck();
  const { data: apiData, error: apiError } = mode === "B" ? useThreeWay(tolerance) : { data: null, error: null };
  const [localData, setLocalData] = useState<ThreeWayData[]>([]);

  useEffect(() => {
    (async () => {
      if (!conn || mode !== "A") return;
      
      try {
        const result = await conn.query(`
          WITH base AS (
            SELECT 
              s.SKU, 
              s.inv_match_status, 
              s.stock_qty,
              COALESCE(e.err_gw, 0) AS err_gw, 
              COALESCE(e.err_cbm, 0) AS err_cbm
            FROM sku_master s
            LEFT JOIN exceptions e ON s.SKU = e.SKU
          )
          SELECT 
            SKU, 
            inv_match_status, 
            stock_qty, 
            err_gw, 
            err_cbm,
            CASE 
              WHEN inv_match_status != 'PASS' THEN 'FAIL' 
              ELSE 'PASS' 
            END AS verdict
          FROM base
          ORDER BY err_gw DESC, err_cbm DESC
          LIMIT 1000
        `);
        
        setLocalData(result.toArray() as ThreeWayData[]);
      } catch (err) {
        console.error("Failed to fetch three-way data:", err);
      }
    })();
  }, [conn, mode, tolerance]);

  const data = mode === "A" ? localData : (apiData?.rows || []);
  const loading = mode === "A" ? duckLoading : !apiData && !apiError;
  const error = mode === "A" ? duckError : apiError;

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="h-4 bg-gray-300 rounded w-32 animate-pulse"></div>
          <div className="h-6 bg-gray-300 rounded w-48 animate-pulse"></div>
        </div>
        <div className="rounded-xl border bg-white">
          <div className="p-4 space-y-3">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-300 rounded animate-pulse"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <h3 className="text-red-800 font-medium">3-Way Reconciliation 오류</h3>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : "데이터를 로드할 수 없습니다."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 톨러런스 슬라이더 */}
      <div className="flex items-center gap-4 p-4 bg-white rounded-lg border">
        <label className="text-sm font-medium text-gray-700 min-w-fit">
          허용 오차 (Tolerance):
        </label>
        <div className="flex items-center gap-3 flex-1">
          <span className="text-sm text-gray-500">0%</span>
          <input
            type="range"
            min={0}
            max={50}
            value={tolerance}
            onChange={(e) => setTolerance(Number(e.target.value))}
            className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <span className="text-sm text-gray-500">50%</span>
        </div>
        <div className="min-w-[60px] text-center">
          <span className="text-lg font-semibold text-gray-900">
            {tolerance}%
          </span>
        </div>
      </div>

      {/* 통계 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-white rounded-lg border">
          <div className="text-sm text-gray-600">총 레코드</div>
          <div className="text-2xl font-bold text-gray-900">{data.length.toLocaleString()}</div>
        </div>
        <div className="p-4 bg-white rounded-lg border">
          <div className="text-sm text-gray-600">FAIL 케이스</div>
          <div className="text-2xl font-bold text-red-600">
            {data.filter(d => d.verdict === 'FAIL').length.toLocaleString()}
          </div>
        </div>
        <div className="p-4 bg-white rounded-lg border">
          <div className="text-sm text-gray-600">PASS 케이스</div>
          <div className="text-2xl font-bold text-green-600">
            {data.filter(d => d.verdict === 'PASS').length.toLocaleString()}
          </div>
        </div>
      </div>

      {/* 데이터 테이블 */}
      <div className="rounded-xl border bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  SKU
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Match Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stock Qty
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  GW Error
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  CBM Error
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Verdict
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.slice(0, 100).map((row, index) => (
                <tr 
                  key={index} 
                  className={`hover:bg-gray-50 ${
                    row.verdict === 'FAIL' ? 'bg-red-50' : ''
                  }`}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                    {row.SKU}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      row.inv_match_status === 'PASS' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {row.inv_match_status || 'N/A'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    {row.stock_qty ? row.stock_qty.toLocaleString() : 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    {row.err_gw ? row.err_gw.toFixed(2) : '0.00'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    {row.err_cbm ? row.err_cbm.toFixed(3) : '0.000'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      row.verdict === 'PASS' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {row.verdict}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {data.length > 100 && (
          <div className="px-6 py-3 bg-gray-50 border-t text-sm text-gray-500 text-center">
            상위 100개 레코드만 표시됩니다. 전체 {data.length.toLocaleString()}개 중
          </div>
        )}
      </div>
    </div>
  );
}
