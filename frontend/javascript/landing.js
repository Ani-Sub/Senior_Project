/*
  * Handles the login/signup model on index.html.
  * If the user is already logged in, redirects to home.
  * Otherwise, shows the login/signup form and handles its submission.
  * Depends on api.js for the authActions.login and authActions.register functions.
  * NOTE: This is intentionally separate from dashboard.js to avoid loading authActions on every page.
  *       If you find yourself needing authActions on another page, consider moving it to a shared file.
 */

// Skip the landing page if the user is already logged in
document.addEventListener('DOMContentLoaded', () => {
  auth.redirectIfLoggedIn();
});

// -- Modal Controls --

// Opens the auth modal and switches to the specified tab (login or signup).
function openModal(tab) {
  document.getElementById('authModal').classList.add('active');
  switchTab(tab);
  clearFormError();
}

// Closes the auth modal.
function closeModal() {
  document.getElementById('authModal').classList.remove('active');
  clearFormError();
}

// Close modal on overlay click
function closeModalOnOverlay(e) {
  if (e.target == document.getElementById('authModal')) {
    closeModal();
  }
}

// switches between login and signup tabs in the modal, updating the form and text accordingly.
function switchTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('loginForm').style.display  = isLogin ? 'block' : 'none';
  document.getElementById('signupForm').style.display = isLogin ? 'none'  : 'block';
  document.getElementById('loginTab').classList.toggle('active',  isLogin);
  document.getElementById('signupTab').classList.toggle('active', !isLogin);
  document.getElementById('modalTitle').textContent = isLogin ? 'WELCOME BACK' : 'GET STARTED';
  document.getElementById('modalSub').textContent   = isLogin
    ? 'Sign in to your NarrativeIQ account'
    : 'Create your free account today';
  clearFormError();
}
 
// closes the modal
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});
 
// ── LOGIN ─────────────────────────────────────────────────────
 
async function handleLogin() {
  const email    = document.querySelector('#loginForm input[type="email"]').value.trim();
  const password = document.querySelector('#loginForm input[type="password"]').value;
  const btn      = document.querySelector('#loginForm .form-submit');
 
  clearFormError();
 
  if (!email || !password) {
    showFormError('Please enter your email and password.');
    return;
  }
 
  setButtonLoading(btn, true, 'Logging in...');
 
  const { data, error } = await authActions.login(email, password);
 
  setButtonLoading(btn, false, 'Log In →');
 
  if (error) {
    showFormError(error);
    return;
  }
 
  // Redirect to app home on success
  window.location.href = 'html/home.html';
}
 
// ── REGISTER ──────────────────────────────────────────────────
 
async function handleRegister() {
  const name     = document.querySelector('#signupForm input[type="text"]').value.trim();
  const email    = document.querySelector('#signupForm input[type="email"]').value.trim();
  const password = document.querySelector('#signupForm input[type="password"]').value;
  const btn      = document.querySelector('#signupForm .form-submit');
 
  clearFormError();
 
  if (!name || !email || !password) {
    showFormError('Please fill in all fields.');
    return;
  }
 
  if (password.length < 8) {
    showFormError('Password must be at least 8 characters.');
    return;
  }
 
  setButtonLoading(btn, true, 'Creating account...');
 
  const { data, error } = await authActions.register(name, email, password);
 
  setButtonLoading(btn, false, 'Create Account →');
 
  if (error) {
    showFormError(error);
    return;
  }
 
  window.location.href = 'html/home.html';
}
 
// ── WIRE SUBMIT BUTTONS ───────────────────────────────────────
// Replace static buttons in index.html with JS-driven ones.
// This runs after DOMContentLoaded so the DOM is ready.
 
document.addEventListener('DOMContentLoaded', () => {
  const loginBtn  = document.querySelector('#loginForm .form-submit');
  const signupBtn = document.querySelector('#signupForm .form-submit');
 
  if (loginBtn)  loginBtn.addEventListener('click', handleLogin);
  if (signupBtn) signupBtn.addEventListener('click', handleRegister);
 
  // Also allow Enter key submission
  document.querySelector('#loginForm')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') handleLogin();
  });
  document.querySelector('#signupForm')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') handleRegister();
  });
});
 
// ── BUTTON LOADING STATE ──────────────────────────────────────
 
function setButtonLoading(btn, isLoading, label) {
  if (!btn) return;
  btn.disabled = isLoading;
  btn.textContent = label;
  btn.style.opacity = isLoading ? '0.7' : '1';
}
 
// ── SCROLL FADE-IN ANIMATIONS ─────────────────────────────────
 
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) e.target.classList.add('visible');
  });
}, { threshold: 0.1 });
 
document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));