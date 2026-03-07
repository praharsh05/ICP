# ICP Family Graph — System Architecture & Documentation

## Overview

The ICP (Identity and Citizenship Platform) Family Graph is a secure, government-grade web application for visualizing family relationships. It allows authorized personnel to search for a person by their Unified ID and explore their full family tree — parents, children, siblings, spouses, step-relationships, and guardians — rendered as an interactive graph.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          BROWSER (User)                                  │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │                  Next.js Frontend  (port 6693)                   │  │
│   │                                                                  │  │
│   │   /landing   ── public page, passive Keycloak init              │  │
│   │   /app       ── protected page, active Keycloak init            │  │
│   │   /tree/:id  ── protected page, family tree visualization       │  │
│   └──────────────┬───────────────────────────────┬───────────────────┘  │
│                  │  OIDC Authorization Code+PKCE  │  REST API calls      │
└──────────────────┼───────────────────────────────┼──────────────────────┘
                   │                               │
                   ▼                               ▼
   ┌───────────────────────────┐    ┌──────────────────────────────┐
   │   Keycloak 24.0           │    │   FastAPI Backend (port 8000) │
   │   (port 8080)             │    │                              │
   │                           │    │   - Validates JWT via JWKS   │
   │   - Realm: icp            │    │   - Auto-provisions users    │
   │   - Client: icp-frontend  │◄───│     in PostgreSQL on login   │
   │   - Users & Roles         │    │   - Queries Neo4j for trees  │
   │   - Issues JWT tokens     │    │   - Serves REST API          │
   │   - JWKS endpoint         │    └────────────┬─────────────────┘
   └───────────────────────────┘                 │
                                                 │
                              ┌──────────────────┴──────────────────┐
                              │                                      │
                 ┌────────────▼────────────┐       ┌────────────────▼────────┐
                 │   PostgreSQL (port 5432) │       │   Neo4j (port 7687)     │
                 │                         │       │                         │
                 │   - User accounts       │       │   - Person nodes        │
                 │   - keycloak_sub key    │       │     (Citizen, Resident) │
                 │   - Roles & groups      │       │   - Family relationships│
                 │   - Session data        │       │   - CHILD_OF, SPOUSE_OF │
                 └─────────────────────────┘       │   - STEP_CHILD_OF, etc. │
                                                   └─────────────────────────┘
```

---

## Keycloak SSO — Architecture & Flow

### What is Keycloak?

Keycloak is an open-source Identity and Access Management (IAM) server. In this system it acts as the **single source of truth for authentication** — the frontend and backend never store or handle passwords. All login, logout, session management, and token issuance is delegated to Keycloak.

### Protocol: Authorization Code Flow with PKCE

This system uses the **OIDC Authorization Code Flow with PKCE (Proof Key for Code Exchange)** — the most secure flow for browser-based (SPA) applications.

PKCE prevents authorization code interception attacks. The frontend generates a random `code_verifier`, hashes it to produce a `code_challenge` (SHA-256), and sends the challenge to Keycloak. When exchanging the code for tokens, it must prove it holds the original verifier — so even if an attacker intercepts the auth code, they cannot exchange it.

---

### Complete Login Flow (Step by Step)

```
User                  Frontend               Keycloak               Backend
 │                       │                      │                      │
 │  Click "Sign In"       │                      │                      │
 │──────────────────────►│                      │                      │
 │                       │                      │                      │
 │                       │ 1. Generate           │                      │
 │                       │    code_verifier      │                      │
 │                       │    code_challenge     │                      │
 │                       │    (SHA-256 hash)     │                      │
 │                       │                      │                      │
 │                       │ 2. Redirect browser   │                      │
 │                       │    to Keycloak login  │                      │
 │◄──────────────────────│    with               │                      │
 │   Browser redirects   │    code_challenge     │                      │
 │──────────────────────────────────────────────►│                      │
 │                       │                      │                      │
 │  Enter credentials    │                      │                      │
 │──────────────────────────────────────────────►│                      │
 │                       │                      │                      │
 │                       │                      │ 3. Validates creds   │
 │                       │                      │    Generates auth    │
 │                       │                      │    code              │
 │                       │                      │                      │
 │                       │ 4. Keycloak redirects │                      │
 │◄──────────────────────────────────────────────│                      │
 │   /landing?code=xxx   │                      │                      │
 │   &state=yyy          │                      │                      │
 │──────────────────────►│                      │                      │
 │                       │                      │                      │
 │                       │ 5. keycloak-js        │                      │
 │                       │    detects code=      │                      │
 │                       │    in URL, exchanges  │                      │
 │                       │    code + code_verifier                      │
 │                       │──────────────────────►│                      │
 │                       │                      │ 6. Verifies          │
 │                       │                      │    code_verifier     │
 │                       │                      │    matches challenge │
 │                       │                      │                      │
 │                       │◄──────────────────────│                      │
 │                       │  access_token (JWT)   │                      │
 │                       │  refresh_token        │                      │
 │                       │  id_token             │                      │
 │                       │                      │                      │
 │                       │ 7. isLoggedIn = true  │                      │
 │◄──────────────────────│    Show "Access       │                      │
 │   Landing page        │    System" button     │                      │
 │   (authenticated)     │                      │                      │
 │                       │                      │                      │
 │  Enter Unified ID     │                      │                      │
 │──────────────────────►│                      │                      │
 │                       │                      │                      │
 │                       │ 8. API call with      │                      │
 │                       │    Authorization:     │                      │
 │                       │    Bearer <JWT>       │                      │
 │                       │─────────────────────────────────────────────►│
 │                       │                      │                      │ 9. Validate JWT
 │                       │                      │                      │    via JWKS
 │                       │                      │◄─────────────────────│
 │                       │                      │  Public keys (JWKS)  │
 │                       │                      │─────────────────────►│
 │                       │                      │                      │ 10. Verify
 │                       │                      │                      │     signature
 │                       │                      │                      │     Query Neo4j
 │◄──────────────────────────────────────────────────────────────────── │
 │   Family tree data    │                      │                      │
