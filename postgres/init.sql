-- Initialize additional databases
-- This script runs on first container start (when data volume is empty)

SELECT 'CREATE DATABASE keycloak_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak_db')\gexec
