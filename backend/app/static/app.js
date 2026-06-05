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

function appendMessage(content, role = "assistant") {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = content;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
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
    status.textContent = `Policy: ${result.policy}. Mode: ${result.mode}.`;
    appendMessage(result.message, "assistant");
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
