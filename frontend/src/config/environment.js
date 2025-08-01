/**
 * Environment-aware configuration
 * Automatically detects environment and uses correct backend URLs
 */

// Environment detection
const isProduction = process.env.NODE_ENV === 'production';
const isDevelopment = process.env.NODE_ENV === 'development';

// Server configuration based on environment
const ENVIRONMENTS = {
  development: {
    // Development environment - external IP for remote access
    BACKEND_URL: 'http://65.108.32.143:8000',
    API_BASE_URL: 'http://65.108.32.143:8000/api',
    WS_URL: 'ws://65.108.32.143:8000/ws',
    FRONTEND_URL: 'http://65.108.32.143:3000'
  },
  production: {
    // Production environment - relative URLs for same-server deployment
    BACKEND_URL: '', // Same server
    API_BASE_URL: '/api', // Relative path
    WS_URL: `ws://${window?.location?.host || 'localhost'}/ws`,
    FRONTEND_URL: window?.location?.origin || 'https://review.halbzeit.ai'
  }
};

// Get current environment config
const getCurrentEnvironment = () => {
  if (isProduction) return 'production';
  if (isDevelopment) return 'development';
  return 'development'; // fallback
};

const currentEnv = getCurrentEnvironment();
const config = ENVIRONMENTS[currentEnv];

// Export configuration
export const API_CONFIG = {
  // Primary API base URL (used by axios instances)
  BASE_URL: config.API_BASE_URL,
  
  // Individual service URLs
  BACKEND_URL: config.BACKEND_URL,
  FRONTEND_URL: config.FRONTEND_URL,
  WS_URL: config.WS_URL,
  
  // Environment info
  ENVIRONMENT: currentEnv,
  IS_PRODUCTION: isProduction,
  IS_DEVELOPMENT: isDevelopment,
  
  // Request configuration
  TIMEOUT: isProduction ? 30000 : 10000, // 30s prod, 10s dev
  RETRY_ATTEMPTS: isProduction ? 3 : 1,
};

// Debug logging in development
if (isDevelopment) {
  console.log('🔧 Frontend Environment Configuration:');
  console.log(`   Environment: ${currentEnv}`);
  console.log(`   API Base URL: ${API_CONFIG.BASE_URL}`);
  console.log(`   Backend URL: ${API_CONFIG.BACKEND_URL}`);
  console.log(`   Frontend URL: ${API_CONFIG.FRONTEND_URL}`);
}

export default API_CONFIG;