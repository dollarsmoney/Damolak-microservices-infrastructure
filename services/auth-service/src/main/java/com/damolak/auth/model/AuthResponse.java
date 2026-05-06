package com.damolak.auth.model;

import java.time.Instant;

/**
 * Authentication response payload.
 */
public class AuthResponse {

    private String status;
    private String token;
    private String tokenType;
    private String username;
    private String role;
    private long expiresIn;
    private Instant issuedAt;

    public AuthResponse() {}

    public AuthResponse(String token, String username, String role, long expiresIn) {
        this.status = "success";
        this.token = token;
        this.tokenType = "Bearer";
        this.username = username;
        this.role = role;
        this.expiresIn = expiresIn;
        this.issuedAt = Instant.now();
    }

    // Getters and setters
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getToken() { return token; }
    public void setToken(String token) { this.token = token; }
    public String getTokenType() { return tokenType; }
    public void setTokenType(String tokenType) { this.tokenType = tokenType; }
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public long getExpiresIn() { return expiresIn; }
    public void setExpiresIn(long expiresIn) { this.expiresIn = expiresIn; }
    public Instant getIssuedAt() { return issuedAt; }
    public void setIssuedAt(Instant issuedAt) { this.issuedAt = issuedAt; }
}
