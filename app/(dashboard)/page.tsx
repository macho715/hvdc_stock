"use client";
import { useState, useEffect } from "react";

export const dynamic = "force-dynamic";
import { ErrorBoundary, AsyncErrorBoundary } from "./components/error-boundary";
import { LoadingSpinner } from "./components/ui/loading-spinner";
import { formatDate } from "@/lib/utils";
import KpiCards from "./components/kpi-cards";
import ThreeWayTable from "./components/threeway-table";
import HeatmapChart from "./components/heatmap-chart";
import CaseFlowView from "./components/caseflow-view";
import ExceptionsTable from "./components/exceptions-table";

const tabs = [
  { key: "overview", label: "Overview", icon: "📊" },
  { key: "threeway", label: "3-Way Reconciliation", icon: "🔄" },
  { key: "heatmap", label: "Inventory Heatmap", icon: "🗺️" },
  { key: "caseflow", label: "Case Flow", icon: "📋" },
  { key: "exceptions", label: "Exceptions & Audit", icon: "⚠️" }
];

export default function DashboardPage() {
  const [active, setActive] = useState("overview");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate initial loading
    const timer = setTimeout(() => {
      setIsLoading(false);
      setLastUpdated(new Date());
    }, 1000);

    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-[1400px] p-6">
        <div className="flex items-center justify-center min-h-[600px]">
          <LoadingSpinner size="lg" text="Loading HVDC Dashboard..." />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1400px] p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
              <span className="text-blue-600">🏭</span>
              HVDC Master Dashboard
            </h1>
            <p className="text-gray-600">
              Tri-Source Reconciliation • 6,791 SKU Records • Real-time Analytics
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Last Updated</div>
            <div className="text-sm font-medium text-gray-900">
              {lastUpdated ? formatDate(lastUpdated) : 'Never'}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="mb-6">
        <div className="flex gap-1 overflow-x-auto border-b">
          {tabs.map(t => (
            <button 
              key={t.key}
              onClick={() => setActive(t.key)}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-all duration-200 ${
                active === t.key 
                  ? "border-blue-600 text-blue-600 bg-blue-50" 
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <span className="text-base">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content Area */}
      <ErrorBoundary>
        <AsyncErrorBoundary>
          <div className="min-h-[600px]">
            {active === "overview" && <KpiCards />}
            {active === "threeway" && <ThreeWayTable />}
            {active === "heatmap" && <HeatmapChart />}
            {active === "caseflow" && <CaseFlowView />}
            {active === "exceptions" && <ExceptionsTable />}
          </div>
        </AsyncErrorBoundary>
      </ErrorBoundary>

      {/* Footer */}
      <div className="mt-8 pt-6 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center gap-4">
            <span>HVDC SKU Master Hub v2.0</span>
            <span>•</span>
            <span>Data Source: Tri-Source Reconciliation</span>
            <span>•</span>
            <span>Mode: {process.env.NEXT_PUBLIC_MODE || 'B'}</span>
          </div>
          <div>
            <span>© 2025 Samsung C&T Logistics</span>
          </div>
        </div>
      </div>
    </div>
  );
}
