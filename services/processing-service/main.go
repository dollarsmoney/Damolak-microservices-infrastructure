/*
Processing Service — Go

High-throughput background job processor using goroutines.
Accepts processing requests from the Data Service,
processes them concurrently, and sends callbacks upon completion.

Design Decision: Go is chosen for this service because:
  - Goroutines enable lightweight concurrency without thread overhead
  - Low memory footprint ideal for Fargate cost optimization
  - Fast startup time (~50ms) vs Java (~5s) for scaling events
*/
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/mux"
)

// ── Configuration ────────────────────────────────────

type Config struct {
	Port            string
	MaxWorkers      int
	ShutdownTimeout time.Duration
}

func loadConfig() Config {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}
	return Config{
		Port:            port,
		MaxWorkers:      10,
		ShutdownTimeout: 30 * time.Second,
	}
}

// ── Models ───────────────────────────────────────────

type ProcessRequest struct {
	JobID       string                 `json:"job_id"`
	Type        string                 `json:"type"`
	Payload     map[string]interface{} `json:"payload"`
	Priority    string                 `json:"priority"`
	CallbackURL string                 `json:"callback_url"`
}

type ProcessResult struct {
	JobID       string `json:"job_id"`
	Status      string `json:"status"`
	DurationMs  int64  `json:"duration_ms"`
	ProcessedAt string `json:"processed_at"`
	WorkerID    int    `json:"worker_id"`
}

type HealthResponse struct {
	Status       string    `json:"status"`
	Service      string    `json:"service"`
	Version      string    `json:"version"`
	Timestamp    string    `json:"timestamp"`
	Uptime       float64   `json:"uptime"`
	ActiveJobs   int       `json:"active_jobs"`
	TotalProcessed int     `json:"total_processed"`
}

type StatsResponse struct {
	TotalProcessed int     `json:"total_processed"`
	TotalFailed    int     `json:"total_failed"`
	ActiveJobs     int     `json:"active_jobs"`
	AvgDurationMs  float64 `json:"avg_duration_ms"`
}

// ── Job Queue & Worker Pool ─────────────────────────

type JobQueue struct {
	jobs           chan ProcessRequest
	activeJobs     int
	totalProcessed int
	totalFailed    int
	totalDuration  int64
	mu             sync.RWMutex
	wg             sync.WaitGroup
	startTime      time.Time
}

func NewJobQueue(bufferSize int) *JobQueue {
	return &JobQueue{
		jobs:      make(chan ProcessRequest, bufferSize),
		startTime: time.Now(),
	}
}

func (q *JobQueue) Enqueue(job ProcessRequest) {
	q.jobs <- job
	q.mu.Lock()
	q.activeJobs++
	q.mu.Unlock()
	log.Printf("[ENQUEUE] job_id=%s type=%s priority=%s", job.JobID, job.Type, job.Priority)
}

func (q *JobQueue) StartWorkers(ctx context.Context, numWorkers int) {
	for i := 0; i < numWorkers; i++ {
		q.wg.Add(1)
		go q.worker(ctx, i)
	}
	log.Printf("[POOL] Started %d workers", numWorkers)
}

func (q *JobQueue) worker(ctx context.Context, workerID int) {
	defer q.wg.Done()

	for {
		select {
		case <-ctx.Done():
			log.Printf("[WORKER-%d] Shutting down", workerID)
			return
		case job, ok := <-q.jobs:
			if !ok {
				return
			}
			q.processJob(workerID, job)
		}
	}
}

func (q *JobQueue) processJob(workerID int, job ProcessRequest) {
	start := time.Now()
	log.Printf("[WORKER-%d] Processing job_id=%s type=%s", workerID, job.JobID, job.Type)

	// ── Simulate multi-stage processing ────────
	// Stage 1: Validation (50-100ms)
	time.Sleep(time.Duration(50+time.Now().UnixNano()%50) * time.Millisecond)

	// Stage 2: Transformation (100-200ms)
	time.Sleep(time.Duration(100+time.Now().UnixNano()%100) * time.Millisecond)

	// Stage 3: Enrichment (75-150ms)
	time.Sleep(time.Duration(75+time.Now().UnixNano()%75) * time.Millisecond)

	duration := time.Since(start)
	status := "completed"

	// Update stats
	q.mu.Lock()
	q.activeJobs--
	q.totalProcessed++
	q.totalDuration += duration.Milliseconds()
	q.mu.Unlock()

	log.Printf("[WORKER-%d] Completed job_id=%s duration=%dms", workerID, job.JobID, duration.Milliseconds())

	// Send callback to Data Service
	if job.CallbackURL != "" {
		go q.sendCallback(job, status, duration.Milliseconds(), workerID)
	}
}

