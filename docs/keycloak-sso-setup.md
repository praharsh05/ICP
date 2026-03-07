# Keycloak SSO Setup Guide

## Architecture

```
Browser (Frontend)
    │
    │  1. User clicks "Sign in with Keycloak"
    ▼
Keycloak (port 8080)  ──► Postgres keycloak_db (realm data, sessions)
    │
    │  2. OIDC Authorization Code flow (PKCE)
    │  3. Returns access_token (JWT signed with realm private key)
    ▼
Browser stores token
    │
    │  4. API call with Bearer <access_token>
    ▼
Backend (FastAPI, port 8000)
    │  5. Fetches Keycloak JWKS and validates token signature
    │  6. Extracts sub, email, roles from claims
    │  7. Auto-provisions user in PostgreSQL on first login
    ▼
PostgreSQL icp_db (users table, keycloak_sub column)
```

## Services

| Service    | URL                        | Credentials          |
|------------|----------------------------|----------------------|
| Keycloak   | http://localhost:8080      | admin / admin        |
| Frontend   | http://localhost:6693      | —                    |
| Backend    | http://localhost:8000      | —                    |
| PostgreSQL | localhost:5432             | postgres / postgres  |

## Realm: `icp`

Auto-imported from `keycloak/icp-realm.json` on first start.

### Pre-created test users

| Username | Password    | Role     |
|----------|-------------|----------|
| admin    | admin123    | admin    |
| analyst  | analyst123  | analyst  |
| viewer   | viewer123   | viewer   |
| agent    | agent123    | agent    |

### Keycloak client

- **Client ID**: `icp-frontend`
- **Type**: Public (no secret — SPA)
- **Flow**: Authorization Code + PKCE
- **Redirect URIs**: `http://localhost:6693/*`

## First-time setup

```bash
# 1. Start all services
docker compose up -d

# Wait ~90 seconds for Keycloak to start and import the realm

# 2. Verify Keycloak realm is ready
curl http://localhost:8080/realms/icp

# 3. Install frontend dependencies
cd frontend && npm install

# 4. Start frontend (dev)
npm run dev
```

## Existing database migration (LDAP → Keycloak)

If upgrading from the LDAP-based setup, run once:

```bash
cd backend
python scripts/migrate_to_keycloak.py
```

This:
- Adds the `keycloak_sub` column to the `users` table
- Drops the deprecated `ldap_dn` and `last_sync` columns

## Environment variables

### Backend (`backend/.env` or docker-compose environment)

```env
KEYCLOAK_URL=http://localhost:8080    # http://keycloak:8080 inside Docker
KEYCLOAK_REALM=icp
KEYCLOAK_CLIENT_ID=icp-frontend
```

### Frontend (`frontend/.env.local` or docker-compose environment)

```env
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_REALM=icp
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=icp-frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Token flow detail

1. Frontend calls `keycloak.init({ onLoad: 'check-sso' })`
2. If no active session, calls `keycloak.login()` → browser redirects to Keycloak
3. After login, Keycloak redirects back with auth code
4. `keycloak-js` exchanges code for tokens automatically (PKCE)
5. Frontend calls backend APIs with `Authorization: Bearer <access_token>`
6. Backend verifies token against `http://keycloak:8080/realms/icp/protocol/openid-connect/certs`
7. If valid, user is auto-provisioned/updated in PostgreSQL and the request proceeds

## Token auto-refresh

`keycloak-js` automatically refreshes the access token (default: when < 30 s remaining)
via `keycloak.updateToken(30)`. No explicit refresh logic is needed in the frontend.

## Admin UI

Access the Keycloak Admin Console at `http://localhost:8080` → "Administration Console"
with credentials `admin / admin` to:
- Add/remove users
- Assign roles
- Configure MFA
- View active sessions
- Integrate with external identity providers (LDAP, SAML, Google, etc.)

## LDAP Federation (optional)

To federate Keycloak with an existing LDAP/AD:
1. Keycloak Admin Console → Realm Settings → User Federation → Add LDAP
2. Configure LDAP connection — Keycloak will import/sync users automatically
3. No changes to the backend or frontend are needed

## Security notes

- Tokens are validated using the realm's RS256 public key (never the Keycloak server directly)
- PKCE is enforced on the public client to prevent auth code interception
- The backend never handles passwords — all credential logic is in Keycloak
- Token lifespan: access token 1 h, SSO session 10 h (configurable in realm settings)
