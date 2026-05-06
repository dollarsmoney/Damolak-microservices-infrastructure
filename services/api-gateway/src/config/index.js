/**
 * API Gateway Configuration
 * Centralized config with service registry for downstream routing.
 */

const config = {
  port: parseInt(process.env.PORT, 10) || 3000,
  nodeEnv: process.env.NODE_ENV || 'development',
  logLevel: process.env.LOG_LEVEL || 'info',
  appName: 'damolak-api-gateway',
  appVersion: '1.0.0',

  // ── Downstream Service URLs ────────────────────────
  // In ECS, these resolve via CloudMap service discovery or
  // hardcoded internal ALB/task IPs. Locally, docker-compose
  // DNS handles resolution.
  services: {
    auth: process.env.AUTH_SERVICE_URL || 'http://auth-service:8080',
    data: process.env.DATA_SERVICE_URL || 'http://data-service:8000',
    processing: process.env.PROCESSING_SERVICE_URL || 'http://processing-service:8081',
    notification: process.env.NOTIFICATION_SERVICE_URL || 'http://notification-service:5000',
  },

  // Rate Limiting
  rateLimitWindowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS, 10) || 15 * 60 * 1000,
  rateLimitMax: parseInt(process.env.RATE_LIMIT_MAX, 10) || 200,
};

module.exports = config;
