// FAQ Toggle
document.querySelectorAll(".faq-item").forEach(item => {
  item.addEventListener("click", () => {
    const answer = item.querySelector(".faq-answer");
    answer.style.display =
      answer.style.display === "block" ? "none" : "block";
  });
});

// Fake submit handler
document.getElementById("supportForm")
  .addEventListener("submit", function(e){
    e.preventDefault();
    document.getElementById("formStatus").textContent =
      "Message sent! Our team will respond shortly.";
    this.reset();
  });