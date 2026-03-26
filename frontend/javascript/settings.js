
document.getElementById("updatePlanBtn").addEventListener("click", () => {
  document.getElementById("planStatus").textContent = "Plan updated successfully!";
});

document.getElementById("savePaymentBtn").addEventListener("click", () => {
  document.getElementById("paymentStatus").textContent = "Payment details saved!";
});

document.getElementById("saveSecurityBtn").addEventListener("click", () => {
  document.getElementById("securityStatus").textContent = "Security settings updated!";
});

document.getElementById("saveNotifBtn").addEventListener("click", () => {
  document.getElementById("notifStatus").textContent = "Notification preferences saved!";
});