```

---

### Token Lifecycle

```
                    ┌─────────────────────────────────────┐
                    │         Keycloak Token Bundle        │
                    │                                     │
                    │  access_token  (JWT, ~5 min TTL)    │
                    │  ├── sub: "uuid-of-user"            │
                    │  ├── preferred_username: "admin"    │
                    │  ├── email: "admin@icp.local"       │
                    │  ├── realm_access.roles: [...]      │
                    │  └── exp: <timestamp>               │
                    │                                     │
                    │  refresh_token  (~30 min TTL)       │
                    │  └── used to get a new access_token │
                    │      without re-login               │
                    │                                     │
                    │  id_token  (user identity only)     │
                    └─────────────────────────────────────┘

Token refresh (handled automatically by keycloak-js):
  - Every API call checks if access_token expires within 30 seconds
  - If yes, calls kc.updateToken(30) to silently refresh
  - If refresh_token is also expired → redirect to login
```

---

### Backend JWT Validation (No Keycloak Contact Per Request)

The backend does **not** call Keycloak on every API request. Instead it validates tokens locally using Keycloak's public keys:

```
Backend receives:  Authorization: Bearer eyJhbGci...

Step 1: Decode JWT header → get kid (Key ID)
        { "alg": "RS256", "kid": "abc123" }

Step 2: Fetch JWKS from Keycloak (cached in memory)
        GET http://keycloak:8080/realms/icp/protocol/openid-connect/certs
        Returns: { "keys": [ { "kid": "abc123", "n": "...", "e": "AQAB" } ] }

Step 3: Find the matching public key by kid

Step 4: Verify RS256 signature locally
        - Checks token has not been tampered with
        - Checks token is not expired
        - Checks issuer matches our Keycloak realm

Step 5: Extract claims (sub, username, email, roles)

Step 6: Auto-provision or sync user in PostgreSQL
        - First login  → CREATE user row (keycloak_sub as stable key)
        - Subsequent   → UPDATE email, name, roles from latest token

Step 7: Return user object to the route handler
```

**Key rotation handling:** If the JWT's `kid` is not found in the cached JWKS, the cache is cleared and refreshed once from Keycloak before failing. This handles Keycloak key rotations transparently.

---

### Frontend Keycloak Init Strategy

Two different init strategies are used depending on the page type:

```
┌─────────────────────────────────────────────────────────┐
│  initKeycloakPassive()  — used on /landing              │
│                                                         │
│  - Calls kc.init({ pkceMethod: 'S256',                  │
│                    checkLoginIframe: false })            │
│  - If a ?code= is in the URL → exchanges it (post-login)│
│  - If no code and no session → returns false (silent)   │
│  - NEVER redirects automatically                        │
│  - Sets isLoggedIn React state when resolved            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  initKeycloakRequired()  — used on /app, /tree          │
│                                                         │
│  - Same kc.init() call                                  │
│  - If not authenticated → redirects to Keycloak login   │
│  - Handles stale auth codes (already-used codes):       │
│    detects code= in URL + false return → clears URL     │
│    and does ONE clean redirect (prevents loops)         │
│  - If authenticated → resolves true, page renders       │
└─────────────────────────────────────────────────────────┘
```

**React StrictMode race condition fix:**

React StrictMode in development double-invokes `useEffect`, which would cause two concurrent `kc.init()` calls — the second one would fail with "Code already used" and trigger an infinite redirect loop.

This is fixed with a module-level promise that is assigned **synchronously** before any `await`:

```typescript
// _initPromise is set BEFORE the first await.
// Any second concurrent caller sees it immediately and returns the same promise.
_initPromise = (async () => {
  const kc = await getKeycloak();
  return kc.init({ pkceMethod: 'S256', checkLoginIframe: false });
})();
```

Both concurrent calls share the same promise — `kc.init()` is called exactly once.

---

### Keycloak Realm Configuration

| Setting | Value |
|---------|-------|
| Realm | `icp` |
| Client ID | `icp-frontend` |
| Client Type | Public (no client secret — browser SPA) |
| PKCE Method | S256 (SHA-256) |
| Valid Redirect URIs | `http://localhost:6693/*` |
| Web Origins | `http://localhost:6693` |

