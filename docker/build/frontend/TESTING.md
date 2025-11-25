# Testing Nginx Health Endpoint

This document describes how to test the `/health` endpoint configuration.

## Quick Test

If the frontend container is running:

```bash
# Run the automated test script
./docker/build/frontend/test-health-endpoint.sh
```

## Manual Testing

### Prerequisites

The frontend container must be running in production mode (not Vite dev server).

### Test Steps

1. **Test health endpoint returns 200 OK**:
   ```bash
   curl -v http://localhost:80/health
   ```
   Expected output:
   ```
   HTTP/1.1 200 OK
   Content-Type: text/plain

   OK
   ```

2. **Test root endpoint still works**:
   ```bash
   curl -v http://localhost:80/
   ```
   Should return the Vue.js app HTML.

3. **Verify logging behavior**:
   ```bash
   # Clear existing logs or note current line count
   docker logs <frontend-container-name> 2>&1 | wc -l

   # Make requests
   curl http://localhost:80/health  # Should NOT be logged
   curl http://localhost:80/        # SHOULD be logged

   # Check logs again
   docker logs <frontend-container-name> 2>&1 | tail -10
   ```

   You should see the request to `/` but NOT the request to `/health`.

## Expected Behavior

- `/health` returns `200 OK` with body `OK`
- `/health` requests are NOT logged to nginx access logs
- `/` and other endpoints continue to work normally and ARE logged
- Docker healthcheck uses `/health` endpoint (configured in docker-compose)

## Troubleshooting

If tests fail:

1. **Check nginx configuration syntax**:
   ```bash
   docker exec <frontend-container> nginx -t
   ```

2. **View nginx error logs**:
   ```bash
   docker exec <frontend-container> cat /var/log/nginx/error.log
   ```

3. **Reload nginx configuration** (if container is running):
   ```bash
   docker exec <frontend-container> nginx -s reload
   ```

## Integration with Docker Healthcheck

After this change is deployed, update the healthcheck in `docker-compose.yml`:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/health"]
  interval: 30s
  timeout: 10s
  start_period: 5s
  retries: 3
```

This change should be made in the `docker-lmelp` repository (Issue #5).
