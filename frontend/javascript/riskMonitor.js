const ITEMS_PER_PAGE = 6;
let currentPage = 1;

// DUMMY DATA (matches your DB: Channel = creator)
let creators = [
  { id: "channel_1", name: "TechWorld", handle: "@techworld", subs: "1.2M subscribers", risk: 72, violations: ["misinfo"] },
  { id: "channel_2", name: "Daily News Hub", handle: "@dailyhub", subs: "850K subscribers", risk: 45, violations: [] },
  { id: "channel_3", name: "ScienceDaily", handle: "@sciencedaily", subs: "2.1M subscribers", risk: 8, violations: [] },
  { id: "channel_4", name: "Crypto Vision", handle: "@cryptovision", subs: "640K subscribers", risk: 88, violations: ["scam", "misleading"] },
  { id: "channel_5", name: "World Trends", handle: "@worldtrends", subs: "1.5M subscribers", risk: 61, violations: [] },
  { id: "channel_6", name: "Insight Central", handle: "@insightcentral", subs: "430K subscribers", risk: 33, violations: [] },
  { id: "channel_7", name: "Truth Watch", handle: "@truthwatch", subs: "980K subscribers", risk: 79, violations: ["misinfo"] },
  { id: "channel_8", name: "Media Pulse", handle: "@mediapulse", subs: "720K subscribers", risk: 55, violations: [] },
  { id: "channel_9", name: "Global Scope", handle: "@globalscope", subs: "1.8M subscribers", risk: 67, violations: [] },
  { id: "channel_10", name: "Rapid Reports", handle: "@rapidreports", subs: "510K subscribers", risk: 41, violations: [] },
  { id: "channel_11", name: "Fact Checkers", handle: "@factcheck", subs: "2.4M subscribers", risk: 22, violations: [] },
  { id: "channel_12", name: "Trend Breakers", handle: "@trendbreakers", subs: "390K subscribers", risk: 74, violations: ["misleading"] },
  { id: "channel_13", name: "Echo Media", handle: "@echo_media", subs: "1.1M subscribers", risk: 69, violations: [] },
  { id: "channel_14", name: "Clarity News", handle: "@claritynews", subs: "870K subscribers", risk: 30, violations: [] },
  { id: "channel_15", name: "Insight Grid", handle: "@insightgrid", subs: "610K subscribers", risk: 53, violations: [] },
  { id: "channel_16", name: "Channel Watchdog", handle: "@watchdog", subs: "2.0M subscribers", risk: 91, violations: ["misinfo", "harmful"] },
  { id: "channel_17", name: "Narrative Lens", handle: "@narrativelens", subs: "480K subscribers", risk: 65, violations: [] },
  { id: "channel_18", name: "Reality Check", handle: "@realitycheck", subs: "760K subscribers", risk: 28, violations: [] },
  { id: "channel_19", name: "Stream Watchers", handle: "@streamwatch", subs: "1.3M subscribers", risk: 84, violations: ["misleading"] },
  { id: "channel_20", name: "Pulse Network", handle: "@pulsenet", subs: "590K subscribers", risk: 47, violations: [] }
];

let filteredCreators = [...creators];
// ── INIT ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // auth.requireAuth(); // optional

  // const dashboardId = getDashboardId();

  // FUTURE BACKEND WIRING
  /*
  creators = await fetchCreators(dashboardId);
  */

  renderAll();
  setupSearch();
});


// ── MAIN RENDER ──────────────────────────────────────────────
function renderAll() {
  renderCreators();
  renderStats();
  renderChart();
}


// ── FETCH (COMMENTED FOR NOW) ────────────────────────────────
async function fetchCreators(dashboardId) {
  // 1. Get channels tied to board
  const { data, error } = await api.get(`/dashboards/${dashboardId}/creators`);
  if (error) return [];

  // 2. Attach risk per creator
  const enriched = await Promise.all(
    data.map(async (c) => {
      const riskRes = await api.get(`/creators/${c.channel_id}/risk`);

      return {
        id: c.channel_id,
        name: c.channel_title,
        handle: "@unknown",
        subs: "—",
        risk: riskRes.data?.score || 0,
        violations: riskRes.data?.violations || []
      };
    })
  );

  return enriched;
}


// ── RENDER CREATORS ──────────────────────────────────────────
function renderCreators() {
  const container = document.getElementById("creatorList");

  // 🛑 safety check (prevents blank screen)
  if (!filteredCreators || filteredCreators.length === 0) {
    container.innerHTML = "<p>No creators found</p>";
    return;
  }

  const start = (currentPage - 1) * ITEMS_PER_PAGE;
  const paginated = filteredCreators.slice(start, start + ITEMS_PER_PAGE);

  container.innerHTML = paginated.map(c => creatorCardHTML(c)).join("");

  renderPagination();
}

