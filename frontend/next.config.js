/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',
  
  // Disable source maps in production (optional)
  productionBrowserSourceMaps: false,
  
  // Configure API rewrites if needed
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
  
  // Image optimization config
  images: {
    domains: ['localhost'],
    unoptimized: true,
  },
};

module.exports = nextConfig;