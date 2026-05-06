package com.damolak.auth.controller;

import com.damolak.auth.model.AuthRequest;
import com.damolak.auth.model.AuthResponse;
import com.damolak.auth.service.JwtService;
import io.jsonwebtoken.Claims;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Authentication Controller
 *
 * Endpoints:
 *   POST /login    — Authenticate and receive JWT
 *   POST /register — Create new user account
 *   POST /validate — Validate a JWT token (inter-service)
 *
 * Note: Uses in-memory user store for demonstration.
 * In production, back this with a database (RDS/DynamoDB).
 */
@RestController
public class AuthController {

    private static final Logger logger = LoggerFactory.getLogger(AuthController.class);

    private final JwtService jwtService;
    private final PasswordEncoder passwordEncoder;

    // In-memory user store (replace with DB in production)
    private final ConcurrentHashMap<String, UserRecord> users = new ConcurrentHashMap<>();

    public AuthController(JwtService jwtService, PasswordEncoder passwordEncoder) {
        this.jwtService = jwtService;
        this.passwordEncoder = passwordEncoder;

        // Seed a default admin user
        users.put("admin", new UserRecord(
                "admin",
                passwordEncoder.encode("admin123"),
                "admin"
        ));
        users.put("user", new UserRecord(
                "user",
                passwordEncoder.encode("user123"),
                "user"
        ));

        logger.info("Auth controller initialized with {} seeded users", users.size());
    }

    /**
     * POST /register — Create a new user account.
     */
    @PostMapping("/register")
    public ResponseEntity<?> register(@Valid @RequestBody AuthRequest request) {
        String username = request.getUsername().toLowerCase().trim();

        if (users.containsKey(username)) {
            logger.warn("Registration failed — username already exists: {}", username);
            return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
                    "status", "error",
                    "message", "Username already exists"
            ));
        }

        String encodedPassword = passwordEncoder.encode(request.getPassword());
        users.put(username, new UserRecord(username, encodedPassword, "user"));

        String token = jwtService.generateToken(username, "user");

        logger.info("User registered: {}", username);

        return ResponseEntity.status(HttpStatus.CREATED)
                .body(new AuthResponse(token, username, "user", 3600000));
    }

    /**
     * POST /login — Authenticate user and return JWT.
     */
    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody AuthRequest request) {
        String username = request.getUsername().toLowerCase().trim();

        UserRecord user = users.get(username);
        if (user == null || !passwordEncoder.matches(request.getPassword(), user.passwordHash)) {
            logger.warn("Login failed for user: {}", username);
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of(
                    "status", "error",
                    "message", "Invalid username or password"
            ));
        }

        String token = jwtService.generateToken(username, user.role);

        logger.info("User logged in: {}, role: {}", username, user.role);

        return ResponseEntity.ok(new AuthResponse(token, username, user.role, 3600000));
    }

    /**
     * POST /validate — Validate a JWT token.
     * Used by other services for inter-service authentication.
     */
    @PostMapping("/validate")
    public ResponseEntity<?> validateToken(@RequestBody Map<String, String> body) {
        String token = body.get("token");

        if (token == null || token.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of(
                    "status", "error",
                    "message", "Token is required"
            ));
        }

        // Strip "Bearer " prefix if present
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }

        Claims claims = jwtService.validateToken(token);

        if (claims == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of(
                    "status", "error",
                    "message", "Invalid or expired token"
            ));
        }

        return ResponseEntity.ok(Map.of(
                "status", "valid",
                "username", claims.getSubject(),
                "role", claims.get("role", String.class),
                "issuedAt", claims.getIssuedAt().toInstant().toString(),
                "expiresAt", claims.getExpiration().toInstant().toString()
        ));
    }

    /**
     * Internal user record.
     */
    private static class UserRecord {
        final String username;
        final String passwordHash;
        final String role;

        UserRecord(String username, String passwordHash, String role) {
            this.username = username;
            this.passwordHash = passwordHash;
            this.role = role;
        }
    }
}
