// Fade-in animation on scroll
const faders = document.querySelectorAll(".fade-in");

const appearOptions = {
  threshold: 0.2
};

const appearOnScroll = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    entry.target.classList.add("visible");
    observer.unobserve(entry.target);
  });
}, appearOptions);

faders.forEach(el => appearOnScroll.observe(el));

// Save profile (frontend only for now)
const saveBtn = document.getElementById("saveBtn");
const statusText = document.getElementById("saveStatus");

saveBtn.addEventListener("click", () => {
  const name = document.getElementById("fullName").value;
  const email = document.getElementById("email").value;

  document.getElementById("displayName").textContent = name;
  document.getElementById("displayEmail").textContent = email;

  statusText.textContent = "Profile updated successfully.";
});