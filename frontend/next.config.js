/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    appDir: true,
  },
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8080/api/:path*', // Proxy to Backend
      },
      {
        source: '/ws/:path*',
        destination: 'http://localhost:8080/ws/:path*', // Proxy WebSocket
      },
    ]
  },
}

module.exports = nextConfig