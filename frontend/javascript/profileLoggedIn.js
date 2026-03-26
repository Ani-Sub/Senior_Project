// Fade-in animation
const faders = document.querySelectorAll(".fade-in");

if (faders.length > 0) {

  const observer = new IntersectionObserver(entries => {

    entries.forEach(entry => {

      if (!entry.isIntersecting) return;

      entry.target.classList.add("visible");

    });

  }, { threshold: 0.2 });

  faders.forEach(el => observer.observe(el));

}


// Save profile
const saveBtn = document.getElementById("saveBtn");

if (saveBtn) {

  saveBtn.addEventListener("click", () => {

    const name = document.getElementById("fullName").value;
    const email = document.getElementById("email").value;

    const displayName = document.getElementById("displayName");
    const displayEmail = document.getElementById("displayEmail");

    if (displayName) displayName.textContent = name;
    if (displayEmail) displayEmail.textContent = email;

    const sidebarName = document.querySelector(".user-name");
    const sidebarEmail = document.querySelector(".user-email");

    if (sidebarName) sidebarName.textContent = name;
    if (sidebarEmail) sidebarEmail.textContent = email;

    const statusText = document.getElementById("saveStatus");

    if (statusText) {
      statusText.textContent = "Profile updated successfully.";
    }

  });

}
//Bottom of Sidebar 
function toggleUserMenu(e) {
  e.stopPropagation();
  const row = document.getElementById('userRow');
  const dropdown = document.getElementById('userDropdown');
  const isOpen = dropdown.classList.contains('open');
  closeUserMenu();
  if (!isOpen) { dropdown.classList.add('open'); row.classList.add('open'); }
}

function closeUserMenu() {
  document.getElementById('userDropdown')?.classList.remove('open');
  document.getElementById('userRow')?.classList.remove('open');
}

function handleLogout() { window.location.href = 'index.html'; }

document.addEventListener('click', () => closeUserMenu());
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeUserMenu(); });