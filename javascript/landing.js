// MODAL CONTROLS
function openModal(tab) {
  document.getElementById('authModal').classList.add('active');
  switchTab(tab);
}

function closeModal() {
  document.getElementById('authModal').classList.remove('active');
}

function closeModalOnOverlay(e) {
  if (e.target === document.getElementById('authModal')) closeModal();
}

function switchTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('loginForm').style.display = isLogin ? 'block' : 'none';
  document.getElementById('signupForm').style.display = isLogin ? 'none' : 'block';
  document.getElementById('loginTab').classList.toggle('active', isLogin);
  document.getElementById('signupTab').classList.toggle('active', !isLogin);
  document.getElementById('modalTitle').textContent = isLogin ? 'WELCOME BACK' : 'GET STARTED';
  document.getElementById('modalSub').textContent = isLogin
    ? 'Sign in to your NarrativeIQ account'
    : 'Create your free account today';
}

// CLOSE MODAL ON ESC KEY
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// SCROLL FADE-IN ANIMATIONS
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) e.target.classList.add('visible');
  });
}, { threshold: 0.1 });

document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));