func (q *JobQueue) sendCallback(job ProcessRequest, status string, durationMs int64, workerID int) {
	result := map[string]interface{}{
		"status":       status,
		"duration_ms":  durationMs,
		"processed_at": time.Now().UTC().Format(time.RFC3339),
		"worker_id":    workerID,
	}

	body, _ := json.Marshal(result)
	client := &http.Client{Timeout: 5 * time.Second}

	resp, err := client.Post(job.CallbackURL, "application/json",
		bytes.NewReader(body))
	if err != nil {
		log.Printf("[CALLBACK] Failed for job_id=%s: %v", job.JobID, err)
		return
	}
	defer resp.Body.Close()
	log.Printf("[CALLBACK] Sent for job_id=%s status=%d", job.JobID, resp.StatusCode)
}

func (q *JobQueue) GetStats() StatsResponse {
	q.mu.RLock()
	defer q.mu.RUnlock()

	avgDuration := float64(0)
	if q.totalProcessed > 0 {
		avgDuration = float64(q.totalDuration) / float64(q.totalProcessed)
	}

	return StatsResponse{
		TotalProcessed: q.totalProcessed,
		TotalFailed:    q.totalFailed,
		ActiveJobs:     q.activeJobs,
		AvgDurationMs:  avgDuration,
	}
}

func (q *JobQueue) Wait() {
	close(q.jobs)
	q.wg.Wait()
}

// ── HTTP Handlers ───────────────────────────────────

func healthHandler(queue *JobQueue) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		q := queue
		q.mu.RLock()
		resp := HealthResponse{
			Status:         "healthy",
			Service:        "damolak-processing-service",
			Version:        "1.0.0",
			Timestamp:      time.Now().UTC().Format(time.RFC3339),
			Uptime:         time.Since(q.startTime).Seconds(),
			ActiveJobs:     q.activeJobs,
			TotalProcessed: q.totalProcessed,
		}
		q.mu.RUnlock()

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}
}

func processHandler(queue *JobQueue) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req ProcessRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, `{"status":"error","message":"Invalid JSON"}`, http.StatusBadRequest)
			return
		}

		if req.JobID == "" || req.Type == "" {
			http.Error(w, `{"status":"error","message":"job_id and type are required"}`, http.StatusBadRequest)
			return
		}

		// Non-blocking enqueue
		queue.Enqueue(req)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusAccepted)
		json.NewEncoder(w).Encode(map[string]string{
			"status":  "accepted",
			"message": "Job queued for processing",
			"job_id":  req.JobID,
		})
	}
}

func statsHandler(queue *JobQueue) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(queue.GetStats())
	}
}

// ── Main ────────────────────────────────────────────

func main() {
	cfg := loadConfig()

	queue := NewJobQueue(100)

	// Start worker pool with context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	queue.StartWorkers(ctx, cfg.MaxWorkers)

	// Router
	r := mux.NewRouter()

	// Middleware: Request ID + logging
	r.Use(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			requestID := r.Header.Get("X-Request-ID")
			if requestID == "" {
				requestID = fmt.Sprintf("go-%d", time.Now().UnixNano())
			}
			w.Header().Set("X-Request-ID", requestID)

			start := time.Now()
			next.ServeHTTP(w, r)
			log.Printf("[HTTP] %s %s %dms request_id=%s",
				r.Method, r.URL.Path, time.Since(start).Milliseconds(), requestID)
		})
	})

	r.HandleFunc("/health", healthHandler(queue)).Methods("GET")
	r.HandleFunc("/process", processHandler(queue)).Methods("POST")
	r.HandleFunc("/stats", statsHandler(queue)).Methods("GET")

	// Server
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Start server in goroutine
	go func() {
		log.Printf("[SERVER] Processing Service starting on :%s with %d workers", cfg.Port, cfg.MaxWorkers)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[SERVER] Fatal: %v", err)
		}
	}()

	// Graceful shutdown on SIGTERM/SIGINT
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGTERM, syscall.SIGINT)
	sig := <-quit
	log.Printf("[SERVER] Received %s, initiating graceful shutdown...", sig)

	// Stop accepting new HTTP requests
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer shutdownCancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("[SERVER] HTTP shutdown error: %v", err)
	}

	// Stop workers and wait for in-flight jobs
	cancel()
	queue.Wait()

	log.Println("[SERVER] Shutdown complete")
}
