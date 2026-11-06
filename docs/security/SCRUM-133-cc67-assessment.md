# SCRUM-133: SOC 2 CC6.7 Interim Assessment

## Control
Protection of Information During Transmission (CC6.7)

## Assessment Scope
React frontend, FastAPI backend, PostgreSQL database,
Docker Compose networking, and staging deployment configuration.

## AC01: Communication Path Documentation

Status: Partially Assessed

### Repository Observations

1. React frontend:
   - API requests use VITE_API_BASE_URL.
   - Sensitive requests include login, registration,
     account access, and password recovery.

2. Staging frontend configuration:
   - .env.staging.example specifies an HTTP API URL.
   - CORS_ORIGINS also uses an HTTP origin.
   - Actual deployment configuration is not yet verified.

3. FastAPI backend:
   - Authentication routes are defined in
     backend/app/api/auth.py.
   - Staging Docker Compose publishes backend port 8000.

4. PostgreSQL:
   - Staging PostgreSQL has no published host port.
   - Backend database communication uses the Docker
     service hostname "db".
   - Database transport encryption is not yet verified.

5. Staging deployment:
   - Frontend port 5173 is published.
   - Backend port 8000 is published.
   - No TLS termination configuration was identified
     in the inspected Compose files.
   - AWS network exposure and security groups are unknown.

## Preliminary Findings

### F-01: Staging HTTP Configuration
The staging environment template contains HTTP-based
frontend/API configuration. Actual deployment use and
public exposure require verification.

### F-02: Published Application Ports
Staging Compose publishes frontend and backend ports.
AWS security groups and host firewall restrictions
must be assessed before determining external exposure.

### F-03: Internal Database Transport
PostgreSQL is not published directly in staging.
Encryption and compensating network protections for
backend-to-database traffic remain unverified.

## Supporting Repository Evidence

- .env.staging.example
- .env.production.example
- docker-compose.yml
- docker-compose.staging.yml
- frontend/src/pages/Login.jsx
- frontend/src/pages/Register.jsx
- frontend/src/pages/Account.jsx
- frontend/src/pages/ForgotPassword.jsx
- frontend/src/pages/ResetPassword.jsx
- backend/app/api/auth.py
- backend/tests/test_deployment_security.py
- backend/app/services/deployment_config.py
- .github/workflows/staging.yml
- scripts/deploy.py

## Outstanding Verification

- Identify actual staging TLS termination.
- Inspect AWS security-group and host firewall rules.
- Verify public HTTPS enforcement.
- Test public HTTP request handling.
- Validate applicable TLS certificates.
- Assess FastAPI-to-PostgreSQL transport security.
- Inspect authentication requests using browser tools.
- Collect sanitized, timestamped test evidence.

## Interim Conclusion

CC6.7-AC01 is partially assessed.

The repository provides evidence of application
communication paths and potential configuration risks,
but deployed transport security has not yet been verified.

No conclusion of full CC6.7 compliance is made.
