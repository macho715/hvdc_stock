import duckdb from "duckdb";
import path from "path";

let _db: duckdb.Database | null = null;
let _conn: duckdb.Connection | null = null;

export function getConn(): duckdb.Connection {
  const dbPath = process.env.DUCKDB_PATH || "../out_recon/sku_master_v2.duckdb";
  
  // 절대 경로로 변환
  const absolutePath = path.resolve(dbPath);
  
  if (!_db) {
    try {
      _db = new duckdb.Database(absolutePath);
    } catch (error) {
      console.error("Failed to connect to DuckDB:", error);
      throw new Error(`DuckDB connection failed: ${error}`);
    }
  }
  
  if (!_conn) {
    try {
      _conn = _db.connect();
    } catch (error) {
      console.error("Failed to create DuckDB connection:", error);
      throw new Error(`DuckDB connection creation failed: ${error}`);
    }
  }
  
  return _conn;
}

export function closeConn() {
  if (_conn) {
    _conn.close();
    _conn = null;
  }
  if (_db) {
    _db.close();
    _db = null;
  }
}
