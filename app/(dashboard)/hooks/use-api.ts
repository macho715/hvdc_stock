"use client";
import useSWR from "swr";

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useKpi() {
  return useSWR("/api/kpi", fetcher);
}

export function useThreeWay(tol: number) {
  return useSWR(`/api/3way?tol=${tol}`, fetcher);
}

export function useHeatmap() {
  return useSWR("/api/heatmap", fetcher);
}

export function useCaseFlow(sku?: string) {
  return useSWR(
    sku ? `/api/caseflow?sku=${encodeURIComponent(sku)}` : "/api/caseflow", 
    fetcher
  );
}