function creatorCardHTML(c) {
  const level = getRiskLevel(c.risk);
  const initials = getInitials(c.name);

  if (!c.violations.length) {
    return `
      <div class="creator-card" data-name="${c.name.toLowerCase()}">
        <div class="creator-header">

          <div class="avatar">${initials}</div>

          <div class="creator-info">
            <h3>${c.name}</h3>
            <p>${c.handle} • ${c.subs}</p>
          </div>

          <div class="risk-score ${level}">
            ${c.risk}
            <span>Risk</span>
          </div>

        </div>

        <div class="verified">
          ✔ Verified creator — no violations detected
        </div>
      </div>
    `;
  }

  return `
    <div class="creator-card" data-name="${c.name.toLowerCase()}">
      <div class="creator-header">

        <div class="avatar">${initials}</div>

        <div class="creator-info">
          <h3>${c.name}</h3>
          <p>${c.handle} • ${c.subs}</p>
        </div>

        <div class="risk-score ${level}">
          ${c.risk}
          <span>Risk</span>
        </div>

      </div>

      <div class="violation-section">
        <div class="violation-title">⚠ Violations Detected</div>
        <div class="flags">
          ${c.violations.map(v => `<span class="flag">${v}</span>`).join("")}
        </div>
      </div>
    </div>
  `;
}


function renderPagination() {
  const container = document.getElementById("pagination");
  if (!container) return; // prevents crash if missing

  const totalPages = Math.ceil(filteredCreators.length / ITEMS_PER_PAGE);

  container.innerHTML = "";

  if (totalPages <= 1) return;

  for (let i = 1; i <= totalPages; i++) {
    const btn = document.createElement("button");
    btn.innerText = i;
    btn.style.color = "#c0c8d1";

    btn.className = "page-btn";

    if (i === currentPage) {
      btn.classList.add("active");
    }

    btn.onclick = () => {
      currentPage = i;
      renderCreators();
    };

    container.appendChild(btn);
  }

  // PREV BUTTON
  const prev = document.createElement("button");
  prev.innerText = "←";
  prev.className = "page-btn";
  prev.disabled = currentPage === 1;

  prev.onclick = () => {
    currentPage--;
    renderCreators();
  };

  container.appendChild(prev);

  // PAGE NUMBERS (your loop here)

  // NEXT BUTTON
  const next = document.createElement("button");
  next.innerText = "→";
  next.className = "page-btn";
  next.disabled = currentPage === totalPages;

  next.onclick = () => {
    currentPage++;
    renderCreators();
  };

  container.appendChild(next);
  
}
renderCreators();
prev.classList.add("nav");
next.classList.add("nav");

// ── STATS ───────────────────────────────────────────────────
function renderStats() {
  const high = creators.filter(c => c.risk >= 70).length;
  const review = creators.filter(c => c.risk >= 40 && c.risk < 70).length;
  const verified = creators.filter(c => c.risk < 20).length;

  document.getElementById("statHighRisk").textContent = high;
  document.getElementById("statReview").textContent = review;
  document.getElementById("statVerified").textContent = verified;
  document.getElementById("statTotal").textContent = creators.length;
}


// ── CHART ───────────────────────────────────────────────────
function renderChart() {
  const ctx = document.getElementById("riskChart");

  const buckets = {
    critical: creators.filter(c => c.risk >= 90).length,
    high: creators.filter(c => c.risk >= 70 && c.risk < 90).length,
    medium: creators.filter(c => c.risk >= 40 && c.risk < 70).length,
    low: creators.filter(c => c.risk >= 20 && c.risk < 40).length,
    safe: creators.filter(c => c.risk < 20).length
  };

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Critical", "High", "Medium", "Low", "Verified"],
      datasets: [{
        data: Object.values(buckets),
        backgroundColor: [
          "#dc2626",
          "#ea580c",
          "#f59e0b",
          "#84cc16",
          "#10b981"
        ]
      }]
    },
    options: {
      plugins: { legend: { display: false } }
    }
  });
}


// ── SEARCH ───────────────────────────────────────────────────
function setupSearch() {
  const search = document.getElementById("creatorSearch");

  search.addEventListener("input", () => {
    const term = search.value.toLowerCase();

    filteredCreators = creators.filter(c =>
      c.name.toLowerCase().includes(term) ||
      c.handle.toLowerCase().includes(term)
    );

    currentPage = 1; // reset to first page
    renderCreators();
  });
}


// ── HELPERS ──────────────────────────────────────────────────
function getRiskLevel(score) {
  if (score >= 90) return "critical";
  if (score >= 70) return "danger";
  if (score >= 40) return "warn";
  return "safe";
}

function getInitials(name = "") {
  return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
}

function getDashboardId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("id");
}


// ── SIDEBAR ──────────────────────────────────────────────────
function toggleUserMenu(e) {
  e.stopPropagation();
  const row = document.getElementById('userRow');
  const dropdown = document.getElementById('userDropdown');
  const isOpen = dropdown.classList.contains('open');
  closeUserMenu();
  if (!isOpen) {
    dropdown.classList.add('open');
    row.classList.add('open');
  }
}

function closeUserMenu() {
  document.getElementById('userDropdown')?.classList.remove('open');
  document.getElementById('userRow')?.classList.remove('open');
}

function handleLogout() {
  window.location.href = 'index.html';
}

document.addEventListener('click', () => closeUserMenu());
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeUserMenu();
});