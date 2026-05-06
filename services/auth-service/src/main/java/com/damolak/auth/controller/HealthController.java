package com.damolak.auth.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

/**
 * Health endpoint — separate from Actuator for explicit ALB routing.
 */
@RestController
public class HealthController {

    private final Instant startTime = Instant.now();

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        long uptimeSeconds = Instant.now().getEpochSecond() - startTime.getEpochSecond();

        return ResponseEntity.ok(Map.of(
                "status", "healthy",
                "service", "damolak-auth-service",
                "version", "1.0.0",
                "timestamp", Instant.now().toString(),
                "uptime", uptimeSeconds
        ));
    }
}
