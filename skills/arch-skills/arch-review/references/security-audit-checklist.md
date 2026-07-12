# Security Audit Checklist

OWASP Top 10 + CVSS scoring framework for `/arch-review` Security Posture axis (v2.9.0+).

## Security Posture Axis (10 points)

The Security Posture axis evaluates OWASP Top 10 compliance and CVSS-scored findings.

### CVSS v3.1 Scoring

| CVSS Score | Severity | Deduction |
|-----------|----------|-----------|
| 9.0–10.0 | Critical | −5 points per finding |
| 7.0–8.9 | High | −2 points per finding |
| 4.0–6.9 | Medium | −1 point per finding |
| 0.1–3.9 | Low | Informational only |

## OWASP Top 10 Checks

### A01: Broken Access Control
- [ ] Authorization enforced in use case layer (not presentation)
- [ ] Default deny — no endpoint accessible without explicit authorization
- [ ] CORS configured correctly (no wildcard origins in production)
- [ ] IDOR prevention — access checks use authenticated user context, not client-supplied IDs
- [ ] Directory traversal prevented in file operations

### A02: Cryptographic Failures
- [ ] Sensitive data encrypted at rest (AES-256 minimum)
- [ ] TLS 1.2+ for all data in transit
- [ ] No weak algorithms (MD5, SHA1 for security, DES, RC4)
- [ ] Cryptographic keys managed securely (rotation, no hardcoding)
- [ ] Certificate validation enabled for outbound connections

### A03: Injection
- [ ] SQL: parameterized queries only (no string concatenation)
- [ ] NoSQL: input validation + query parameterization
- [ ] Command injection: no shell execution with user input
- [ ] LDAP injection: input sanitization
- [ ] Template injection: no user input in template rendering

### A04: Insecure Design
- [ ] Threat modeling performed during design phase
- [ ] Security controls aligned with data sensitivity
- [ ] Rate limiting on all public endpoints
- [ ] Fail-secure: errors don't expose internal state

### A05: Security Misconfiguration
- [ ] No default credentials in any environment
- [ ] Error messages don't leak stack traces or internal paths
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options)
- [ ] Unnecessary features/endpoints disabled
- [ ] Dependencies up to date (no known CVEs)

### A06: Vulnerable Components
- [ ] Dependency inventory maintained
- [ ] Automated CVE scanning in CI
- [ ] Transitive dependencies checked
- [ ] Unused dependencies removed

### A07: Authentication Failures
- [ ] Multi-factor authentication available for sensitive operations
- [ ] Password policy enforced (length, complexity, breach check)
- [ ] Session management: secure, HTTPOnly, SameSite cookies
- [ ] Brute-force protection (account lockout or CAPTCHA)
- [ ] Credential storage: bcrypt/argon2 (never plain, never MD5/SHA)

### A08: Software and Data Integrity
- [ ] CI/CD pipeline integrity verified
- [ ] Unsigned updates not accepted
- [ ] Serialized data validated before deserialization
- [ ] Software supply chain verified (SBOM, signed artifacts)

### A09: Security Logging and Monitoring
- [ ] Security events logged (auth failures, access denials, privilege changes)
- [ ] Logs don't contain sensitive data (passwords, tokens, PII)
- [ ] Alerting configured for anomalous patterns
- [ ] Audit trail tamper-resistant

### A10: Server-Side Request Forgery (SSRF)
- [ ] User-supplied URLs validated against allowlist
- [ ] Internal network not accessible via user-controlled requests
- [ ] DNS rebinding protection in place

## SAST Tool Recommendations

| Language | Tool | Command |
|----------|------|---------|
| Go | `govulncheck` | `govulncheck ./...` |
| Java | SpotBugs + Find Security Bugs | `spotbugs -plugin fb-contrib` |
| Python | Bandit | `bandit -r src/` |
| Multi | Semgrep | `semgrep --config=auto` |
| Multi | Trivy | `trivy fs --scanners vuln .` |

## Recording in REVIEW.md

Security findings are included in the standard AD table with Route = `/devtdd` (code fix) or `/arch-detail` (design gap). The Security Posture score is reported as part of the architecture health score.