**Realm Roles:**

| Role | Purpose |
|------|---------|
| `admin` | Full system access |
| `analyst` | Read + analysis access |
| `viewer` | Read-only access |
| `agent` | Field agent access |

**Test Users (development only):**

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | admin |
| `analyst` | `analyst123` | analyst |
| `viewer` | `viewer123` | viewer |
| `agent` | `agent123` | agent |

---

### Logout Flow

```
User clicks "Sign Out"
         │
         ▼
  authService.logout()
         │
         ▼
  kc.logout({ redirectUri: 'http://localhost:6693/landing' })
         │
         ▼
  Browser → Keycloak logout endpoint
         │  (invalidates SSO session)
         │
         ▼
  Keycloak → redirects to /landing
         │
         ▼
  Landing page loads, initKeycloakPassive() returns false
  isLoggedIn = false → shows "Sign In" button
```

---

## Data Flow: Family Tree Query

```
User enters Unified ID (e.g. "E5")
         │
         ▼
Frontend: GET /api/v1/persons/E5/exists
  └── Backend checks Neo4j: MATCH (p) WHERE p.spm_person_no = "E5"
  └── Returns: { exists: true, person_type: "citizen" }
         │
         ▼
Frontend: GET /api/v1/persons/E5/tree?depth=3
  └── Authorization: Bearer <access_token>
  └── Backend validates JWT → gets user from PostgreSQL
  └── Queries Neo4j with Cypher:
      - Ego node (self)
      - Spouses (SPOUSE_OF)
      - Biological parents & grandparents (CHILD_OF up to 2 hops)
      - Biological children & grandchildren (CHILD_OF down 2 hops)
      - Biological siblings (shared CHILD_OF parent)
      - Step-parents, step-children, step-siblings (STEP_CHILD_OF)
      - Guardians and wards (GUARDIAN_OF)
  └── Computes kinship label for each person relative to ego
  └── Returns: { root, nodes[], edges[] }
         │
         ▼
Frontend renders interactive ReactFlow graph
  - Nodes: person cards (name, DOB, gender, kinship)
  - Edges: relationship lines (color-coded by type)
```

---

## Directory Structure

```
ICP/
├── docker-compose.yml          # All services orchestration
├── keycloak/
│   └── icp-realm.json          # Realm import (users, roles, client config)
├── postgres/
│   └── init.sql                # Creates keycloak_db on first start
│
├── backend/
│   ├── app/
│   │   ├── auth/
│   │   │   ├── keycloak_auth.py    # JWT validation via JWKS
│   │   │   └── authentication.py  # FastAPI dependency: get_current_user()
│   │   ├── db/
│   │   │   ├── neo4j_client.py    # Neo4j driver singleton
│   │   │   └── postgres_client.py # SQLAlchemy session
│   │   ├── models/
│   │   │   └── user_db.py         # User table (keycloak_sub as stable key)
│   │   ├── routers/
│   │   │   ├── auth.py            # GET /api/v1/auth/me
│   │   │   └── family.py          # GET /api/v1/persons/:id/tree
│   │   └── services/
│   │       └── graph_service.py   # Neo4j Cypher tree query
│   └── scripts/
│       └── seed_neo4j.py          # Seeds mock family data
│
└── frontend/
    ├── utils/
    │   ├── keycloak.ts            # keycloak-js singleton + init logic
    │   └── authService.ts         # Auth facade used by components
    ├── components/
    │   └── AuthModal.tsx          # "Sign in with Keycloak" modal
    └── app/
        ├── landing/page.tsx       # Public landing page
        ├── app/page.tsx           # Notebook dashboard (protected)
        └── tree/[id]/page.tsx     # Family tree view (protected)
```

---

## Running the Project

### Prerequisites
- Docker + Docker Compose

### Start all services

```bash
docker compose up -d
```

Services start in dependency order:
1. **PostgreSQL** — starts first (Keycloak and backend depend on it)
2. **Neo4j** — starts in parallel with PostgreSQL
3. **Keycloak** — starts after PostgreSQL is healthy; imports `icp-realm.json` automatically
4. **Backend** — starts after PostgreSQL, Neo4j, and Keycloak are all healthy
5. **Frontend** — starts after backend

### Seed mock data

```bash
docker exec icp-backend python scripts/seed_neo4j.py
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:6693/landing |
| Backend API | http://localhost:8000/docs |
| Keycloak Admin | http://localhost:8080 (admin / admin) |
| Neo4j Browser | http://localhost:7474 (neo4j / password) |

### Test family tree IDs

| ID | Person | Relationship highlight |
|----|--------|----------------------|
| `E1` | Hassan Al Mazrouei | Grandfather — full 3-gen tree |
| `E5` | Omar Al Mazrouei | Father — parents, wife, 3 kids, step-child |
| `E9` | Ahmed Al Mazrouei | Grandchild — parents, grandparents, siblings |
| `E7` | Layla Al Mazrouei | Has resident spouse (R1) and ward (E13) |
| `R1` | John Smith | Resident spouse, connected to Layla's family |
