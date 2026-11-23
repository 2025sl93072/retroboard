const COLUMNS = ["went_well", "didnt_go_well", "action_items"];

// ── Bootstrap ────────────────────────────────────────────────────────────────

async function init() {
  await loadBoard();
  document.getElementById("exportBtn").href = `/api/boards/${BOARD_ID}/export`;
  document.getElementById("copyBtn").addEventListener("click", copyLink);

  document.querySelectorAll(".btn-add").forEach(btn => {
    btn.addEventListener("click", () => addNote(btn.dataset.column));
  });

  document.querySelectorAll(".note-input").forEach(input => {
    input.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        addNote(input.id.replace("input-", ""));
      }
    });
  });
}

// ── Load Board ───────────────────────────────────────────────────────────────

async function loadBoard() {
  const res  = await fetch(`/api/boards/${BOARD_ID}`);
  const data = await res.json();

  document.getElementById("boardTitle").textContent = data.title;
  document.title = `${data.title} · RetroBoard`;

  COLUMNS.forEach(col => renderColumn(col, data.columns[col] || []));
}

function renderColumn(column, notes) {
  const list  = document.getElementById(`notes-${column}`);
  const count = document.getElementById(`count-${column}`);
  count.textContent = notes.length;

  list.innerHTML = "";
  if (notes.length === 0) {
    list.innerHTML = `<p class="empty-state">No notes yet — add one below</p>`;
    return;
  }

  notes
    .slice()
    .sort((a, b) => b.votes - a.votes)
    .forEach(note => list.appendChild(buildNoteCard(note, column)));
}

function buildNoteCard(note, column) {
  const card = document.createElement("div");
  card.className = "note-card";
  card.dataset.id = note.id;

  card.innerHTML = `
    <p class="note-text">${escapeHtml(note.text)}</p>
    <div class="note-actions">
      <button class="btn-vote" data-id="${note.id}" data-column="${column}" title="Upvote">
        ▲ <span class="vote-count">${note.votes}</span>
      </button>
      <button class="btn-delete" data-id="${note.id}" data-column="${column}" title="Delete note">✕</button>
    </div>
  `;

  card.querySelector(".btn-vote").addEventListener("click",   e => voteNote(e.currentTarget));
  card.querySelector(".btn-delete").addEventListener("click", e => deleteNote(e.currentTarget));
  return card;
}

// ── Add Note ─────────────────────────────────────────────────────────────────

async function addNote(column) {
  const input = document.getElementById(`input-${column}`);
  const btn   = document.querySelector(`.btn-add[data-column="${column}"]`);
  const text  = input.value.trim();

  if (!text) { input.focus(); return; }

  btn.disabled = true;
  try {
    const res = await fetch(`/api/boards/${BOARD_ID}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ column, text }),
    });
    if (!res.ok) {
      const err = await res.json();
      showToast(err.error || "Failed to add note");
      return;
    }
    input.value = "";
    await loadBoard();
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

// ── Vote ─────────────────────────────────────────────────────────────────────

async function voteNote(btn) {
  if (btn.classList.contains("voted")) {
    showToast("You already voted on this note");
    return;
  }
  const noteId = btn.dataset.id;
  const res    = await fetch(`/api/boards/${BOARD_ID}/notes/${noteId}/vote`, { method: "POST" });
  if (!res.ok) return;
  const data   = await res.json();

  btn.classList.add("voted");
  btn.classList.remove("pop");
  void btn.offsetWidth; // reflow to restart animation
  btn.classList.add("pop");
  btn.querySelector(".vote-count").textContent = data.votes;
  showToast("Vote counted ▲");
  await loadBoard();
}

// ── Delete ────────────────────────────────────────────────────────────────────

async function deleteNote(btn) {
  if (!confirm("Delete this note?")) return;
  const noteId = btn.dataset.id;
  const res    = await fetch(`/api/boards/${BOARD_ID}/notes/${noteId}`, { method: "DELETE" });
  if (res.ok) {
    await loadBoard();
    showToast("Note deleted");
  }
}

// ── Copy Link ─────────────────────────────────────────────────────────────────

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href);
    showToast("Board link copied to clipboard ✓");
  } catch {
    showToast("Copy: " + window.location.href);
  }
}

// ── Toast ─────────────────────────────────────────────────────────────────────

let toastTimer;
function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2500);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Start ─────────────────────────────────────────────────────────────────────

init();
