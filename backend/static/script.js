const API = window.location.origin; // http://127.0.0.1:5000

let currentUserId = null;
let currentUsername = null;

// ---------- AUTH ----------
async function registerUser(){
  const username = document.getElementById("reg-username").value.trim();
  const password = document.getElementById("reg-password").value.trim();
  const msg = document.getElementById("auth-msg");
  msg.textContent = "";

  if(!username || !password){ msg.textContent = "Enter username & password"; return; }

  try{
    const res = await fetch(`${API}/register`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    msg.textContent = data.message || (res.ok ? "Registered" : "Error");
  }catch(e){
    msg.textContent = "Server error";
    console.error(e);
  }
}

async function loginUser(){
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const msg = document.getElementById("auth-msg");
  msg.textContent = "";

  if(!username || !password){ msg.textContent = "Enter username & password"; return; }

  try{
    const res = await fetch(`${API}/login`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if(res.ok && data.user_id){
      currentUserId = data.user_id;
      currentUsername = username;
      document.getElementById("welcome-msg").innerText = `Welcome, ${currentUsername}!`;
      document.getElementById("auth-section").classList.add("hidden");
      document.getElementById("recipe-section").classList.remove("hidden");
      loadMyRecipes();
    } else {
      msg.textContent = data.message || "Invalid credentials";
    }
  }catch(e){
    msg.textContent = "Server error";
    console.error(e);
  }
}

function logoutUser(){
  currentUserId = null;
  currentUsername = null;
  document.getElementById("recipe-section").classList.add("hidden");
  document.getElementById("auth-section").classList.remove("hidden");
}

// ---------- IMAGE HELP ----------
function readFileAsDataURL(file){
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = reject;
    fr.readAsDataURL(file);
  });
}

document.getElementById("recipe-image").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  const wrap = document.getElementById("preview-wrap");
  const img = document.getElementById("preview-img");
  if(!file){ wrap.classList.add("hidden"); img.src = ""; return; }
  try{
    const dataUrl = await readFileAsDataURL(file);
    img.src = dataUrl;
    wrap.classList.remove("hidden");
  }catch(err){
    console.error("Image read error", err);
  }
});

// ---------- ADD RECIPE ----------
async function addRecipe(){
  if(!currentUserId){ alert("Login required"); return; }
  const title = document.getElementById("recipe-title").value.trim();
  const description = document.getElementById("recipe-desc").value.trim();
  if(!title){ alert("Add a title"); return; }

  // read image if provided
  const fileInput = document.getElementById("recipe-image");
  let image_base64 = null;
  if(fileInput.files[0]){
    try {
      image_base64 = await readFileAsDataURL(fileInput.files[0]); // data URL
    } catch(err){
      console.error("Failed to read image", err);
    }
  }

  try{
    const res = await fetch(`${API}/add_recipe`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        title,
        description,
        owner_id: currentUserId,
        image_base64
      })
    });
    const data = await res.json();
    alert(data.message || (res.ok ? "Added" : "Error"));
    // clear form
    document.getElementById("recipe-title").value = "";
    document.getElementById("recipe-desc").value = "";
    document.getElementById("recipe-image").value = "";
    document.getElementById("preview-wrap").classList.add("hidden");
    // reload list
    loadMyRecipes();
  }catch(err){
    console.error(err);
    alert("Server error");
  }
}

// ---------- LOAD ALL RECIPES ----------
async function loadAllRecipes(){
  try{
    const res = await fetch(`${API}/recipes`);
    const list = await res.json();
    renderRecipes(list, false);
  }catch(err){
    console.error(err);
    alert("Could not load recipes");
  }
}

// ---------- LOAD MY RECIPES ----------
async function loadMyRecipes(){
  if(!currentUserId){ alert("Login required"); return; }
  try{
    const res = await fetch(`${API}/my_recipes/${currentUserId}`);
    const list = await res.json();
    renderRecipes(list, true);
  }catch(err){
    console.error(err);
    alert("Could not load your recipes");
  }
}

// ---------- RENDER ----------
function renderRecipes(items, ownerView = false){
  const container = document.getElementById("recipes");
  container.innerHTML = "";
  if(!items || items.length === 0){ container.innerHTML = "<p class='muted'>No recipes found.</p>"; return; }

  items.forEach(it => {
    const card = document.createElement("div");
    card.className = "recipe-card";
    const imgHtml = it.image_base64 ? `<img class="recipe-img" src="${it.image_base64}" alt="">` : "";
    const ownerLine = it.owner ? `<div class="meta">By: ${escapeHtml(it.owner)}</div>` : "";
    const actions = ownerView ? `
      <div class="actions">
        <button class="btn outline" onclick="showEdit(${it.id}, '${escapeJs(it.title)}', '${escapeJs(it.description)}')">Edit</button>
        <button class="btn" onclick="deleteRecipe(${it.id})">Delete</button>
      </div>` : "";

    card.innerHTML = `
      <h4>${escapeHtml(it.title)}</h4>
      ${ownerLine}
      ${imgHtml}
      <p>${escapeHtml(it.description)}</p>
      ${actions}
    `;
    container.appendChild(card);
  });
}

// ---------- EDIT / DELETE ----------
function escapeJs(s){ return (s||"").replace(/'/g, "\\'").replace(/\n/g,"\\n"); }
function escapeHtml(s){ if(!s) return ""; return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

function showEdit(id, oldTitle, oldDesc){
  const title = prompt("Edit title:", oldTitle);
  if(title === null) return;
  const desc = prompt("Edit description:", oldDesc);
  if(desc === null) return;
  editRecipe(id, title, desc);
}

async function editRecipe(id, title, description){
  try{
    const res = await fetch(`${API}/edit_recipe/${id}/${currentUserId}`, {
      method: "PUT",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ title, description }) // not changing image here
    });
    const data = await res.json();
    alert(data.message || "Updated");
    loadMyRecipes();
  }catch(err){
    console.error(err);
    alert("Server error");
  }
}

async function deleteRecipe(id){
  if(!confirm("Delete this recipe?")) return;
  try{
    const res = await fetch(`${API}/delete_recipe/${id}/${currentUserId}`, { method: "DELETE" });
    const data = await res.json();
    alert(data.message || "Deleted");
    loadMyRecipes();
  }catch(err){
    console.error(err);
    alert("Server error");
  }
}
