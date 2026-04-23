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
