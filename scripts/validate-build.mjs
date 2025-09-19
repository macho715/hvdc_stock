#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

console.log("🔍 Validating build artifacts...");

const requiredFiles = [
  ".next/static",
  ".next/server",
  ".next/BUILD_ID"
];

const optionalFiles = [
  "out_recon/sku_master_v2.duckdb",
  "out_recon/SKU_MASTER_v2.parquet"
];

let hasErrors = false;

// Check required files
for (const file of requiredFiles) {
  if (!fs.existsSync(file)) {
    console.error(`❌ Required file missing: ${file}`);
    hasErrors = true;
  } else {
    console.log(`✅ Found: ${file}`);
  }
}

// Check optional files
for (const file of optionalFiles) {
  if (fs.existsSync(file)) {
    const stats = fs.statSync(file);
    const sizeKB = (stats.size / 1024).toFixed(2);
    console.log(`✅ Found: ${file} (${sizeKB} KB)`);
  } else {
    console.log(`⚠️  Optional file missing: ${file}`);
  }
}

// Check build size
const nextDir = ".next";
if (fs.existsSync(nextDir)) {
  const getDirSize = (dir) => {
    let size = 0;
    const files = fs.readdirSync(dir);
    for (const file of files) {
      const filePath = path.join(dir, file);
      const stats = fs.statSync(filePath);
      if (stats.isDirectory()) {
        size += getDirSize(filePath);
      } else {
        size += stats.size;
      }
    }
    return size;
  };
  
  const buildSize = getDirSize(nextDir);
  const buildSizeMB = (buildSize / 1024 / 1024).toFixed(2);
  console.log(`📊 Build size: ${buildSizeMB} MB`);
  
  if (buildSize > 50 * 1024 * 1024) { // 50MB
    console.warn(`⚠️  Build size is large (${buildSizeMB} MB). Consider optimization.`);
  }
}

if (hasErrors) {
  console.error("❌ Build validation failed!");
  process.exit(1);
} else {
  console.log("✅ Build validation passed!");
  process.exit(0);
}
