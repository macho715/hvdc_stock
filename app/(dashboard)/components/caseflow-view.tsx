"use client";
import { getMode } from "../hooks/use-config";
import { useDuck } from "../hooks/use-duck";
import { useCaseFlow } from "../hooks/use-api";
import { useEffect, useState } from "react";

interface CaseFlowData {
  SKU: string;
  Status_Location: string;
  Flow_Code: number;
  ts: string;
}

const flowDescriptions = {
  0: "Pre-Arrival (도착 전)",
  1: "Port Arrival (항만 도착)", 
  2: "Warehouse (창고 입고)",
  3: "MOSB (MOSB 경유)",
  4: "Site Delivery (현장 배송)"
};

export default function CaseFlowView() {
  const [selectedSku, setSelectedSku] = useState<string>("");
  const mode = getMode();
  const { conn, loading: duckLoading, error: duckError } = useDuck();
  const { data: apiData, error: apiError } = mode === "B" ? useCaseFlow(selectedSku) : { data: null, error: null };
  const [localData, setLocalData] = useState<CaseFlowData[]>([]);
  const [availableSkus, setAvailableSkus] = useState<string[]>([]);

  useEffect(() => {
    (async () => {
      if (!conn || mode !== "A") return;
      
      try {
        // 사용 가능한 SKU 목록 가져오기
        const skuResult = await conn.query(`
          SELECT DISTINCT SKU FROM sku_master 
          WHERE SKU IS NOT NULL 
          ORDER BY SKU 
          LIMIT 100
        `);
        setAvailableSkus(skuResult.toArray().map(row => row.SKU as string));

        // Case Flow 데이터 가져오기 (events 테이블이 있다면)
        try {
          const flowResult = await conn.query(`
            SELECT SKU, Status_Location, Flow_Code, ts
            FROM events
            ${selectedSku ? `WHERE SKU = '${selectedSku}'` : ''}
            ORDER BY SKU, ts
            LIMIT 1000
          `);
          setLocalData(flowResult.toArray() as CaseFlowData[]);
        } catch (eventsError) {
          // events 테이블이 없으면 sku_master에서 시뮬레이션
          const simulatedResult = await conn.query(`
            SELECT 
              SKU,
              Final_Location as Status_Location,
              flow_code as Flow_Code,
              first_seen as ts
            FROM sku_master
            ${selectedSku ? `WHERE SKU = '${selectedSku}'` : ''}
            AND first_seen IS NOT NULL
            ORDER BY SKU, first_seen
            LIMIT 1000
          `);
          setLocalData(simulatedResult.toArray() as CaseFlowData[]);
        }
      } catch (err) {
        console.error("Failed to fetch case flow data:", err);
      }
    })();
  }, [conn, mode, selectedSku]);

  const data = mode === "A" ? localData : (apiData?.rows || []);
  const loading = mode === "A" ? duckLoading : !apiData && !apiError;
  const error = mode === "A" ? duckError : apiError;

  // SKU별로 그룹화
  const groupedData = data.reduce((acc, item) => {
    if (!acc[item.SKU]) {
      acc[item.SKU] = [];
    }
    acc[item.SKU].push(item);
    return acc;
  }, {} as Record<string, CaseFlowData[]>);

  // 각 SKU별로 시간순 정렬
  Object.keys(groupedData).forEach(sku => {
    groupedData[sku].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());
  });

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-10 bg-gray-300 rounded w-64 animate-pulse"></div>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-300 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <h3 className="text-red-800 font-medium">Case Flow 데이터 오류</h3>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : "데이터를 로드할 수 없습니다."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* SKU 선택 */}
      <div className="p-4 bg-white rounded-lg border">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700 min-w-fit">
            SKU 필터:
          </label>
          <select
            value={selectedSku}
            onChange={(e) => setSelectedSku(e.target.value)}
            className="flex-1 max-w-xs px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">전체 SKU</option>
            {availableSkus.map(sku => (
              <option key={sku} value={sku}>{sku}</option>
            ))}
          </select>
          <div className="text-sm text-gray-500">
            {Object.keys(groupedData).length}개 SKU 표시
          </div>
        </div>
      </div>

      {/* Flow 코드 범례 */}
      <div className="p-4 bg-gray-50 rounded-lg border">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Flow Code 범례</h4>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          {Object.entries(flowDescriptions).map(([code, desc]) => (
            <div key={code} className="flex items-center gap-2 text-xs">
              <div className={`w-3 h-3 rounded-full ${
                code === '0' ? 'bg-gray-400' :
                code === '1' ? 'bg-blue-400' :
                code === '2' ? 'bg-green-400' :
                code === '3' ? 'bg-yellow-400' :
                'bg-red-400'
              }`}></div>
              <span className="text-gray-700">
                {code}: {desc}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Case Flow 타임라인 */}
      <div className="space-y-4">
        {Object.entries(groupedData).slice(0, 20).map(([sku, flows]) => (
          <div key={sku} className="p-4 bg-white rounded-lg border">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-mono text-sm font-medium text-gray-900">{sku}</h4>
              <span className="text-xs text-gray-500">
                {flows.length}개 이벤트
              </span>
            </div>
            
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              {flows.map((flow, index) => (
                <div key={index} className="flex items-center">
                  {/* Flow 노드 */}
                  <div className="flex flex-col items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                      flow.Flow_Code === 0 ? 'bg-gray-500' :
                      flow.Flow_Code === 1 ? 'bg-blue-500' :
                      flow.Flow_Code === 2 ? 'bg-green-500' :
                      flow.Flow_Code === 3 ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}>
                      {flow.Flow_Code}
                    </div>
                    <div className="text-xs text-gray-600 mt-1 max-w-20 text-center">
                      {flow.Status_Location || 'N/A'}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {new Date(flow.ts).toLocaleDateString()}
                    </div>
                  </div>
                  
                  {/* 화살표 (마지막이 아닌 경우) */}
                  {index < flows.length - 1 && (
                    <div className="mx-2 text-gray-400">
                      →
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* 요약 통계 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-sm text-blue-600">총 이벤트</div>
          <div className="text-2xl font-bold text-blue-900">{data.length}</div>
        </div>
        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
          <div className="text-sm text-green-600">고유 SKU</div>
          <div className="text-2xl font-bold text-green-900">
            {Object.keys(groupedData).length}
          </div>
        </div>
        <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
          <div className="text-sm text-yellow-600">평균 이벤트/SKU</div>
          <div className="text-2xl font-bold text-yellow-900">
            {Object.keys(groupedData).length > 0 
              ? (data.length / Object.keys(groupedData).length).toFixed(1)
              : '0'
            }
          </div>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-600">완료된 Flow</div>
          <div className="text-2xl font-bold text-gray-900">
            {Object.values(groupedData).filter(flows => 
              flows.some(f => f.Flow_Code === 4)
            ).length}
          </div>
        </div>
      </div>

      {Object.keys(groupedData).length > 20 && (
        <div className="text-center text-sm text-gray-500">
          상위 20개 SKU만 표시됩니다. 전체 {Object.keys(groupedData).length}개 중
        </div>
      )}
    </div>
  );
}
