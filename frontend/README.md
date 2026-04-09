# NarrativeIQ — Frontend

The frontend for **NarrativeIQ**, an AI-powered intelligence platform that extracts, clusters, and monitors claims and narratives from YouTube content.

---

## Overview

NarrativeIQ's frontend is a vanilla HTML/CSS/JavaScript multi-page application (MPA). No build step or framework is required — open the files directly in a browser or serve them from a static file server.

---

## Project Structure

```
frontend/
├── index.html              # Landing page (unauthenticated entry point)
├── css/
│   ├── landing.css         # Landing page styles
│   ├── home.css            # Home/feed page styles
│   ├── dashboard.css       # Main analytics dashboard styles
│   ├── narratives.css      # Narratives explorer styles
│   ├── claims.css          # Claims browser styles
│   ├── trends.css          # Trend analysis styles
│   ├── riskMonitor.css     # Creator risk monitor styles
│   ├── profile.css         # Public profile styles
│   ├── profileLoggedIn.css # Authenticated user profile styles
│   ├── support.css         # Help center styles (public)
│   └── supportLoggedIn.css # Help center styles (authenticated)
├── html/
│   ├── home.html           # Post-login home/feed page
│   ├── dashboard.html      # Analytics dashboard (charts, claims, narratives)
│   ├── narratives.html     # Narrative clustering explorer
│   ├── claims.html         # Individual claims browser
│   ├── trends.html         # Temporal trend analysis
│   ├── riskMonitor.html    # Creator risk assessment
│   ├── profileLoggedIn.html# Authenticated user profile & settings
│   ├── support.html        # Help center (public)
│   └── supportLoggedIn.html# Help center (authenticated)
└── javascript/
    ├── api.js              # Core API layer (shared across all pages)
    ├── landing.js          # Landing page logic (auth modal, login/signup)
    ├── home.js             # Home page logic
    ├── dashboard.js        # Dashboard charts and data rendering
    ├── narratives.js       # Narratives page logic
    ├── claims.js           # Claims browser logic
    ├── trends.js           # Trend charts and filters
    ├── riskMonitor.js      # Creator risk scoring UI
    ├── profileLoggedIn.js  # Profile page logic
    ├── support.js          # Help center logic (public)
    └── supportLoggedIn.js  # Help center logic (authenticated)
```

---

## Pages

| Page | File | Auth Required |
|---|---|---|
| Landing | `index.html` | No |
| Home / Feed | `html/home.html` | Yes |
| Dashboard | `html/dashboard.html` | Yes |
| Narratives | `html/narratives.html` | Yes |
| Claims | `html/claims.html` | Yes |
| Trends | `html/trends.html` | Yes |
| Risk Monitor | `html/riskMonitor.html` | Yes |
| Profile | `html/profileLoggedIn.html` | Yes |
| Help Center | `html/support.html` | No |
| Help Center | `html/supportLoggedIn.html` | Yes |

---

## API Layer (`javascript/api.js`)

All backend communication goes through `api.js`, which is loaded on every page. It exposes three global objects:

### `auth` — Session management

```js
auth.saveSession(token, user)  // Store JWT + user in localStorage
auth.clearSession()            // Remove JWT + user from localStorage
auth.getToken()                // Returns raw JWT string or null
auth.getUser()                 // Returns parsed user object or null
auth.isLoggedIn()              // Returns true if a token exists
auth.requireAuth()             // Redirects to landing if not logged in
auth.redirectIfLoggedIn()      // Redirects to home if already logged in
```

Call `auth.requireAuth()` at the top of `DOMContentLoaded` on every protected page.

### `api` — HTTP methods

```js
api.get(path, opts)          // GET  /api/v1{path}
api.post(path, body, opts)   // POST /api/v1{path}
api.patch(path, body, opts)  // PATCH /api/v1{path}
api.delete(path, opts)       // DELETE /api/v1{path}
```

All methods return `{ data, error, status }` and never throw. Pass `{ noAuth: true }` in `opts` to skip the `Authorization` header (used for login/signup).

### `authActions` — High-level auth helpers

```js
authActions.login(email, password)        // POST /auth/login, saves session
authActions.register(name, email, password) // POST /auth/signup, saves session
authActions.logout()                      // Clears session, redirects to landing
```

### Utility functions

```js
hydrateUserSidebar()           // Fills #userAvatar, #userName, #userEmail from localStorage
getInitials(name)              // "Animesh Subedi" → "AS"
showFormError(message, id?)    // Renders inline form error
clearFormError(id?)            // Hides inline form error
```

---

## Backend Connection

The frontend expects the backend API to be running at:

```
http://localhost:8000/api/v1
```

This is set at the top of `api.js`:

```js
const API_BASE = "http://localhost:8000/api/v1";
```

If the backend is unreachable, all `api.*` calls will return:
```js
{ data: null, error: "Cannot reach the server. Is the backend running?", status: 0 }
```

---

## Running Locally

No build step required. Serve the `frontend/` directory from any static file server.

**Using Python:**
```bash
cd frontend
python -m http.server 3000
```
Then open `http://localhost:3000` in your browser.

**Using Node (`serve`):**
```bash
npx serve frontend
```

> **Note:** The backend must be running separately on port `8000` for API calls to work. See the backend README for setup instructions.

---

## Authentication Flow

1. User visits `index.html` (landing page).
2. User clicks **Log In** or **Get Started** — an auth modal opens.
3. On successful login/signup, the backend returns `{ token, user }`.
4. `authActions.login()` / `authActions.register()` stores both in `localStorage`.
5. User is redirected to `html/home.html`.
6. All subsequent protected pages call `auth.requireAuth()` on load and attach `Authorization: Bearer <token>` to every API request automatically.
7. A `401` response from the backend auto-clears the session and redirects to the landing page.

---

## Dependencies

All dependencies are loaded via CDN — no `npm install` required.

| Library | Version | Used in |
|---|---|---|
| [Chart.js](https://www.chartjs.org/) | 4.4.0 | `dashboard.html`, `trends.html` |
| Google Fonts (Bebas Neue, DM Sans, DM Mono) | — | All pages |

---

## Pricing Tiers

| Plan | Price | Channels | Claims |
|---|---|---|---|
| Free | $0/mo | 5 | 100/mo |
| Analyst | $49/mo | 20 | Unlimited |
| Enterprise | $199/mo | Unlimited | Unlimited |
