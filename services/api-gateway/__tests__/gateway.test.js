const request = require('supertest');
const createApp = require('../src/app');

let app;
beforeAll(() => { app = createApp(); });

describe('API Gateway', () => {
  describe('GET /', () => {
    it('should return service metadata and endpoint map', async () => {
      const res = await request(app).get('/');
      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty('service', 'damolak-api-gateway');
      expect(res.body.endpoints).toHaveProperty('auth');
      expect(res.body.endpoints).toHaveProperty('data');
      expect(res.body.endpoints).toHaveProperty('processing');
      expect(res.body.endpoints).toHaveProperty('notifications');
    });
  });

  describe('GET /health', () => {
    it('should return health status (degraded when services are down)', async () => {
      const res = await request(app).get('/health');
      // In test env, downstream services aren't running
      expect([200, 207]).toContain(res.status);
      expect(res.body).toHaveProperty('status');
      expect(res.body).toHaveProperty('downstream');
      expect(res.body).toHaveProperty('uptime');
    });
  });

  describe('GET /nonexistent', () => {
    it('should return 404', async () => {
      const res = await request(app).get('/nonexistent');
      expect(res.status).toBe(404);
      expect(res.body).toHaveProperty('status', 'error');
    });
  });

  describe('Request ID propagation', () => {
    it('should generate X-Request-ID when not provided', async () => {
      const res = await request(app).get('/');
      expect(res.headers['x-request-id']).toBeDefined();
    });

    it('should preserve provided X-Request-ID', async () => {
      const res = await request(app)
        .get('/')
        .set('X-Request-ID', 'test-trace-123');
      expect(res.headers['x-request-id']).toBe('test-trace-123');
    });
  });
});
