"use client";
import { getMode } from "../hooks/use-config";
import { useDuck } from "../hooks/use-duck";
import { useEffect, useState } from "react";

interface ExceptionData {
  SKU: string;
  hvdc_code_norm: string;
  Invoice_RAW_CODE: string;
  Err_GW: number;
  Err_CBM: number;
  Match_Status: string;
  GW_SumPicked: number;
  CBM_SumPicked: number;
}

export default function ExceptionsTable() {
  const mode = getMode();
  const { conn, loading: duckLoading, error: duckError } = useDuck();
  const [localData, setLocalData] = useState<ExceptionData[]>([]);
  const [filter, setFilter] = useState<"all" | "fail" | "pass">("all");

  useEffect(() => {
    (async () => {
      if (!conn || mode !== "A") return;
      
      try {
        // exceptions 테이블이 있는지 확인
        try {
          const result = await conn.query(`
            SELECT 
              e.SKU,
              e.hvdc_code_norm,
              e.Invoice_RAW_CODE,
              COALESCE(e.Err_GW, 0) as Err_GW,
              COALESCE(e.Err_CBM, 0) as Err_CBM,
              COALESCE(e.Match_Status, 'UNKNOWN') as Match_Status,
              COALESCE(e.GW_SumPicked, 0) as GW_SumPicked,
              COALESCE(e.CBM_SumPicked, 0) as CBM_SumPicked
            FROM exceptions e
            ORDER BY ABS(COALESCE(e.Err_GW, 0)) DESC, ABS(COALESCE(e.Err_CBM, 0)) DESC
            LIMIT 1000
          `);
          setLocalData(result.toArray() as ExceptionData[]);
        } catch (exceptionsError) {
          // exceptions 테이블이 없으면 sku_master에서 예외 케이스 추출
          const result = await conn.query(`
            SELECT 
              s.SKU,
              s.hvdc_code_norm,
              s.SKU as Invoice_RAW_CODE,
              COALESCE(s.err_gw, 0) as Err_GW,
              COALESCE(s.err_cbm, 0) as Err_CBM,
              COALESCE(s.inv_match_status, 'UNKNOWN') as Match_Status,
              COALESCE(s.GW, 0) as GW_SumPicked,
              COALESCE(s.CBM, 0) as CBM_SumPicked
            FROM sku_master s
            WHERE s.inv_match_status != 'PASS' OR s.inv_match_status IS NULL
            ORDER BY ABS(COALESCE(s.err_gw, 0)) DESC, ABS(COALESCE(s.err_cbm, 0)) DESC
            LIMIT 1000
          `);
          setLocalData(result.toArray() as ExceptionData[]);
        }
      } catch (err) {
        console.error("Failed to fetch exceptions data:", err);
      }
    })();
  }, [conn, mode]);

  const loading = mode === "A" ? duckLoading : false;
  const error = mode === "A" ? duckError : null;

  // 필터링
  const filteredData = localData.filter(item => {
    if (filter === "fail") return item.Match_Status !== "PASS";
    if (filter === "pass") return item.Match_Status === "PASS";
    return true;
  });

  // 통계 계산
  const totalExceptions = localData.length;
  const failExceptions = localData.filter(d => d.Match_Status !== "PASS").length;
  const passExceptions = localData.filter(d => d.Match_Status === "PASS").length;
  const avgGwError = localData.length > 0 
    ? localData.reduce((sum, d) => sum + Math.abs(d.Err_GW), 0) / localData.length 
    : 0;
  const avgCbmError = localData.length > 0 
    ? localData.reduce((sum, d) => sum + Math.abs(d.Err_CBM), 0) / localData.length 
    : 0;

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-gray-300 rounded w-48 animate-pulse"></div>
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-300 rounded animate-pulse"></div>
          ))}
        </div>
        <div className="space-y-3">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-300 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <h3 className="text-red-800 font-medium">예외 데이터 오류</h3>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : "데이터를 로드할 수 없습니다."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 제목 및 설명 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900">예외 처리 및 감사 테이블</h3>
        <p className="text-sm text-gray-600 mt-1">
          Invoice 매칭 실패 및 오차 분석 - 재검토가 필요한 SKU 목록
        </p>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-sm text-blue-600">총 예외 건수</div>
          <div className="text-2xl font-bold text-blue-900">{totalExceptions.toLocaleString()}</div>
        </div>
        <div className="p-4 bg-red-50 rounded-lg border border-red-200">
          <div className="text-sm text-red-600">실패 케이스</div>
          <div className="text-2xl font-bold text-red-900">{failExceptions.toLocaleString()}</div>
        </div>
        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
          <div className="text-sm text-green-600">통과 케이스</div>
          <div className="text-2xl font-bold text-green-900">{passExceptions.toLocaleString()}</div>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-600">평균 오차</div>
          <div className="text-lg font-bold text-gray-900">
            GW: {avgGwError.toFixed(2)}kg<br/>
            CBM: {avgCbmError.toFixed(3)}m³
          </div>
        </div>
      </div>

      {/* 필터 */}
      <div className="flex items-center gap-4 p-4 bg-white rounded-lg border">
        <label className="text-sm font-medium text-gray-700">필터:</label>
        <div className="flex gap-2">
          {[
            { key: "all", label: "전체", count: totalExceptions },
            { key: "fail", label: "실패", count: failExceptions },
            { key: "pass", label: "통과", count: passExceptions }
          ].map(option => (
            <button
              key={option.key}
              onClick={() => setFilter(option.key as any)}
              className={`px-3 py-1 text-sm rounded-full transition-colors ${
                filter === option.key
                  ? "bg-blue-100 text-blue-800 border border-blue-300"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {option.label} ({option.count})
            </button>
          ))}
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
                  HVDC Code
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Invoice Code
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  GW 오차
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  CBM 오차
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  GW 수량
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  CBM 수량
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  상태
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredData.slice(0, 100).map((row, index) => (
                <tr 
                  key={index} 
                  className={`hover:bg-gray-50 ${
                    row.Match_Status !== 'PASS' ? 'bg-red-50' : ''
                  }`}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                    {row.SKU}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {row.hvdc_code_norm || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {row.Invoice_RAW_CODE || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                    <span className={`font-medium ${
                      Math.abs(row.Err_GW) > 100 ? 'text-red-600' : 
                      Math.abs(row.Err_GW) > 10 ? 'text-yellow-600' : 'text-green-600'
                    }`}>
                      {row.Err_GW.toFixed(2)} kg
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                    <span className={`font-medium ${
                      Math.abs(row.Err_CBM) > 1 ? 'text-red-600' : 
                      Math.abs(row.Err_CBM) > 0.1 ? 'text-yellow-600' : 'text-green-600'
                    }`}>
                      {row.Err_CBM.toFixed(3)} m³
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    {row.GW_SumPicked.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    {row.CBM_SumPicked.toFixed(3)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      row.Match_Status === 'PASS' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {row.Match_Status || 'UNKNOWN'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {filteredData.length > 100 && (
          <div className="px-6 py-3 bg-gray-50 border-t text-sm text-gray-500 text-center">
            상위 100개 레코드만 표시됩니다. 전체 {filteredData.length.toLocaleString()}개 중
          </div>
        )}
      </div>

      {/* 액션 버튼 */}
      <div className="flex justify-end gap-3">
        <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">
          CSV 내보내기
        </button>
        <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700">
          재검토 요청
        </button>
      </div>
    </div>
  );
}
