const API_BASE_URL = "http://localhost:8000/api/v1";
const TOKEN_KEY = 'niq_token';
const USER_KEY = 'niq_user';

// Token Helper functions
const auth = {
  // Save JWT + user info to localStorage after successful login/registeration
  saveSession: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  // Clear JWT + user info from localStorage on logout
  clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  // Return the raw JWT string from localStorage, or null if not found
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },

  // Return the parsed user object from localStorage, or null if not found
  getUser() {
    const userJson = localStorage.getItem(USER_KEY);
    return userJson ? JSON.parse(userJson) : null;
  },

  // Return true if a valid JWT token exists in localStorage, false otherwise
  isLoggedIn() {
    return !!localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Call every protected page at the top of DOMContentLoaded to redirect unauthenticated users to the login page
   * Note: This is a simple client-side check and should be complemented by server-side authentication checks on protected API endpoints
   */
  requireAuth() {
    if (!auth.isLoggedIn()) {
      window.location.href = getRoot() + 'index.html';
    }
  },

  /**
   * Call on login/register pages to redirect authenticated users away from the login page to the home page
   */
  redirectIfLoggedIn() {
    if (auth.isLoggedIn()) {
      window.location.href = getRoot() + 'html/home.html';
    }
  },
};

// ── CORE FETCH WRAPPER ────────────────────────────────────────
 
/**
 * Internal fetch wrapper.
 * Returns { data, error, status } — never throws.
 *
 * @param {string} method   - 'GET' | 'POST' | 'DELETE'
 * @param {string} path     - e.g. '/auth/login'
 * @param {object} [body]   - JSON body (omit for GET)
 * @param {object} [opts]   - extra options: { noAuth: true } to skip token header
 */

async function request(method, path, body = null, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
 
  if (!opts.noAuth) {
    const token = auth.getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }
 
  const config = { method, headers };
  if (body && method !== 'GET') config.body = JSON.stringify(body);
 
  let response;
  try {
    response = await fetch(API_BASE + path, config);
  } catch (networkErr) {
    // Server unreachable (not started, wrong port, CORS preflight blocked)
    console.error('[api] Network error:', networkErr);
    return { data: null, error: 'Cannot reach the server. Is the backend running?', status: 0 };
  }
 
  // 401 = token expired or invalid → force logout
  if (response.status === 401) {
    auth.clearSession();
    window.location.href = getRoot() + 'index.html';
    return { data: null, error: 'Session expired. Please log in again.', status: 401 };
  }
 
  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
 
  if (!response.ok) {
    // Backend should return { error: "message" } on non-2xx
    const errorMsg = data?.error || data?.message || `Request failed (${response.status})`;
    return { data: null, error: errorMsg, status: response.status };
  }
 
  return { data, error: null, status: response.status };
}
 
// ── PUBLIC API OBJECT ─────────────────────────────────────────
 
const api = {
  get:    (path, opts)       => request('GET',    path, null, opts),
  post:   (path, body, opts) => request('POST',   path, body, opts),
  delete: (path, opts)       => request('DELETE', path, null, opts),
};
 
// ── AUTH ACTIONS ──────────────────────────────────────────────
// These are higher-level helpers that call the API AND manage the session.
// Use these in landing.js instead of calling api.post directly.
 
const authActions = {
  /**
   * Log in with email + password.
   * On success: saves session, returns { data, error }.
   * Caller is responsible for redirecting.
   *
   * Expected server response:
   *   { token: "eyJ...", user: { id, name, email, plan } }
   */
  async login(email, password) {
    const { data, error, status } = await api.post(
      '/auth/login',
      { email, password },
      { noAuth: true }
    );
 
    if (error) return { data: null, error };
 
    auth.saveSession(data.token, data.user);
    return { data, error: null };
  },
 
  /**
   * Register a new account.
   * On success: saves session, returns { data, error }.
   *
   * Expected server response:
   *   { token: "eyJ...", user: { id, name, email, plan } }
   */
  async register(name, email, password) {
    const { data, error } = await api.post(
      '/auth/signup',
      { name, email, password },
      { noAuth: true }
    );
 
    if (error) return { data: null, error };
 
    auth.saveSession(data.token, data.user);
    return { data, error: null };
  },
 
  /**
   * Log out: clears local session, optionally calls server, redirects to landing.
   */
  async logout() {
    // Fire-and-forget: tell server to invalidate token if it supports it
    // If the server doesn't have POST /auth/logout yet, this will fail silently.
    await api.post('/auth/logout').catch(() => {});
    auth.clearSession();
    window.location.href = getRoot() + 'index.html';
  },
};
 
// ── SIDEBAR USER HYDRATION ────────────────────────────────────
// Call this on any authenticated page to fill in the user's name/email/avatar.
//
// Requires these elements in the sidebar (already in dashboard.html):
//   #userAvatar, #userName, #userEmail
 
function hydrateUserSidebar() {
  const user = auth.getUser();
  if (!user) return;
 
  const avatarEl = document.getElementById('userAvatar');
  const nameEl   = document.getElementById('userName');
  const emailEl  = document.getElementById('userEmail');
 
  if (avatarEl) avatarEl.textContent = getInitials(user.name);
  if (nameEl)   nameEl.textContent   = user.name;
  if (emailEl)  emailEl.textContent  = user.email;
}
 
// ── UTILITY ───────────────────────────────────────────────────
 
/** Derive initials from a full name: "Animesh Subedi" → "AS" */
function getInitials(name = '') {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}
 
/**
 * Returns '../' if we're inside html/, or '' if we're at root.
 * Used to build correct redirect paths regardless of which page calls auth.
 */
function getRoot() {
  return window.location.pathname.includes('/html/') ? '../' : '';
}
 
/**
 * Show an inline error message below a form.
 * Looks for an element with id="formError" (or the id you pass).
 *
 * Usage: showFormError('Invalid email or password');
 */
function showFormError(message, elementId = 'formError') {
  let el = document.getElementById(elementId);
  if (!el) {
    // Create it if it doesn't exist yet
    el = document.createElement('div');
    el.id = elementId;
    el.style.cssText = `
      color: #ef4444;
      font-size: 0.78rem;
      font-family: 'DM Mono', monospace;
      margin-top: 8px;
      padding: 8px 12px;
      background: rgba(239,68,68,0.08);
      border: 1px solid rgba(239,68,68,0.2);
      border-radius: 6px;
    `;
    // Append after the submit button if possible
    const submitBtn = document.querySelector('.form-submit');
    if (submitBtn) submitBtn.insertAdjacentElement('afterend', el);
    else document.body.appendChild(el);
  }
  el.textContent = message;
  el.style.display = 'block';
}
 
function clearFormError(elementId = 'formError') {
  const el = document.getElementById(elementId);
  if (el) el.style.display = 'none';
}