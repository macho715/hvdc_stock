/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typescript: {
    ignoreBuildErrors: true,
  },
  output: 'standalone',
  experimental: {
    serverComponentsExternalPackages: ['duckdb']
  },
  webpack: (config, { isServer }) => {
    if (isServer) {
      // 서버 사이드에서만 DuckDB 사용
      config.externals = config.externals || [];
      config.externals.push({
        'duckdb': 'commonjs duckdb'
      });
    } else {
      // 클라이언트 사이드에서는 DuckDB 제외
      config.resolve.fallback = {
        ...config.resolve.fallback,
        'duckdb': false,
        'fs': false,
        'path': false,
        'os': false
      };
    }
    
    // 네이티브 모듈 관련 파일들 제외
    config.module.rules.push({
      test: /\.(html|cs|js)$/,
      include: /node_modules\/(@mapbox|node-gyp)/,
      use: 'ignore-loader'
    });
    
    return config;
  }
};

export default nextConfig;
