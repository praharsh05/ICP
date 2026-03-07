/**
 * Keycloak OIDC client — singleton, browser-only.
 *
 * Race-condition fix:
 * `_initPromise` is assigned SYNCHRONOUSLY (before any await) so that
 * React StrictMode's double-invocation of useEffect cannot trigger two
 * concurrent kc.init() calls. Both concurrent callers share the same promise.
 */

let _keycloak: any = null;
let _initPromise: Promise<boolean> | null = null;

export async function getKeycloak() {
  if (typeof window === 'undefined') {
    throw new Error('Keycloak can only be used in the browser');
  }

  if (!_keycloak) {
    const Keycloak = (await import('keycloak-js')).default;
    _keycloak = new Keycloak({
      url: process.env.NEXT_PUBLIC_KEYCLOAK_URL || 'http://localhost:8080',
      realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'icp',
      clientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || 'icp-frontend',
    });
  }

  return _keycloak;
}

/**
 * Core init — guaranteed to call kc.init() EXACTLY ONCE per page load,
 * regardless of concurrent callers (React StrictMode, etc.).
 *
 * The trick: `_initPromise` is set to an IIFE promise synchronously,
 * so any second caller sees it immediately and returns the same promise.
 */
function _init(): Promise<boolean> {
  if (_initPromise) return _initPromise;

  // Assign synchronously — no await before this line
  _initPromise = (async () => {
    const kc = await getKeycloak();

    const authenticated = await kc.init({
      pkceMethod: 'S256',
      checkLoginIframe: false,
      // No onLoad — we control the redirect ourselves to avoid auto-loops
    });

    return authenticated;
  })();

  return _initPromise;
}

/**
 * For PROTECTED pages (/app).
 *
 * - Returns true when authenticated (session restored or auth code exchanged).
 * - If not authenticated AND no auth code in the URL → redirects to Keycloak.
 * - If not authenticated BUT auth code present → exchange failed (expired/used);
 *   clears the stale URL and does ONE clean redirect — no loop.
 */
export async function initKeycloakRequired(): Promise<boolean> {
  let authenticated: boolean;

  try {
    authenticated = await _init();
  } catch (err) {
    console.error('[Keycloak] init error:', err);
    // Reset so a clean retry is possible
    _initPromise = null;
    _keycloak = null;
    // Strip the broken hash and redirect to login
    window.history.replaceState(null, '', window.location.pathname);
    await keycloakLogin(`${window.location.origin}/app`);
    return false;
  }

  if (!authenticated) {
    const hasCode =
      window.location.hash.includes('code=') ||
      window.location.search.includes('code=');

    if (hasCode) {
      // Stale / already-used code — clear it and do a clean login
      console.warn('[Keycloak] auth code present but init returned false — clearing and retrying');
      _initPromise = null;
      _keycloak = null;
      window.history.replaceState(null, '', window.location.pathname);
    }

    await keycloakLogin(`${window.location.origin}/app`);
    return false; // browser navigated away
  }

  return true;
}

/**
 * For PUBLIC pages (/landing).
 * Returns true if already authenticated — no redirect.
 */
export async function initKeycloakPassive(): Promise<boolean> {
  try {
    return await _init();
  } catch {
    return false;
  }
}

/**
 * Redirect to the Keycloak login page.
 */
export async function keycloakLogin(redirectUri?: string) {
  const kc = await getKeycloak();
  await kc.login({
    redirectUri: redirectUri || `${window.location.origin}/app`,
  });
}

/**
 * Redirect to the Keycloak logout endpoint, then to /landing.
 */
export async function keycloakLogout(redirectUri?: string) {
  const kc = await getKeycloak();
  await kc.logout({
    redirectUri: redirectUri || `${window.location.origin}/landing`,
  });
}

/**
 * Return the current access token, refreshing silently if near expiry.
 */
export async function getAccessToken(): Promise<string | null> {
  const kc = await getKeycloak();
  if (!kc.authenticated) return null;

  try {
    await kc.updateToken(30);
  } catch {
    await kc.login({ redirectUri: window.location.href });
    return null;
  }

  return kc.token ?? null;
}

/**
 * Synchronous — only reliable after initKeycloak* has resolved.
 */
export function isKeycloakAuthenticated(): boolean {
  return !!_keycloak?.authenticated;
}
