const PLANS = {
  free:       { name: 'Free',       limit: 1  },
  analyst:    { name: 'Analyst',    limit: 5  },
  enterprise: { name: 'Enterprise', limit: Infinity }
};

// Simulated current user — swap this with real auth data from your backend
const CURRENT_USER = {
  name: 'Animesh Subedi',
  email: 'animesh@example.com',
  initials: 'AS',
  plan: 'analyst'   // 'free' | 'analyst' | 'enterprise'
};

// ── INIT ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById("currentPlan");
  console.log("currentPlan element:", el);
  if (el) {
    el.textContent = `Current Plan: ${PLANS[CURRENT_USER.plan].name}`;
  } else {
    console.warn("currentPlan element not found!");
  }
});




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




