const userId = "demo";

const fields = {
  pantry: document.querySelector("#pantry"),
  equipment: document.querySelector("#equipment"),
  preferences: document.querySelector("#preferences"),
  allergies: document.querySelector("#allergies"),
};
const messages = document.querySelector("#messages");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const traceToggle = document.querySelector("#traceToggle");

function listFromField(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function fieldFromList(items) {
  return (items || []).join(", ");
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatInlineMarkdown(value) {
  return escapeHtml(value).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

function renderMarkdown(content) {
  const html = [];
  const lines = content.trim().split("\n");
  let paragraph = [];
  let list = null;

  function flushParagraph() {
    if (!paragraph.length) return;
    html.push(`<p>${paragraph.map(formatInlineMarkdown).join("<br>")}</p>`);
    paragraph = [];
  }

  function flushList() {
    if (!list) return;
    html.push(`<${list.type}>${list.items.join("")}</${list.type}>`);
    list = null;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length + 2;
      html.push(`<h${level}>${formatInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    const unordered = line.match(/^[-*]\s+(.+)$/);
    if (unordered) {
      flushParagraph();
      if (!list || list.type !== "ul") {
        flushList();
        list = { type: "ul", items: [] };
      }
      list.items.push(`<li>${formatInlineMarkdown(unordered[1])}</li>`);
      continue;
    }

    const ordered = line.match(/^\d+\.\s+(.+)$/);
    if (ordered) {
      flushParagraph();
      if (!list || list.type !== "ol") {
        flushList();
        list = { type: "ol", items: [] };
      }
      list.items.push(`<li>${formatInlineMarkdown(ordered[1])}</li>`);
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();

  return html.join("");
}

function appendMessage(content, role = "assistant") {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  if (role === "assistant") {
    if (typeof content === "object" && content) {
      node.innerHTML = renderStructuredContent(content);
    } else {
      node.innerHTML = renderMarkdown(content);
    }
  } else {
    node.textContent = content;
  }
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}

function renderStructuredContent(content) {
  const parts = [];
  if (content.intro) {
    parts.push(`<p>${formatInlineMarkdown(content.intro)}</p>`);
  }
  for (const recipe of content.recipes || []) {
    parts.push(renderRecipeCard(recipe));
  }
  if (content.safety_notes?.length) {
    parts.push(`<h4>Notes</h4><ul>${content.safety_notes.map((note) => `<li>${formatInlineMarkdown(note)}</li>`).join("")}</ul>`);
  }
  if (content.follow_up_question) {
    parts.push(`<div class="follow-up"><strong>Quick question:</strong> ${formatInlineMarkdown(content.follow_up_question)}</div>`);
  }
  if (content.allergen_notice) {
    parts.push(`<p class="allergen-note">${formatInlineMarkdown(content.allergen_notice)}</p>`);
  }
  return parts.join("");
}

function renderRecipeCard(recipe) {
  const fitItems = [];
  if (recipe.missing_ingredients?.length) {
    fitItems.push(`<li><strong>Missing pantry items:</strong> ${recipe.missing_ingredients.map(escapeHtml).join(", ")}</li>`);
  }
  if (recipe.missing_equipment?.length) {
    fitItems.push(`<li><strong>Missing equipment:</strong> ${recipe.missing_equipment.map(escapeHtml).join(", ")}</li>`);
  }
  for (const workaround of recipe.workarounds || []) {
    fitItems.push(`<li><strong>Workaround:</strong> ${formatInlineMarkdown(workaround)}</li>`);
  }
  for (const substitution of recipe.substitutions || []) {
    fitItems.push(`<li><strong>Substitution:</strong> ${formatInlineMarkdown(substitution)}</li>`);
  }

  return `
    <section class="recipe-card ${recipe.can_make ? "can-make" : "needs-work"}">
      <h3>${formatInlineMarkdown(recipe.title)}</h3>
      ${recipe.summary ? `<p>${formatInlineMarkdown(recipe.summary)}</p>` : ""}
      ${renderList("Ingredients", recipe.ingredients)}
      ${renderList("Required Equipment", recipe.required_equipment)}
      ${renderOrderedList("Steps", recipe.steps)}
      ${fitItems.length ? `<h4>Fit Check</h4><ul class="fit-list">${fitItems.join("")}</ul>` : `<p class="fit-ok">Fits your saved pantry and equipment.</p>`}
    </section>
  `;
}

function renderList(title, items) {
  if (!items?.length) return "";
  return `<h4>${escapeHtml(title)}</h4><ul>${items.map((item) => `<li>${formatInlineMarkdown(item)}</li>`).join("")}</ul>`;
}

function renderOrderedList(title, items) {
  if (!items?.length) return "";
  return `<h4>${escapeHtml(title)}</h4><ol>${items.map((item) => `<li>${formatInlineMarkdown(item)}</li>`).join("")}</ol>`;
}

function appendTrace(trace) {
  if (!traceToggle.checked || !trace?.length) return;
  const node = document.createElement("pre");
  node.className = "trace";
  node.textContent = JSON.stringify(trace, null, 2);
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
}

async function loadProfile() {
  const response = await fetch(`/api/profile/${userId}`);
  const profile = await response.json();
  fields.pantry.value = fieldFromList(profile.pantry);
  fields.equipment.value = fieldFromList(profile.equipment);
  fields.preferences.value = fieldFromList(profile.preferences);
  fields.allergies.value = fieldFromList(profile.allergies);
}

async function saveProfile() {
  const payload = {
    pantry: listFromField(fields.pantry.value),
    equipment: listFromField(fields.equipment.value),
    preferences: listFromField(fields.preferences.value),
    allergies: listFromField(fields.allergies.value),
  };
  await fetch(`/api/profile/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  appendMessage("Saved household memory.", "status");
}

document.querySelector("#saveProfile").addEventListener("click", saveProfile);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  appendMessage(message, "user");
  const status = appendMessage("Checking your household memory and tools...", "status");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, message }),
    });
    const result = await response.json();
    status.textContent = `Policy: ${result.policy}. Mode: ${result.mode}. Model: ${result.model_tier} (${result.model}).`;
    appendMessage(result.content || result.message, "assistant");
    appendTrace(result.trace);
    await loadProfile();
  } catch (error) {
    status.textContent = "Something went wrong while contacting PantryPal.";
    appendMessage(String(error), "assistant");
  }
});

appendMessage(
  "Tell me what you have, or ask for a dinner idea. I will check your pantry and equipment before I get bossy.",
  "assistant",
);
loadProfile();
