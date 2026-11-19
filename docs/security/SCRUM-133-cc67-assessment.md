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

## AC02, AC03, and AC07: Local HTTP Baseline Tests

### Test Environment

- Environment: Local Docker development
- Execution date: November 5, 2026
- Time: Approximately 4:36 PM PST
- Backend: FastAPI/Uvicorn on localhost:8000
- Credentials used: None
- Test tool: curl

### Test 1: Backend Health Endpoint

Request:
GET http://localhost:8000/health

Expected:
Record whether the backend accepts HTTP requests.

Actual:
HTTP 200 OK.

Result:
The local backend accepts HTTP GET requests.

### Test 2: Unauthenticated Account Endpoint

Request:
GET http://localhost:8000/auth/me

Expected:
Record authentication and HTTP handling behavior.

Actual:
HTTP 401 Unauthorized.
WWW-Authenticate: Bearer.
No HTTPS redirect observed.

Result:
The local endpoint requires authentication but does not
redirect this request to HTTPS.

### Test 3: Negative Authentication Test

Request:
POST http://localhost:8000/auth/login

Content-Type: application/json
Body: {}

Expected:
Determine whether an HTTP login request is redirected,
rejected specifically for insecure transport, or processed
by application validation.

Actual:
HTTP 422 Unprocessable Entity.
No HTTPS redirect observed.

Result:
The local backend processes an HTTP login request through
request validation. No credentials or tokens were submitted.

### Assessment Interpretation

These tests establish baseline behavior for the local
development environment.

They do not establish whether publicly accessible staging
or production deployments enforce HTTPS.

AC02 and AC03 remain unverified for public environments.

AC07 has been partially assessed through a controlled,
credential-free local negative test. The public-path
acceptance criterion remains pending.

### Remaining Verification

- Test the actual staging HTTPS endpoint.
- Determine whether staging HTTP requests redirect or fail.
- Verify authentication requests in browser developer tools.
- Inspect AWS security-group restrictions.
- Validate TLS certificates and termination configuration.
- Repeat relevant tests after any security remediation.

## AWS Staging Infrastructure Verification

### Environment
- Region: us-west-1
- Instance: smp-staging
- Assessment date: November 5, 2026
- Access method: AWS Systems Manager Session Manager
- Inspection method: Read-only configuration and HTTP requests

### AWS Network Findings
- EC2 instance is running with a public IPv4 address.
- Inbound TCP port 80 is restricted to one IPv4 /32 source.
- Inbound TCP port 22 is restricted to the same /32 source.
- No inbound port 443 rule was identified.
- No Elastic Load Balancers were found in us-west-1.
- No AWS Certificate Manager certificates were found in us-west-1.

### Docker and Nginx Findings
- Frontend container publishes host port 80.
- Backend container exposes port 8000 internally.
- PostgreSQL container exposes port 5432 internally.
- Nginx listens on port 80.
- Nginx proxies /api/ requests to http://backend:8000/.
- No Nginx TLS certificate or HTTPS listener was configured.
- No HTTP-to-HTTPS redirect was configured.

### Staging HTTP Verification

Test:
GET http://127.0.0.1/api/auth/me

Execution:
November 5, 2026, 5:16:38 PM PST

Expected:
Sensitive public API requests should use HTTPS.
Insecure public HTTP authentication paths should be
rejected for insecure transport or safely redirected.

Actual:
HTTP 401 Unauthorized.
Server: nginx/1.30.6.
WWW-Authenticate: Bearer.
No HTTPS redirect was observed.

Credentials submitted:
None.

Interpretation:
The staging Nginx-to-FastAPI authentication route is
reachable through HTTP from the EC2 host.

The request was rejected for missing authentication,
not because HTTP transport was insecure.

This identifies a staging HTTP-handling configuration
gap. External reachability and actual credential
transmission were not demonstrated by this test.

### Interim Control Status

CC6.7 remains partially verified.

AC03 failed for the tested staging HTTP authentication
path. Public exposure and complete HTTPS enforcement
require additional verification.

### Recommended Remediation
1. Coordinate HTTPS/TLS implementation with the
   infrastructure owner.
2. Identify an appropriate TLS termination component.
3. Configure HTTPS for sensitive application requests.
4. Redirect ordinary HTTP navigation to HTTPS.
5. Reject insecure authentication submissions before
   credentials are processed.
6. Verify certificate trust, expiration, and hostname.
7. Reassess internal service communication protection.
8. Repeat AC02, AC03, AC04, AC06, and AC07 tests.

## AC05: Internal Transmission Protection

### Assessment Environment
- AWS Region: us-west-1
- Instance: smp-staging
- Inspection method: AWS Systems Manager Session Manager
- Assessment date: November 5, 2026

### PostgreSQL TLS Verification

Command:
sudo docker exec stock-market-predictor-db-1 \
  psql -U smp -d smp -tAc "SHOW ssl;"

Actual result:
off

Finding:
PostgreSQL server-side TLS is disabled in the inspected
staging environment.

### Docker Network Inspection

Commands:
sudo docker network inspect stock-market-predictor_default \
  --format 'Driver={{.Driver}} Internal={{.Internal}}'

sudo docker network inspect stock-market-predictor_default \
  --format '{{range .Containers}}{{println .Name}}{{end}}'

Actual results:
- Driver: bridge
- Internal: false
- Connected containers:
  - stock-market-predictor-frontend-1
  - stock-market-predictor-backend-1
  - stock-market-predictor-db-1

### Network Protection Findings

The frontend, backend, and database share a Docker bridge
network on the staging EC2 host.

The database does not publish port 5432 to the EC2 host.

Nginx forwards API requests to FastAPI using HTTP.

PostgreSQL TLS is disabled.

These observations demonstrate missing transport encryption
mechanisms on inspected internal communication paths.

Docker network isolation reduces external exposure but does
not independently establish encryption or complete
protection against unauthorized interception.

### AC05 Status

Partially verified, with confirmed missing TLS mechanisms.

The acceptance criterion remains unmet pending verification
of adequate compensating network protections or remediation
of the identified transport encryption gaps.

### Remaining Work

1. Assess whether Docker bridge isolation provides adequate
   protection for the deployment trust boundaries.
2. Evaluate PostgreSQL TLS configuration requirements.
3. Evaluate encryption for Nginx-to-FastAPI connections.
4. Coordinate infrastructure remediation with the team.
5. Retest the affected communication paths.
6. Document evidence supporting any compensating controls.
