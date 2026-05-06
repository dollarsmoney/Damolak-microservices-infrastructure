/**
 * API Gateway Entry Point — ECS-aware graceful lifecycle.
 */

const createApp = require('./app');
const config = require('./config');
const logger = require('./utils/logger');

const app = createApp();

const server = app.listen(config.port, '0.0.0.0', () => {
  logger.info('API Gateway started', {
    port: config.port,
    environment: config.nodeEnv,
    services: Object.keys(config.services),
  });
});

// ─── Graceful Shutdown (ECS SIGTERM) ─────────────────
const SHUTDOWN_TIMEOUT = 15000;

async function shutdown(signal) {
  logger.info(`${signal} received. Draining connections...`);
  const timer = setTimeout(() => process.exit(1), SHUTDOWN_TIMEOUT);

  server.close(() => {
    clearTimeout(timer);
    logger.info('Gateway shutdown complete.');
    process.exit(0);
  });
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('uncaughtException', (err) => {
  logger.error('Uncaught exception', { error: err.message, stack: err.stack });
  process.exit(1);
});
process.on('unhandledRejection', (reason) => {
  logger.error('Unhandled rejection', { reason: String(reason) });
  process.exit(1);
});

module.exports = server;
