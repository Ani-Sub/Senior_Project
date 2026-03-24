const ctx = document.getElementById("riskChart");

new Chart(ctx,{
type:"bar",
data:{
labels:["Critical","High","Medium","Low","Verified"],
datasets:[{
label:"Creators",
data:[5,12,28,45,80],
backgroundColor:[
"#dc2626",
"#ea580c",
"#f59e0b",
"#84cc16",
"#10b981"
]
}]
},
options:{
plugins:{legend:{display:false}},
scales:{
x:{grid:{display:false}},
y:{grid:{color:"#1a2535"}}
}
}
});



const search=document.getElementById("creatorSearch");

search.addEventListener("input",()=>{

const term=search.value.toLowerCase();

document.querySelectorAll(".creator-card").forEach(card=>{

const name=card.dataset.name;

card.style.display=name.includes(term)?"block":"none";

});

});


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