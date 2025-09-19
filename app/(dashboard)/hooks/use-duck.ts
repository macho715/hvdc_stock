"use client";
import { useEffect, useRef, useState } from "react";
import * as duckdb from "@duckdb/duckdb-wasm";

export function useDuck() {
  const [conn, setConn] = useState<duckdb.AsyncDuckDBConnection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const dbRef = useRef<duckdb.AsyncDuckDB | null>(null);

  useEffect(() => {
    (async () => {
      if (dbRef.current) return;
      
      try {
        setLoading(true);
        setError(null);
        
        const bundles = duckdb.getJsDelivrBundles();
        const worker = new Worker(bundles.mainWorker!, { type: "module" });
        const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
        await db.instantiate(bundles.mainModule, bundles.pthreadWorker);
        const c = await db.connect();

        // 환경 변수에서 Parquet URL 가져오기
        const skuUrl = process.env.NEXT_PUBLIC_PARQUET_URL_SKU;
        const eventsUrl = process.env.NEXT_PUBLIC_PARQUET_URL_EVENTS;
        const exceptionsUrl = process.env.NEXT_PUBLIC_PARQUET_URL_EXCEPTIONS;

        if (skuUrl) {
          await c.query(`CREATE VIEW sku_master AS SELECT * FROM read_parquet('${skuUrl}')`);
        }
        if (eventsUrl) {
          await c.query(`CREATE VIEW events AS SELECT * FROM read_parquet('${eventsUrl}')`);
        }
        if (exceptionsUrl) {
          await c.query(`CREATE VIEW exceptions AS SELECT * FROM read_parquet('${exceptionsUrl}')`);
        }

        dbRef.current = db;
        setConn(c);
        setLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to initialize DuckDB");
        setLoading(false);
      }
    })();
  }, []);

  return { conn, loading, error };
}
