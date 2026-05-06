/**
 * API Gateway — Express Application
 *
 * Routes incoming requests to the appropriate downstream microservice.
 * Acts as the single entry point — clients never talk to internal services directly.
 *
 * Routing strategy:
 *   /api/auth/*       → Auth Service (Java/Spring Boot)
 *   /api/data/*       → Data Service (Python/FastAPI)
 *   /api/processing/* → Processing Service (Go)
 *   /api/notify/*     → Notification Service (Python)
 *   /health           → Local health + downstream aggregation
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const { v4: uuidv4 } = require('uuid');
const axios = require('axios');
const rateLimit = require('express-rate-limit');

const config = require('./config');
const logger = require('./utils/logger');

function createApp() {
  const app = express();

  // ─── Security ──────────────────────────────────────
  app.use(helmet());
  app.use(cors({
    origin: process.env.CORS_ORIGIN || '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID'],
  }));

  // ─── Rate Limiting ────────────────────────────────
  app.use('/api/', rateLimit({
    windowMs: config.rateLimitWindowMs,
    max: config.rateLimitMax,
    standardHeaders: true,
    legacyHeaders: false,
    message: { status: 'error', message: 'Rate limit exceeded. Try again later.' },
  }));

  // ─── Body Parsing ─────────────────────────────────
  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true }));

  // ─── Request ID Propagation ───────────────────────
  app.use((req, res, next) => {
    req.requestId = req.headers['x-request-id'] || uuidv4();
    res.setHeader('X-Request-ID', req.requestId);
    next();
  });

  // ─── HTTP Logging ─────────────────────────────────
  app.use(morgan(':method :url :status :res[content-length] - :response-time ms', {
    stream: { write: (msg) => logger.info(msg.trim(), { type: 'http' }) },
  }));

  // ─── Root ─────────────────────────────────────────
  app.get('/', (req, res) => {
    res.json({
      service: config.appName,
      version: config.appVersion,
      endpoints: {
        health: '/health',
        auth: '/api/auth',
        data: '/api/data',
        processing: '/api/processing',
        notifications: '/api/notify',
      },
    });
  });

  // ─── Health Check ─────────────────────────────────
  app.get('/health', async (req, res) => {
    const checks = {};
    const serviceEntries = Object.entries(config.services);

    await Promise.allSettled(
      serviceEntries.map(async ([name, url]) => {
        try {
          const start = Date.now();
          const resp = await axios.get(`${url}/health`, { timeout: 3000 });
          checks[name] = {
            status: 'healthy',
            responseMs: Date.now() - start,
            data: resp.data,
          };
        } catch (err) {
          checks[name] = { status: 'unreachable', error: err.message };
        }
      })
    );

    const allHealthy = Object.values(checks).every((c) => c.status === 'healthy');

    res.status(allHealthy ? 200 : 207).json({
      status: allHealthy ? 'healthy' : 'degraded',
      service: config.appName,
      version: config.appVersion,
      timestamp: new Date().toISOString(),
      uptime: Math.floor(process.uptime()),
      downstream: checks,
    });
  });

  // ─── Proxy Helper ─────────────────────────────────
  // Generic reverse proxy function. Forwards request body,
  // headers, and query params to the target service.
  const proxyRequest = (serviceUrl) => async (req, res) => {
    const targetPath = req.originalUrl.replace(/^\/api\/\w+/, '');
    const url = `${serviceUrl}${targetPath || '/'}`;

    try {
      const response = await axios({
        method: req.method,
        url,
        data: req.body,
        params: req.query,
        headers: {
          'Content-Type': req.headers['content-type'] || 'application/json',
          'X-Request-ID': req.requestId,
          'Authorization': req.headers['authorization'] || '',
        },
        timeout: 15000,
        validateStatus: () => true, // Don't throw on 4xx/5xx — forward them
      });

      // Forward downstream response headers
      if (response.headers['content-type']) {
        res.setHeader('Content-Type', response.headers['content-type']);
      }

      res.status(response.status).json(response.data);
    } catch (error) {
      logger.error('Proxy request failed', {
        requestId: req.requestId,
        targetUrl: url,
        error: error.message,
      });

      res.status(502).json({
        status: 'error',
        message: `Service unavailable: ${error.message}`,
        requestId: req.requestId,
      });
    }
  };

  // ─── Service Routes ───────────────────────────────
  app.all('/api/auth/*', proxyRequest(config.services.auth));
  app.all('/api/auth', proxyRequest(config.services.auth));

  app.all('/api/data/*', proxyRequest(config.services.data));
  app.all('/api/data', proxyRequest(config.services.data));

  app.all('/api/processing/*', proxyRequest(config.services.processing));
  app.all('/api/processing', proxyRequest(config.services.processing));

  app.all('/api/notify/*', proxyRequest(config.services.notification));
  app.all('/api/notify', proxyRequest(config.services.notification));

  // ─── 404 ──────────────────────────────────────────
  app.use((req, res) => {
    res.status(404).json({
      status: 'error',
      message: `Route ${req.method} ${req.originalUrl} not found`,
      requestId: req.requestId,
    });
  });

  // ─── Global Error Handler ─────────────────────────
  app.use((err, req, res, _next) => {
    logger.error('Unhandled error', { error: err.message, stack: err.stack });
    res.status(500).json({
      status: 'error',
      message: config.nodeEnv === 'production' ? 'Internal Server Error' : err.message,
      requestId: req.requestId,
    });
  });

  return app;
}

module.exports = createApp;
