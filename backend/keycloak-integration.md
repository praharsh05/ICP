# Keycloak Integration Guide

## Overview

The ICP backend supports two authentication modes controlled by the `AUTH_PROVIDER` environment variable:

| Mode | Value | Description |
|------|-------|-------------|
| Local | `AUTH_PROVIDER=local` | Username/password login with local JWT tokens. No external IdP needed. |
| Keycloak | `AUTH_PROVIDER=keycloak` | Keycloak OIDC SSO. Tokens are validated against Keycloak's JWKS endpoint. |

---

## Quick Start (Local Mode)

No Keycloak setup required. Users are authenticated against the PostgreSQL `users` table.

```bash
# backend/.env
AUTH_PROVIDER=local
JWT_SECRET_KEY=your-random-secret
```

---

## Connecting to an Existing Keycloak Instance

### 1. Set Environment Variables

```bash
# backend/.env
AUTH_PROVIDER=keycloak
KEYCLOAK_URL=https://your-keycloak-server.example.com
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=your-client-id
```

For Docker Compose, update `docker-compose.yml`:

```yaml
backend:
  environment:
    - AUTH_PROVIDER=keycloak
    - KEYCLOAK_URL=http://keycloak:8080      # internal Docker network URL
    - KEYCLOAK_REALM=your-realm
    - KEYCLOAK_CLIENT_ID=your-client-id
```

### 2. Keycloak Client Configuration

Create a client in your Keycloak realm with the following settings:

| Setting | Value |
|---------|-------|
| Client ID | `icp-frontend` (or your chosen ID) |
| Client Protocol | `openid-connect` |
| Access Type | `public` |
| Authentication Flow | Standard + PKCE |
| Valid Redirect URIs | `http://localhost:6693/*` (adjust for your frontend URL) |
| Web Origins | `http://localhost:6693` (adjust for your frontend URL) |
| Post Logout Redirect URIs | `http://localhost:6693/*` |

### 3. Realm Roles

Create these realm roles in Keycloak (map them to users as needed):

| Role | Description |
|------|-------------|
| `admin` | Full system access |
| `analyst` | Can view and analyze data |
| `viewer` | Read-only access |

The backend filters out Keycloak system roles (`offline_access`, `uma_authorization`, `default-roles-*`) automatically.

### 4. Groups (Optional)

If you use Keycloak groups, add the **groups** mapper to your client:

1. Go to **Client > icp-frontend > Client Scopes > icp-frontend-dedicated**
2. Add mapper: **Group Membership**
   - Name: `groups`
   - Token Claim Name: `groups`
   - Full group path: `OFF`

Groups are synced to the user record and can be used for role mapping via `config/role_mapping.yaml`.

### 5. Frontend Configuration

The frontend needs to know where Keycloak is:

```bash
# frontend/.env or docker-compose environment
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8080
NEXT_PUBLIC_KEYCLOAK_REALM=icp
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=icp-frontend
```

---

## How It Works

### Token Flow

```
Browser → Keycloak login page → OIDC redirect with access token
    → Frontend sends Bearer token to backend
    → Backend validates token against Keycloak JWKS endpoint
    → User auto-provisioned/synced in PostgreSQL
    → Response returned
```

### Auto-Provisioning

On first login, the backend automatically creates a user in PostgreSQL using claims from the Keycloak token:

- `sub` → `keycloak_sub` (stable user identifier)
- `preferred_username` → `username`
- `email` → `email`
- `given_name` / `family_name` / `name` → name fields
- `realm_access.roles` → `roles`
- `groups` → `groups`

On subsequent logins, these fields are synced from the latest token.

### Key Backend Files

| File | Purpose |
|------|---------|
| `app/config.py` | Central config — reads `AUTH_PROVIDER` flag |
| `app/auth/authentication.py` | Unified `get_current_user` dependency — routes to Keycloak or local handler |
| `app/auth/keycloak_auth.py` | Keycloak JWKS validation and token claim extraction |
| `app/auth/jwt_handler.py` | Local JWT creation and validation |
| `app/routers/auth.py` | Auth endpoints — adapts based on active provider |

### API Endpoints

| Endpoint | Keycloak Mode | Local Mode |
|----------|--------------|------------|
| `GET /api/v1/auth/provider` | `{"provider": "keycloak"}` | `{"provider": "local"}` |
| `GET /api/v1/auth/me` | Returns user from Keycloak token | Returns user from local JWT |
| `GET /api/v1/auth/keycloak-config` | Returns Keycloak URL/realm/clientId | 404 |
| `POST /api/v1/auth/login` | 404 | Returns local JWT |
| `POST /api/v1/auth/logout` | Returns Keycloak logout URL | Returns discard message |

---

## Switching Between Modes

Simply change `AUTH_PROVIDER` and restart the backend:

```bash
# Switch to Keycloak
AUTH_PROVIDER=keycloak

# Switch to local
AUTH_PROVIDER=local
```

No code changes or redeployment needed — just an environment variable.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `keycloak_db does not exist` | Run `CREATE DATABASE keycloak_db;` in PostgreSQL before starting Keycloak |
| `No matching public key found` | Keycloak URL is wrong or unreachable from the backend container |
| `Token validation failed` | Check that `KEYCLOAK_REALM` matches the realm that issued the token |
| CORS errors on frontend | Ensure Keycloak's **Web Origins** includes your frontend URL |
| Roles not showing up | Verify roles are assigned at the **realm level**, not just client level |
| Groups missing from token | Add the **Group Membership** mapper to the client scope (see step 4) |

---

## Test Users (Built-in Keycloak Realm)

If using the included `keycloak/icp-realm.json` auto-import:

| Username | Password | Roles |
|----------|----------|-------|
| admin | admin123 | admin |
| analyst | analyst123 | analyst |
| viewer | viewer123 | viewer |
| agent | agent123 | agent |
