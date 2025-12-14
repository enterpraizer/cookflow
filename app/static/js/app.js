const CookFlow = (() => {
  let currentUser = null;

  // -----------------------------
  // UI helpers
  // -----------------------------
  function showFlash(msg, type = "info") {
    const el = document.getElementById("flash");
    if (!el) return;
    el.classList.remove("hidden");
    el.classList.remove("flash-info", "flash-error", "flash-ok");
    el.classList.add(type === "error" ? "flash-error" : type === "ok" ? "flash-ok" : "flash-info");
    el.textContent = msg;
    setTimeout(() => el.classList.add("hidden"), 3500);
  }

  function escapeHtml(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || null;
  }

  async function apiFetch(url, options = {}) {
    const opts = {
      headers: {
        ...(options.headers || {}),
      },
      credentials: options.credentials || "same-origin",
      ...options,
    };

    const method = (opts.method || "GET").toUpperCase();

    // JSON body helper
    if (opts.body && typeof opts.body === "string") {
      opts.headers["Content-Type"] = "application/json";
    }

    // CSRF for unsafe methods (AJAX pattern) [web:21]
    const csrf = getCsrfToken();
    if (csrf && !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
      opts.headers["X-CSRFToken"] = csrf;
    }

    const res = await fetch(url, opts);
    const json = await res.json().catch(() => null);

    if (!res.ok) {
      const msg = json?.error?.message || "Ошибка запроса";
      const code = json?.error?.code || "HTTP_ERROR";
      showFlash(`${msg} (${code})`, "error");
      throw new Error(msg);
    }

    if (json && json.ok === false) {
      const msg = json?.error?.message || "Ошибка";
      const code = json?.error?.code || "API_ERROR";
      showFlash(`${msg} (${code})`, "error");
      throw new Error(msg);
    }

    return json?.data ?? json;
  }

  // -----------------------------
  // Auth
  // -----------------------------
  async function getCurrentUser() {
    const data = await apiFetch("/api/auth/user", { method: "GET" });
    currentUser = data.user;
    return currentUser;
  }

  async function initAuthUI() {
    await getCurrentUser();

    const badge = document.getElementById("userBadge");
    const loginLink = document.getElementById("loginLink");
    const registerLink = document.getElementById("registerLink");
    const logoutBtn = document.getElementById("logoutBtn");

    if (!badge || !loginLink || !registerLink || !logoutBtn) return;

    if (currentUser) {
      badge.classList.remove("hidden");
      badge.textContent = currentUser.name;
      loginLink.classList.add("hidden");
      registerLink.classList.add("hidden");
      logoutBtn.classList.remove("hidden");

      logoutBtn.onclick = async () => {
        await logout();
        window.location.href = "/";
      };
    } else {
      badge.classList.add("hidden");
      loginLink.classList.remove("hidden");
      registerLink.classList.remove("hidden");
      logoutBtn.classList.add("hidden");
    }
  }

  async function register(name, email, password) {
    await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    showFlash("Аккаунт создан", "ok");
    await initAuthUI();
  }

  async function login(email, password) {
    await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    showFlash("Вход выполнен", "ok");
    await initAuthUI();
  }

  async function logout() {
    await apiFetch("/api/auth/logout", { method: "POST" });
    showFlash("Вы вышли", "ok");
    await initAuthUI();
  }

  // -----------------------------
  // Recipe cards + lists
  // -----------------------------
  function recipeCard(r) {
    const img = r.image_url ? `<img class="card-img" src="${r.image_url}" alt="">` : "";
    const diff = r.difficulty ? `<span class="pill">${escapeHtml(r.difficulty)}</span>` : "";
    const time = r.cooking_time ? `<span class="pill">${escapeHtml(r.cooking_time)} мин</span>` : "";
    return `
      <a class="card" href="/recipe/${r.id}">
        ${img}
        <div class="card-body">
          <div class="row row-between">
            <h3 class="card-title">${escapeHtml(r.title)}</h3>
            <span class="muted">${escapeHtml(r.author?.name || "")}</span>
          </div>
          <div class="row">${diff}${time}</div>
        </div>
      </a>
    `;
  }

  let recipesPage = 1;
  const perPage = 12;

  async function loadRecipes() {
    const data = await apiFetch(`/api/recipes?page=${recipesPage}&per_page=${perPage}`, { method: "GET" });
    const grid = document.getElementById("recipesGrid");
    if (grid) grid.innerHTML = (data.items || []).map(recipeCard).join("");

    const pageInfo = document.getElementById("pageInfo");
    const prev = document.getElementById("prevPage");
    const next = document.getElementById("nextPage");

    if (pageInfo) pageInfo.textContent = `Страница ${data.page} из ${data.pages}`;
    if (prev) prev.disabled = data.page <= 1;
    if (next) next.disabled = data.page >= data.pages;

    if (prev && !prev.dataset.bound) {
      prev.dataset.bound = "1";
      prev.addEventListener("click", async () => {
        recipesPage = Math.max(1, recipesPage - 1);
        await loadRecipes();
      });
    }
    if (next && !next.dataset.bound) {
      next.dataset.bound = "1";
      next.addEventListener("click", async () => {
        recipesPage = recipesPage + 1;
        await loadRecipes();
      });
    }
  }

  async function searchRecipes(q) {
    if (!q) return loadRecipes();
    const data = await apiFetch(`/api/recipes/search?q=${encodeURIComponent(q)}`, { method: "GET" });
    const grid = document.getElementById("recipesGrid");
    if (grid) grid.innerHTML = (data.items || []).map(recipeCard).join("");

    const pageInfo = document.getElementById("pageInfo");
    if (pageInfo) pageInfo.textContent = `Найдено: ${(data.items || []).length}`;
  }

  // -----------------------------
  // Recipe detail
  // -----------------------------
  async function loadRecipe(id) {
    const r = await apiFetch(`/api/recipes/${id}`, { method: "GET" });

    const header = document.getElementById("recipeHeader");
    if (header) {
      header.innerHTML = `
        <div class="row row-between">
          <h1>${escapeHtml(r.title)}</h1>
          ${r.is_saved ? `<span class="pill pill-ok"><i class="fa-solid fa-bookmark"></i> В избранном</span>` : ""}
        </div>
        ${r.image_url ? `<img class="hero-img" src="${r.image_url}" alt="">` : ""}
        <p class="muted">${escapeHtml(r.description || "")}</p>
      `;
    }

    const ing = document.getElementById("ingredientsList");
    if (ing) {
      ing.innerHTML = (r.ingredients || [])
        .map(i => `<li>${escapeHtml(i.name)} ${i.quantity ? `— <span class="muted">${escapeHtml(i.quantity)}</span>` : ""}</li>`)
        .join("");
    }

    const steps = document.getElementById("stepsList");
    if (steps) {
      steps.innerHTML = (r.steps || [])
        .map(s => {
          const t = s.timer_seconds ? ` <span class="pill">${escapeHtml(s.timer_seconds)} сек</span>` : "";
          return `<li>${escapeHtml(s.description)}${t}</li>`;
        })
        .join("");
    }

    const saveBtn = document.getElementById("toggleSaveBtn");
    if (saveBtn) {
      saveBtn.innerHTML = r.is_saved
        ? `<i class="fa-solid fa-bookmark"></i> Убрать из избранного`
        : `<i class="fa-regular fa-bookmark"></i> В избранное`;
    }

    // show edit button for owner
    const editBtn = document.getElementById("editRecipeBtn");
    if (editBtn) {
      await getCurrentUser();
      if (currentUser && r.author?.id === currentUser.id) {
        editBtn.classList.remove("hidden");
        editBtn.onclick = () => window.location.href = `/recipe/${id}/edit`;
      } else {
        editBtn.classList.add("hidden");
      }
    }

    return r;
  }

  async function toggleSaveRecipe(id) {
    await getCurrentUser();
    if (!currentUser) throw new Error("Not logged in");

    const r = await apiFetch(`/api/recipes/${id}`, { method: "GET" });
    if (r.is_saved) {
      await apiFetch(`/api/recipes/${id}/save`, { method: "DELETE" });
      showFlash("Удалено из избранного", "ok");
    } else {
      await apiFetch(`/api/recipes/${id}/save`, { method: "POST" });
      showFlash("Сохранено", "ok");
    }
  }

  async function loadSavedRecipes() {
    const data = await apiFetch("/api/recipes/my", { method: "GET" });
    const grid = document.getElementById("savedGrid");
    if (grid) grid.innerHTML = (data.items || []).map(recipeCard).join("");
  }

  async function loadMyAuthoredRecipes() {
    const data = await apiFetch("/api/recipes/mine", { method: "GET" });
    const grid = document.getElementById("myAuthoredGrid");
    if (grid) grid.innerHTML = (data.items || []).map(recipeCard).join("");
  }

  // -----------------------------
  // Comments
  // -----------------------------
  async function loadComments(recipeId) {
    const data = await apiFetch(`/api/recipes/${recipeId}/comments`, { method: "GET" });
    const list = document.getElementById("commentsList");
    if (!list) return;

    const items = data.items || [];
    list.innerHTML = items.length
      ? items.map(c => `
          <div class="comment">
            <div class="row row-between">
              <strong>${escapeHtml(c.user.name)}</strong>
              <span class="muted">${new Date(c.created_at).toLocaleString("ru-RU")}</span>
            </div>
            <div>${escapeHtml(c.text)}</div>
          </div>
        `).join("")
      : `<div class="muted">Пока нет комментариев</div>`;
  }

  async function addComment(recipeId, text) {
    if (!text) {
      showFlash("Введите текст комментария", "error");
      return;
    }
    await apiFetch(`/api/recipes/${recipeId}/comments`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    showFlash("Комментарий добавлен", "ok");
  }

  // -----------------------------
  // Challenges
  // -----------------------------
  async function loadChallenges() {
    const data = await apiFetch("/api/challenges", { method: "GET" });

    const grid = document.getElementById("challengesGrid");
    if (grid) {
      grid.innerHTML = (data.items || []).map(ch => {
        const cat = ch.category ? `Категория: ${escapeHtml(ch.category.name)}` : "Категория: любая";
        const target = ch.target_count ? `Цель: ${escapeHtml(ch.target_count)}` : "Цель: не задана";
        return `
          <div class="card">
            <div class="card-body">
              <h3 class="card-title">${escapeHtml(ch.title)}</h3>
              <p class="muted">${escapeHtml(ch.description || "")}</p>
              <div class="muted">${cat}</div>
              <div class="muted">${target}</div>
              <button class="btn" data-start="${ch.id}"><i class="fa-solid fa-flag-checkered"></i> Начать</button>
            </div>
          </div>
        `;
      }).join("");

      grid.querySelectorAll("[data-start]").forEach(btn => {
        btn.addEventListener("click", async () => {
          await apiFetch(`/api/challenges/${btn.dataset.start}/start`, { method: "POST" });
          showFlash("Челлендж начат", "ok");
          await loadMyChallenges();
        });
      });
    }

    await loadMyChallenges();
  }

  async function loadMyChallenges() {
    const box = document.getElementById("myChallenges");
    if (!box) return;

    await getCurrentUser();
    if (!currentUser) {
      box.innerHTML = `<div class="muted">Войдите, чтобы видеть прогресс.</div>`;
      return;
    }

    const data = await apiFetch("/api/challenges/my", { method: "GET" });
    const items = data.items || [];

    box.innerHTML = items.length
      ? items.map(p => {
          const t = p.target_count || 0;
          const done = p.completed_count || 0;
          const percent = t > 0 ? Math.min(100, Math.round(done * 100 / t)) : 0;
          return `
            <div class="card">
              <div class="card-body">
                <div class="row row-between">
                  <div>
                    <div><strong>${escapeHtml(p.challenge.title)}</strong></div>
                    <div class="muted">Прогресс: ${escapeHtml(done)}${t ? " / " + escapeHtml(t) : ""}</div>
                  </div>
                  <button class="btn btn-outline" data-plus="${p.challenge.id}">+1</button>
                </div>
                ${t ? `<div class="progress"><div class="progress-bar" style="width:${percent}%"></div></div>` : ""}
              </div>
            </div>
          `;
        }).join("")
      : `<div class="muted">Нет активных челленджей.</div>`;

    box.querySelectorAll("[data-plus]").forEach(btn => {
      btn.addEventListener("click", async () => {
        await apiFetch(`/api/challenges/${btn.dataset.plus}/progress`, {
          method: "POST",
          body: JSON.stringify({ delta: 1 })
        });
        await loadMyChallenges();
      });
    });
  }

  // -----------------------------
  // Uploads (for step images and also recipe image in edit)
  // -----------------------------
  async function uploadStepImage(file) {
    const fd = new FormData();
    fd.append("file", file);

    const csrf = getCsrfToken();
    const res = await fetch("/api/uploads/image", {
      method: "POST",
      body: fd,
      credentials: "same-origin",
      headers: csrf ? { "X-CSRFToken": csrf } : {}
    });

    const json = await res.json().catch(() => null);
    if (!res.ok) {
      const msg = json?.error?.message || "Ошибка загрузки";
      const code = json?.error?.code || "HTTP_ERROR";
      showFlash(`${msg} (${code})`, "error");
      throw new Error(msg);
    }
    return json.data.url;
  }

  // -----------------------------
  // Add recipe form
  // -----------------------------
  function ingredientRowPrefill(name = "", qty = "") {
    const div = document.createElement("div");
    div.className = "row";
    div.innerHTML = `
      <input class="input ing-name" placeholder="Ингредиент" required>
      <input class="input ing-qty" placeholder="Количество">
      <button type="button" class="btn btn-outline ing-del"><i class="fa-solid fa-trash"></i></button>
    `;
    div.querySelector(".ing-name").value = name;
    div.querySelector(".ing-qty").value = qty;
    div.querySelector(".ing-del").addEventListener("click", () => div.remove());
    return div;
  }

  function stepRowPrefill(desc = "", timer = 0, imageUrl = "") {
    const div = document.createElement("div");
    div.className = "card";
    div.style.padding = "12px";
    div.innerHTML = `
      <textarea class="textarea step-desc" placeholder="Описание шага" required></textarea>
      <div class="row">
        <input class="input step-timer" type="number" min="0" placeholder="Таймер (сек)">
        <input class="input step-image-url" placeholder="URL картинки шага (или загрузите файл)">
        <input class="input step-image-file" type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp">
      </div>
      <button type="button" class="btn btn-outline step-del"><i class="fa-solid fa-trash"></i> Удалить шаг</button>
    `;
    div.querySelector(".step-desc").value = desc;
    div.querySelector(".step-timer").value = String(timer || 0);
    div.querySelector(".step-image-url").value = imageUrl || "";
    div.querySelector(".step-del").addEventListener("click", () => div.remove());
    return div;
  }

  async function createRecipeMultipart(payload, file) {
    const fd = new FormData();
    fd.append("data", JSON.stringify(payload));
    if (file) fd.append("image", file);

    const csrf = getCsrfToken();
    const res = await fetch("/api/recipes", {
      method: "POST",
      body: fd,
      credentials: "same-origin",
      headers: csrf ? { "X-CSRFToken": csrf } : {}
    });

    const json = await res.json().catch(() => null);
    if (!res.ok) {
      const msg = json?.error?.message || "Ошибка создания рецепта";
      const code = json?.error?.code || "HTTP_ERROR";
      showFlash(`${msg} (${code})`, "error");
      throw new Error(msg);
    }
    return json.data;
  }

  function recipeFormInit() {
    const ingBox = document.getElementById("ingredientsBox");
    const stepsBox = document.getElementById("stepsBox");
    const addIngredientBtn = document.getElementById("addIngredientBtn");
    const addStepBtn = document.getElementById("addStepBtn");

    if (!ingBox || !stepsBox || !addIngredientBtn || !addStepBtn) return;

    ingBox.innerHTML = "";
    stepsBox.innerHTML = "";

    ingBox.appendChild(ingredientRowPrefill());
    stepsBox.appendChild(stepRowPrefill());

    addIngredientBtn.addEventListener("click", () => ingBox.appendChild(ingredientRowPrefill()));
    addStepBtn.addEventListener("click", () => stepsBox.appendChild(stepRowPrefill()));

    document.getElementById("recipeForm").addEventListener("submit", async (e) => {
      e.preventDefault();

      await getCurrentUser();
      if (!currentUser) {
        showFlash("Нужно войти, чтобы создать рецепт", "error");
        window.location.href = "/login";
        return;
      }

      const title = document.getElementById("title").value.trim();
      if (!title) return showFlash("Название обязательно", "error");

      const description = document.getElementById("description").value.trim();
      const cooking_time = parseInt(document.getElementById("cooking_time").value || "0", 10) || null;
      const servings = parseInt(document.getElementById("servings").value || "0", 10) || null;
      const difficulty = document.getElementById("difficulty").value || null;
      const file = document.getElementById("image").files[0] || null;

      const ingredients = [...ingBox.querySelectorAll(".row")]
        .map((row, idx) => ({
          order: idx + 1,
          name: row.querySelector(".ing-name").value.trim(),
          quantity: row.querySelector(".ing-qty").value.trim()
        }))
        .filter(i => i.name);

      const stepCards = [...stepsBox.querySelectorAll(".card")];
      const steps = [];
      for (let idx = 0; idx < stepCards.length; idx++) {
        const card = stepCards[idx];
        const description = card.querySelector(".step-desc").value.trim();
        if (!description) continue;

        let image_url = card.querySelector(".step-image-url").value.trim();
        const f = card.querySelector(".step-image-file")?.files?.[0] || null;
        if (f) image_url = await uploadStepImage(f);

        steps.push({
          order: idx + 1,
          description,
          timer_seconds: parseInt(card.querySelector(".step-timer").value || "0", 10) || 0,
          image_url
        });
      }

      const cats = (document.getElementById("categories").value || "")
        .split(",").map(x => x.trim()).filter(Boolean).map(name => ({ name }));

      if (ingredients.length === 0) return showFlash("Добавьте хотя бы 1 ингредиент", "error");
      if (steps.length === 0) return showFlash("Добавьте хотя бы 1 шаг", "error");

      const payload = {
        title,
        description: description || null,
        cooking_time,
        servings,
        difficulty,
        ingredients,
        steps,
        categories: cats
      };

      const created = await createRecipeMultipart(payload, file);
      showFlash("Рецепт создан", "ok");
      window.location.href = `/recipe/${created.id}`;
    });
  }

  // -----------------------------
  // Edit recipe form
  // -----------------------------
  async function editRecipeInit(recipeId) {
    await getCurrentUser();
    if (!currentUser) {
      showFlash("Нужно войти, чтобы редактировать рецепт", "error");
      window.location.href = "/login";
      return;
    }

    const r = await apiFetch(`/api/recipes/${recipeId}`, { method: "GET" });

    if (r.author?.id !== currentUser.id) {
      showFlash("Нет прав на редактирование", "error");
      window.location.href = `/recipe/${recipeId}`;
      return;
    }

    document.getElementById("title").value = r.title || "";
    document.getElementById("description").value = r.description || "";
    document.getElementById("cooking_time").value = r.cooking_time ?? "";
    document.getElementById("servings").value = r.servings ?? "";
    document.getElementById("difficulty").value = r.difficulty ?? "";
    document.getElementById("categories").value = (r.categories || []).map(c => c.name).join(", ");

    const note = document.getElementById("currentImageNote");
    if (note) note.textContent = r.image_url ? `Текущее: ${r.image_url}` : "Текущее: нет";

    const ingBox = document.getElementById("ingredientsBox");
    const stepsBox = document.getElementById("stepsBox");
    ingBox.innerHTML = "";
    stepsBox.innerHTML = "";

    (r.ingredients || []).forEach(i => ingBox.appendChild(ingredientRowPrefill(i.name, i.quantity || "")));
    (r.steps || []).forEach(s => stepsBox.appendChild(stepRowPrefill(s.description, s.timer_seconds || 0, s.image_url || "")));

    if ((r.ingredients || []).length === 0) ingBox.appendChild(ingredientRowPrefill());
    if ((r.steps || []).length === 0) stepsBox.appendChild(stepRowPrefill());

    document.getElementById("addIngredientBtn").addEventListener("click", () => ingBox.appendChild(ingredientRowPrefill()));
    document.getElementById("addStepBtn").addEventListener("click", () => stepsBox.appendChild(stepRowPrefill()));

    document.getElementById("editRecipeForm").addEventListener("submit", async (e) => {
      e.preventDefault();

      const ingredients = [...ingBox.querySelectorAll(".row")]
        .map((row, idx) => ({
          order: idx + 1,
          name: row.querySelector(".ing-name").value.trim(),
          quantity: row.querySelector(".ing-qty").value.trim()
        }))
        .filter(i => i.name);

      const stepCards = [...stepsBox.querySelectorAll(".card")];
      const steps = [];
      for (let idx = 0; idx < stepCards.length; idx++) {
        const card = stepCards[idx];
        const description = card.querySelector(".step-desc").value.trim();
        if (!description) continue;

        let image_url = card.querySelector(".step-image-url").value.trim();
        const f = card.querySelector(".step-image-file")?.files?.[0] || null;
        if (f) image_url = await uploadStepImage(f);

        steps.push({
          order: idx + 1,
          description,
          timer_seconds: parseInt(card.querySelector(".step-timer").value || "0", 10) || 0,
          image_url
        });
      }

      const cats = (document.getElementById("categories").value || "")
        .split(",").map(x => x.trim()).filter(Boolean).map(name => ({ name }));

      const payload = {
        title: document.getElementById("title").value.trim(),
        description: document.getElementById("description").value.trim() || null,
        cooking_time: parseInt(document.getElementById("cooking_time").value || "0", 10) || null,
        servings: parseInt(document.getElementById("servings").value || "0", 10) || null,
        difficulty: document.getElementById("difficulty").value || null,
        ingredients,
        steps,
        categories: cats
      };

      const recipeFile = document.getElementById("image").files[0] || null;
      if (recipeFile) {
        payload.image_url = await uploadStepImage(recipeFile);
      }

      await apiFetch(`/api/recipes/${recipeId}`, {
        method: "PUT",
        body: JSON.stringify(payload)
      });

      showFlash("Сохранено", "ok");
      window.location.href = `/recipe/${recipeId}`;
    });

    document.getElementById("deleteBtn").addEventListener("click", async () => {
      if (!confirm("Удалить рецепт безвозвратно?")) return;
      await apiFetch(`/api/recipes/${recipeId}`, { method: "DELETE" });
      showFlash("Рецепт удалён", "ok");
      window.location.href = "/";
    });
  }

  // -----------------------------
  // Cooking mode (IMPORTANT FIX)
  // Use ONLY existing overlay from template to avoid duplicate IDs [web:227]
  // -----------------------------
  let cooking = { recipe: null, idx: 0, timerId: null, remaining: 0 };
  let cookingBound = false;

  function bindCookingUI() {
    if (cookingBound) return;

    const overlay = document.getElementById("cookingOverlay");
    if (!overlay) return;

    const closeBtn = document.getElementById("cookClose");
    const prevBtn = document.getElementById("cookPrev");
    const nextBtn = document.getElementById("cookNext");

    if (!closeBtn || !prevBtn || !nextBtn) return;

    closeBtn.addEventListener("click", stopCookingMode);
    prevBtn.addEventListener("click", () => prevStep());
    nextBtn.addEventListener("click", () => nextStep());

    cookingBound = true;
  }

  function startCookingMode(recipe) {
    cooking.recipe = recipe;
    cooking.idx = 0;

    bindCookingUI();

    const overlay = document.getElementById("cookingOverlay");
    if (!overlay) {
      showFlash("Cooking overlay не найден. Добавьте include components/cooking_mode.html", "error");
      return;
    }

    overlay.classList.remove("hidden");
    showStep(0);
  }

  function stopCookingMode() {
    if (cooking.timerId) clearInterval(cooking.timerId);
    cooking.timerId = null;
    cooking.remaining = 0;

    const overlay = document.getElementById("cookingOverlay");
    if (overlay) overlay.classList.add("hidden");
  }

  function showStep(index) {
    const recipe = cooking.recipe;
    if (!recipe || !recipe.steps || recipe.steps.length === 0) {
      showFlash("В рецепте нет шагов", "error");
      return;
    }

    cooking.idx = Math.max(0, Math.min(index, recipe.steps.length - 1));
    const step = recipe.steps[cooking.idx];

    document.getElementById("cookTitle").textContent = recipe.title;
    document.getElementById("cookMeta").textContent = `Шагов: ${recipe.steps.length}`;
    document.getElementById("cookStepIndex").textContent = `Шаг ${cooking.idx + 1} / ${recipe.steps.length}`;
    document.getElementById("cookStepText").textContent = step.description;

    const img = document.getElementById("cookStepImage");
    if (step.image_url) {
      img.src = step.image_url;
      img.classList.remove("hidden");
    } else {
      img.classList.add("hidden");
    }

    if (cooking.timerId) clearInterval(cooking.timerId);
    cooking.timerId = null;

    if (step.timer_seconds && step.timer_seconds > 0) {
      startTimer(step.timer_seconds);
    } else {
      document.getElementById("cookTimer").textContent = "";
    }

    const nextBtn = document.getElementById("cookNext");
    if (nextBtn) nextBtn.textContent = (cooking.idx === recipe.steps.length - 1) ? "Готово" : "Далее";
  }

  async function nextStep() {
    const recipe = cooking.recipe;
    if (!recipe) return;

    if (cooking.idx >= recipe.steps.length - 1) {
      // засчитываем готовку (если вы подключили /api/cooking/complete/<id>)
      try {
        await apiFetch(`/api/cooking/complete/${recipe.id}`, { method: "POST" });
      } catch (e) {
        // если не засчиталось — всё равно завершаем UI
      }
      showFlash("Поздравляем! Рецепт завершён.", "ok");
      stopCookingMode();
      return;
    }

    showStep(cooking.idx + 1);
  }

  function prevStep() {
    showStep(cooking.idx - 1);
  }

  function startTimer(seconds) {
    cooking.remaining = seconds;
    const el = document.getElementById("cookTimer");

    function tick() {
      const m = Math.floor(cooking.remaining / 60);
      const s = cooking.remaining % 60;
      el.textContent = `Таймер: ${m}:${String(s).padStart(2, "0")}`;

      if (cooking.remaining <= 0) {
        clearInterval(cooking.timerId);
        cooking.timerId = null;
        showFlash("Таймер завершён", "ok");
        return;
      }

      cooking.remaining -= 1;
    }

    tick();
    cooking.timerId = setInterval(tick, 1000);
  }

  // -----------------------------
  // Public API
  // -----------------------------
  return {
    initAuthUI,
    register,
    login,
    logout,
    getCurrentUser,

    loadRecipes,
    searchRecipes,
    loadRecipe,

    loadSavedRecipes,
    toggleSaveRecipe,
    loadMyAuthoredRecipes,

    loadComments,
    addComment,

    loadChallenges,

    recipeFormInit,
    editRecipeInit,

    startCookingMode,
  };
})();
