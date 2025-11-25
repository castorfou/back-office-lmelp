# test frontend /health (nginx)

bash -c 'FRONTEND_URL=$(/workspaces/back-office-lmelp/.claude/get-frontend-info.sh --url); echo "Frontend URL: $FRONTEND_URL"; curl -f -s "$FRONTEND_URL/health" 2>&1'

# suite a donner

comme explique dans `docker/build/frontend/TESTING.md`

update the healthcheck in `docker-compose.yml` dans l'issue `docker-lmelp` repository (Issue #5).
