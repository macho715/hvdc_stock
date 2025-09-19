"use client";
import { getMode } from "../hooks/use-config";
import { useDuck } from "../hooks/use-duck";
import { useKpi } from "../hooks/use-api";
import { useEffect, useState } from "react";
import { LoadingSpinner, LoadingCard } from "./ui/loading-spinner";
import { formatNumber, formatPercentage, getToleranceColor } from "@/lib/utils";
import { KpiData } from "@/lib/types";


export default function KpiCards() {
  const mode = getMode();
  const { conn, loading: duckLoading, error: duckError } = useDuck();
  const { data: apiData, error: apiError } = mode === "B" ? useKpi() : { data: null, error: null };
  const [localData, setLocalData] = useState<KpiData | null>(null);

  useEffect(() => {
    (async () => {
      if (!conn || mode !== "A") return;
      
      try {
        const result = await conn.query(`
          SELECT 
            COUNT(*)::INT AS total,
            ROUND(COUNT(*) FILTER(WHERE inv_match_status != 'PASS') * 100.0 / NULLIF(COUNT(*), 0), 2) AS mismatch_pct,
            ROUND(COUNT(DISTINCT flow_code) / 5.0 * 100, 2) AS flow_coverage,
            ROUND(COUNT(*) FILTER(WHERE stock_qty IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0), 2) AS stock_coverage,
            ROUND(COUNT(*) FILTER(WHERE sku_sqm IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0), 2) AS sqm_coverage
          FROM sku_master
        `);
        
        if (result && result.length > 0) {
          setLocalData(result[0] as KpiData);
        }
      } catch (err) {
        console.error("Failed to fetch KPI data:", err);
      }
    })();
  }, [conn, mode]);

  const data = mode === "A" ? localData : apiData;
  const loading = mode === "A" ? duckLoading : !apiData && !apiError;
  const error = mode === "A" ? duckError : apiError;

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {[...Array(5)].map((_, i) => (
          <LoadingCard key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <h3 className="text-red-800 font-medium">데이터 로드 오류</h3>
        <p className="text-red-600 text-sm mt-1">
          {error instanceof Error ? error.message : "알 수 없는 오류가 발생했습니다."}
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center">
        <p className="text-gray-600">데이터를 찾을 수 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      <Card 
        title="총 SKU 수" 
        value={formatNumber(data.total)} 
        subtitle="개"
        color="blue"
        trend="up"
        trendValue="+2.3%"
      />
      <Card 
        title="매칭 오류율" 
        value={formatPercentage(data.mismatch_pct || 0)} 
        subtitle="Invoice vs Stock"
        color={data.mismatch_pct > 10 ? "red" : "green"}
        trend={data.mismatch_pct > 10 ? "up" : "down"}
        trendValue={data.mismatch_pct > 10 ? "+1.2%" : "-0.5%"}
      />
      <Card 
        title="Flow 커버리지" 
        value={formatPercentage(data.flow_coverage || 0)} 
        subtitle="5개 코드 중"
        color="blue"
        trend="stable"
        trendValue="0%"
      />
      <Card 
        title="재고 데이터 커버리지" 
        value={formatPercentage(data.stock_coverage || 0)} 
        subtitle="Stock Quantity"
        color="orange"
        trend="up"
        trendValue="+5.1%"
      />
      <Card 
        title="면적 데이터 커버리지" 
        value={formatPercentage(data.sqm_coverage || 0)} 
        subtitle="SQM Coverage"
        color="green"
        trend="stable"
        trendValue="0%"
      />
    </div>
  );
}

function Card({ 
  title, 
  value, 
  subtitle, 
  color = "gray",
  trend,
  trendValue
}: { 
  title: string; 
  value: string; 
  subtitle?: string;
  color?: "blue" | "green" | "red" | "orange" | "gray";
  trend?: "up" | "down" | "stable";
  trendValue?: string;
}) {
  const colorClasses = {
    blue: "border-blue-200 bg-blue-50",
    green: "border-green-200 bg-green-50", 
    red: "border-red-200 bg-red-50",
    orange: "border-orange-200 bg-orange-50",
    gray: "border-gray-200 bg-gray-50"
  };

  const trendColors = {
    up: "text-green-600",
    down: "text-red-600",
    stable: "text-gray-600"
  };

  const trendIcons = {
    up: "↗️",
    down: "↘️", 
    stable: "➡️"
  };

  return (
    <div className={`rounded-xl border p-6 shadow-sm transition-all duration-200 hover:shadow-md ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-medium text-gray-600">{title}</div>
        {trend && trendValue && (
          <div className={`flex items-center gap-1 text-xs ${trendColors[trend]}`}>
            <span>{trendIcons[trend]}</span>
            <span>{trendValue}</span>
          </div>
        )}
      </div>
      <div className="mt-2 text-3xl font-bold text-gray-900">{value}</div>
      {subtitle && (
        <div className="mt-1 text-xs text-gray-500">{subtitle}</div>
      )}
    </div>
  );
}
