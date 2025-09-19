#!/usr/bin/env node

import fs from "node:fs";
import https from "node:https";
import http from "node:http";
import { URL } from "node:url";

const url = process.env.DUCKDB_DOWNLOAD_URL;

if (!url) {
  console.log("ℹ️  No DUCKDB_DOWNLOAD_URL provided. Skipping DuckDB download.");
  process.exit(0);
}

console.log("🔄 Downloading DuckDB file from:", url);

try {
  // Ensure output directory exists
  fs.mkdirSync("out_recon", { recursive: true });
  
  const file = fs.createWriteStream("out_recon/sku_master_v2.duckdb");
  const parsedUrl = new URL(url);
  const client = parsedUrl.protocol === 'https:' ? https : http;
  
  const request = client.get(url, (response) => {
    if (response.statusCode !== 200) {
      console.error(`❌ Failed to download DuckDB file. Status: ${response.statusCode}`);
      process.exit(1);
    }
    
    const totalSize = parseInt(response.headers['content-length'], 10);
    let downloadedSize = 0;
    
    response.on('data', (chunk) => {
      downloadedSize += chunk.length;
      if (totalSize > 0) {
        const progress = ((downloadedSize / totalSize) * 100).toFixed(1);
        process.stdout.write(`\r📥 Downloading: ${progress}% (${downloadedSize}/${totalSize} bytes)`);
      }
    });
    
    response.pipe(file);
    
    file.on('finish', () => {
      file.close();
      console.log(`\n✅ DuckDB file downloaded successfully!`);
      console.log(`📁 File size: ${(downloadedSize / 1024 / 1024).toFixed(2)} MB`);
      console.log(`📍 Location: out_recon/sku_master_v2.duckdb`);
    });
    
    file.on('error', (err) => {
      fs.unlink("out_recon/sku_master_v2.duckdb", () => {}); // Delete partial file
      console.error(`❌ Error writing DuckDB file:`, err.message);
      process.exit(1);
    });
  });
  
  request.on('error', (err) => {
    console.error(`❌ Error downloading DuckDB file:`, err.message);
    process.exit(1);
  });
  
  request.setTimeout(60000, () => {
    request.destroy();
    console.error(`❌ Download timeout after 60 seconds`);
    process.exit(1);
  });
  
} catch (error) {
  console.error(`❌ Error setting up DuckDB download:`, error.message);
  process.exit(1);
}
