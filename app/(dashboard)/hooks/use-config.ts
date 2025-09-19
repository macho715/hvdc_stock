export function getMode(): "A" | "B" {
  const m = process.env.NEXT_PUBLIC_MODE?.toUpperCase() === "A" ? "A" : "B";
  return m as "A" | "B";
}

export function getConfig() {
  const mode = getMode();
  
  if (mode === "A") {
    return {
      mode: "A" as const,
      parquetUrls: {
        sku: process.env.NEXT_PUBLIC_PARQUET_URL_SKU || "",
        events: process.env.NEXT_PUBLIC_PARQUET_URL_EVENTS || "",
        exceptions: process.env.NEXT_PUBLIC_PARQUET_URL_EXCEPTIONS || "",
      }
    };
  } else {
    return {
      mode: "B" as const,
      apiBase: "/api",
      defaultTolerance: parseInt(process.env.DEFAULT_TOLERANCE_PCT || "10")
    };
  }
}
