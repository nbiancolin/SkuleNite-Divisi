@echo off

docker compose -f docker-compose.dev.yml down -v db
docker compose -f docker-compose.dev.yml up db -d