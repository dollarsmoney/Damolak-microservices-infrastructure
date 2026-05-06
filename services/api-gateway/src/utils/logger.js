/**
 * Structured JSON logger for CloudWatch compatibility.
 */

const winston = require('winston');
const config = require('../config');

const logger = winston.createLogger({
  level: config.logLevel,
  format: winston.format.combine(
    winston.format.timestamp({ format: 'ISO' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: config.appName, version: config.appVersion },
  transports: [
    new winston.transports.Console({
      format: config.nodeEnv === 'production'
        ? winston.format.json()
        : winston.format.combine(winston.format.colorize(), winston.format.simple()),
    }),
  ],
});

module.exports = logger;
