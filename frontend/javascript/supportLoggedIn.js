// FAQ toggle
document.querySelectorAll(".faq-item").forEach(item => {

  item.addEventListener("click", () => {

    const answer = item.querySelector(".faq-answer");

    if (!answer) return;

    answer.style.display =
      answer.style.display === "block" ? "none" : "block";

  });

});


// Support form
const supportForm = document.getElementById("supportForm");

if (supportForm) {

  supportForm.addEventListener("submit", function(e){

    e.preventDefault();

    const status = document.getElementById("formStatus");

    if (status) {
      status.textContent =
        "Message sent! Our team will respond shortly.";
    }

    this.reset();

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