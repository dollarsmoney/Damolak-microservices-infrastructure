# ── Multi-stage build: Processing Service (Go) ───────
# Stage 1: Build static binary
FROM golang:1.21-alpine AS build
WORKDIR /app
COPY go.mod ./
RUN GONOSUMCHECK=* GONOSUMDB=* GOFLAGS=-mod=mod go mod download
COPY *.go ./
RUN GONOSUMCHECK=* GONOSUMDB=* CGO_ENABLED=0 GOOS=linux GOFLAGS=-mod=mod go build -ldflags="-s -w" -o /processing-service

# Stage 2: Scratch image (minimal attack surface)
FROM alpine:3.19 AS production
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001 -G appgroup
RUN apk --no-cache add ca-certificates wget
WORKDIR /app
COPY --from=build /processing-service .
RUN chown appuser:appgroup /app/processing-service
USER appuser
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8081/health || exit 1
ENV PORT=8081
CMD ["./processing-service"]
