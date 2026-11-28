# RetroBoard — Feature Documentation

> Complete reference of every implemented feature, how it works, and the files behind it.

---

## 1. Board Creation

**What it does:** The landing page lets any user type a board name and click "Create Board". The app generates a unique board instantly and redirects to it.

**How it works:**
- The form on `index.html` sends a `POST /api/boards` request with the title.
- The server generates two random IDs using Python's `secrets` module (cryptographically secure):
  - A 12-character `board_id` — used in the shareable URL
  - A 16-character `facilitator_token` — only given to the board creator
- The board is saved as a JSON file at `boards/<board_id>.json`.
- The browser is redirected to `/board/<id>?facilitator=<token>` — meaning the creator automatically lands as the facilitator.

**Files:** `app.py:69`, `templates/index.html`, `static/style.css`

---

## 2. Three-Column Board

**What it does:** Every board has three fixed columns for the standard retrospective format.

| Column | Key | Purpose |
|---|---|---|
| What Went Well | `went_well` | Positives from the sprint |
| What Didn't Go Well | `didnt_go_well` | Problems and blockers |
| Action Items | `action_items` | Concrete next steps |

**How it works:**
- Columns are defined as a list in `app.py` (`COLUMNS`) and rendered as a CSS grid in `board.html`.
- Each column has its own colour scheme (green / rose / violet), note list, note count badge, and add-note area.
- On mobile (≤900px) the grid switches to a single column stack.

**Files:** `templates/board.html:52–91`, `static/style.css:327–387`

---

## 3. Adding Notes

**What it does:** Any participant can type a note into a column's textarea and submit it. It appears instantly without a page reload.

**How it works:**
- Clicking "Add" or pressing Enter (without Shift) triggers `addNote(column)` in `app.js`.
- A `POST /api/boards/<id>/notes` request is sent with `{ column, text }`.
- The server validates the note (non-empty, correct column, max 500 characters) and saves it.
- The new note card is inserted into the DOM immediately (no waiting for a WebSocket round-trip), using the `_suppressNextBoardUpdate` flag to prevent a double-reload.
- Notes are blocked (HTTP 403) if the facilitator has locked the columns.

**Validations:** Empty text → 400, invalid column → 400, text > 500 chars → 400, locked columns → 403.

**Files:** `app.py:110`, `static/app.js:168`, `templates/board.html:60–64`

---

## 4. Anonymous Voting (Toggle)

**What it does:** Any participant can upvote a note. Clicking again removes the vote. Multiple users can each vote independently on the same note.

**How it works:**
- Each browser generates a random `user_token` on first visit and stores it in `localStorage`. It persists across page refreshes but is unique per browser.
- Clicking the vote button sends `POST /api/boards/<id>/notes/<note_id>/vote` with `{ user_token }`.
- The server stores votes as `votes_by_user: { token: [note_ids] }` in the board JSON.
- If the note ID is already in the user's list → vote is **removed** (action: `"removed"`). Otherwise it is **added** (action: `"added"`).
- The vote count on the button updates immediately without reloading the board.
- Notes are sorted by vote count (highest first) on every render.

**Files:** `app.py:148`, `static/app.js:213`, `static/app.js:5`

---

## 5. Deleting Notes

**What it does:** Any participant can delete any note with a confirm dialog.

**How it works:**
- Clicking the ✕ button shows a browser `confirm()` dialog.
- On confirm, `DELETE /api/boards/<id>/notes/<note_id>` is sent.
- The card is removed from the DOM immediately. If the column is now empty, the empty-state message is shown.
- A WebSocket `board_updated` event is emitted to all other connected browsers so they also see the deletion.

**Files:** `app.py:177`, `static/app.js:247`

---

## 6. Empty State Messages

**What it does:** When a column has no notes, it shows a helpful placeholder instead of blank space.

**How it works:**
- `renderColumn()` checks if `notes.length === 0` and injects `<p class="empty-state">No notes yet — add one below</p>`.
- The message is also shown after the last note in a column is deleted.

**Files:** `static/app.js:120`, `static/style.css:498`

---

## 7. Real-time Sync (WebSocket)

**What it does:** When any user adds, votes on, or deletes a note, all other browsers viewing the same board update automatically — no manual refresh needed.

**How it works:**
- The backend uses Flask-SocketIO. Each board is a Socket.IO **room** named by its `board_id`.
- When a browser opens a board, it emits `join_board` → server calls `join_room(board_id)`.
- After any data-changing API call, the server emits `board_updated` to the room → all browsers call `loadBoard()` to re-fetch and re-render.
- Facilitator state changes (`board_state` event) are broadcast separately so all browsers instantly see phase/timer/lock changes.
- The `_suppressNextBoardUpdate` flag in `app.js` prevents the browser that made the change from doing a redundant reload (it already updated locally).

**Files:** `app.py:303–324`, `static/app.js:28–52`

---

## 8. Live Presence Badge

**What it does:** A green badge in the board header shows how many people are currently viewing the board (e.g. "● 2 people active").

**How it works:**
- The server maintains a dict `_board_rooms: { board_id: set(session_ids) }`.
- On `join_board`, the session ID is added to the set and the count is emitted to all room members via a `presence` event.
- On `disconnect`, the session ID is removed and the updated count is re-broadcast.
- The badge has a pulsing green dot animation in CSS.

**Files:** `app.py:305–324`, `static/app.js:34–37`, `static/style.css:254–285`

---

## 9. Copy Link Button

**What it does:** One click copies the participant board URL to the clipboard and shows a toast confirmation.

**How it works:**
- The button calls `copyLink()` which uses the Clipboard API (`navigator.clipboard.writeText`).
- The copied URL is the plain board URL **without** the facilitator token — safe to share with the whole team.
- Falls back to showing the URL in a toast if clipboard access is denied.

**Files:** `static/app.js:271`, `templates/board.html:16`

---

## 10. Facilitator Mode

**What it does:** The board creator gets a special control panel (dark bar) with tools to run the retrospective session. Regular participants do not see this bar.

**How it works:**
- When a board is created, the creator is redirected with `?facilitator=<token>` in the URL.
- The Flask route checks if the token matches; if yes, `IS_FACILITATOR = true` is injected into the page template.
- The facilitator bar is shown via `display: flex` in `app.js:74`.
- All facilitator actions send the `facilitator_token` in the request body. The server validates it on every facilitator endpoint — wrong or missing token returns HTTP 403.
- The token is **never** included in the `GET /api/boards` response, so participants cannot discover it.

**Files:** `app.py:54–64`, `app.py:202–207`, `templates/board.html:25–45`

---

## 11. Phase Control

**What it does:** The facilitator can set the board's current phase. A status chip at the top of the board shows the current phase to all participants in real time.

| Phase | Meaning |
|---|---|
| Collecting | Team is writing notes |
| Voting | Team is upvoting notes |
| Discussing | Team is talking through the results |

**How it works:**
- Clicking a phase button calls `facPhase(phase)` → `POST /api/boards/<id>/facilitator/phase`.
- The server updates `data["phase"]` and emits a `board_state` WebSocket event to all browsers.
- All browsers call `applyBoardState()` which updates the phase chip colour and the active button highlight.

**Files:** `app.py:239`, `static/app.js:386`, `static/style.css:754–781`

---

## 12. Reveal / Hide Notes

**What it does:** Notes are hidden from participants by default. The facilitator can reveal them all at once. This prevents the first person's notes from influencing everyone else (anchoring bias).

**How it works:**
- When `notes_revealed: false`, the `GET /api/boards` response replaces every note's `text` with `""` and sets `hidden: true`.
- The frontend renders hidden notes as a greyed-out "🔒 Hidden note" card with voting disabled.
- The facilitator's GET request includes the `facilitator_token` as a query param — the server skips redaction for them.
- Clicking "Reveal Notes" calls `facReveal()` → `POST .../facilitator/reveal` which toggles `notes_revealed` and broadcasts a `board_updated` + `board_state` event.
- Clicking again hides them (it's a toggle).

**Files:** `app.py:97–107`, `app.py:212`, `static/app.js:131–144`, `static/app.js:360`

---

## 13. Lock / Unlock Columns

**What it does:** The facilitator can lock all columns to prevent new notes from being added (useful during voting or discussion phases).

**How it works:**
- `POST .../facilitator/lock` toggles `columns_locked` on the board and broadcasts `board_state`.
- When locked, `POST /api/boards/<id>/notes` returns HTTP 403 with the message "Columns are locked by the facilitator".
- On the frontend, `applyBoardState()` hides all `.add-note-area` elements for non-facilitators.
- The Lock button turns red when active.

**Files:** `app.py:115–116`, `app.py:226`, `static/app.js:169–172`, `static/app.js:373`

---

## 14. Countdown Timer

**What it does:** The facilitator can start a visible countdown timer (2, 5, or 10 minutes) that all participants see ticking down in the status bar.

**How it works:**
- `POST .../facilitator/timer` with `{ minutes: N }` sets `voting_ends_at` to `utcnow() + N minutes` (ISO timestamp) and broadcasts `board_state`.
- All browsers receive the end time and run `startTimerCountdown(endsAt)` — a `setInterval` that ticks every second.
- When time runs out, it shows "⏰ Time's up!".
- Setting minutes to 0 clears `voting_ends_at` and stops the timer on all browsers.

**Files:** `app.py:255`, `static/app.js:338–356`, `static/app.js:398`

---

## 15. Copy Facilitator Link

**What it does:** The facilitator can copy their special link (with token) to share facilitator access with another person.

**How it works:**
- `copyFacLink()` builds the URL as `origin + /board/<id>?facilitator=<token>` and writes it to the clipboard.
- Anyone who opens this URL gets the full facilitator control panel.

**Files:** `static/app.js:281`, `templates/board.html:44`

---

## 16. Markdown Export

**What it does:** Clicking "↓ Export" downloads the entire board as a `.md` file, with notes sorted by vote count.

**What the file contains:**
```
# Sprint 42 Retrospective
> Exported on 2026-11-28 · Board ID: `abc123` · 7 notes total
> What Went Well: 3 · What Didn't Go Well: 2 · Action Items: 2

## What Went Well (3)
- Great teamwork _(+4 votes)_
- CI pipeline runs fast _(+2 votes)_
- Good communication

## What Didn't Go Well (2)
...
```

**How it works:**
- `GET /api/boards/<id>/export` builds a Markdown string server-side.
- Notes within each section are sorted by votes descending.
- Response headers set `Content-Type: text/markdown` and `Content-Disposition: attachment` so the browser downloads it as a file.

**Files:** `app.py:273`

---

## 17. UI Animations & Polish

**What it does:** The UI has a set of micro-animations for a polished feel.

| Animation | Trigger | Description |
|---|---|---|
| `float` | Page load | Logo mark bobs up and down continuously |
| `fadeUp` | Page load | Landing page wrapper fades up into view |
| `slideIn` | New note added | Card slides up and scales in with spring easing |
| `popIn` | Vote button clicked | Button bounces with overshoot |
| `pulse-dot` | Always | Presence badge green dot pulses softly |

**Files:** `static/style.css:88`, `static/style.css:419–433`

---

## 18. Responsive Design

**What it does:** The board works on mobile, tablet, and desktop.

| Breakpoint | Behaviour |
|---|---|
| > 900px | 3-column grid |
| ≤ 900px | Single-column stack |
| ≤ 600px | Compact header, board title moves to its own row, tighter padding |

**Files:** `static/style.css:582–607`

---

## 19. Persistent Vote State per Browser

**What it does:** If you refresh the page, your previously voted notes still appear highlighted — the browser remembers which notes you voted on.

**How it works:**
- On load, `GET /api/boards/<id>/my_votes?user_token=<token>` fetches the list of note IDs the current user has voted on.
- These are stored in `_votedNotes` (a `Set`) and used when rendering vote buttons (`voted` class = highlighted).

**Files:** `static/app.js:81–95`, `app.py:140`

---

## 20. Test Suite (28 tests)

**What it covers:**

| Category | Tests |
|---|---|
| Board creation | Returns ID, default title, 404 on missing board |
| Notes | Add, invalid column, empty text, too long, appears in board |
| Voting | Vote adds, increments, toggle removes, different users, note not found |
| Delete | Removes note, 404 on missing |
| Export | Returns Markdown, includes all column headers |
| Facilitator | Token in create response, notes hidden by default, visible to facilitator, reveal toggle, lock blocks add, phase change, timer set/clear, wrong token rejected |

**Files:** `tests/test_app.py`, `tests/conftest.py`

---

## 21. CI Pipeline

**What it does:** Every push to GitHub automatically runs the full test suite.

**How it works:**
- `.github/workflows/ci.yml` defines a GitHub Actions workflow.
- On every push or pull request, it installs dependencies and runs `pytest tests/ -v`.

**Files:** `.github/workflows/ci.yml`

---

## Summary Table

| # | Feature | Who built it |
|---|---|---|
| 1 | Board creation | You (2025sl93072) |
| 2 | Three-column board | You |
| 3 | Adding notes | You |
| 4 | Anonymous voting (toggle) | You + friend (2025sl93094) |
| 5 | Deleting notes | You |
| 6 | Empty state messages | You |
| 7 | Real-time sync (WebSocket) | Friend (2025sl93094) |
| 8 | Live presence badge | Friend |
| 9 | Copy link button | You |
| 10 | Facilitator mode | Friend |
| 11 | Phase control | Friend |
| 12 | Reveal / hide notes | Friend |
| 13 | Lock / unlock columns | Friend |
| 14 | Countdown timer | Friend |
| 15 | Copy facilitator link | Friend |
| 16 | Markdown export | You + friend (improved by PR #10) |
| 17 | UI animations & polish | You |
| 18 | Responsive design | You |
| 19 | Persistent vote state | Friend |
| 20 | Test suite (28 tests) | You + friend (PR #9) |
| 21 | CI pipeline | Friend (PR #9) |

---

## Professor Q&A — Likely Questions

### Architecture & Design

**Q: Why did you choose Flask over Django or FastAPI?**
Flask is a micro-framework — it gives you routing and templating with no forced structure. For a project this size, Django would be overkill (we don't need an ORM, admin panel, or auth system). FastAPI would also work but adds async complexity without benefit here since our bottleneck is disk I/O, not CPU.

**Q: Why JSON files instead of a database like SQLite or PostgreSQL?**
The goal was zero-configuration self-hosting. With JSON files, you run `python app.py` and it works — no database server to install, no migrations, no connection strings. The trade-off is no ACID guarantees and no querying. For a tool where boards are small and writes are infrequent, this is acceptable.

**Q: What happens if two users add a note at exactly the same time?**
There is a potential race condition — both requests could read the same file, each append their note, and one write could overwrite the other. We don't use file locking. In practice this is unlikely (the write is fast), but it is a known limitation. A proper fix would be to use SQLite (which handles concurrency natively) or add a file lock with Python's `fcntl`.

**Q: How does WebSocket fit into the Flask request/response model?**
Normal HTTP is request-response — the server can't push data to a client. WebSocket is a persistent bidirectional connection. Flask-SocketIO adds a WebSocket layer on top of Flask. When a note is added via HTTP POST, the server also emits a `board_updated` Socket.IO event to everyone in the same board "room", which triggers their browsers to reload the board data.

---

### Security

**Q: How do you prevent someone from using someone else's facilitator token?**
The token is a 16-character random string generated with Python's `secrets` module, which uses the OS's cryptographically secure random number generator. With 36 possible characters, there are 36^16 ≈ 7.9 × 10^24 possible tokens. Brute-forcing it is not practical.

**Q: Why is the facilitator token not returned in GET /api/boards?**
If it were included in the response, any participant could read it from the network tab in their browser and gain facilitator access. The token is only given once — in the create response — and stored in the URL of the person who created the board.

**Q: Can anyone delete any note?**
Yes — there is no ownership check on delete. This is intentional: the tool is designed for trusted teams where anonymity is about psychological safety, not protection from bad actors. Adding ownership would require user authentication, which contradicts the "no login" design goal.

**Q: How do you prevent XSS (Cross-Site Scripting)?**
The `escapeHtml()` function in `app.js` escapes `&`, `<`, `>`, and `"` before injecting any note text into the DOM as `innerHTML`. This prevents a user from posting a note like `<script>alert(1)</script>` and having it execute in other browsers.

---

### Features & Decisions

**Q: Why are notes hidden by default?**
This is a deliberate UX choice to prevent anchoring bias — where the first idea seen disproportionately influences everyone else. The facilitator reveals all notes at once so the team sees them together, not sequentially.

**Q: What does the user_token actually identify?**
It identifies a browser session, not a person. It is generated once and stored in `localStorage`. Two different people using the same browser would share a token; one person using two browsers would have two tokens. It's good enough for vote deduplication in a team setting.

**Q: Why is voting a toggle (can remove vote) instead of one-way?**
In practice, people change their minds. During a timed voting phase it's frustrating to be locked into an accidental click. Allowing vote removal improves usability without compromising the integrity of the results.

**Q: What is the purpose of the `_suppressNextBoardUpdate` flag?**
When you add a note or vote, your browser immediately updates the DOM (optimistic update). The server also broadcasts a `board_updated` WebSocket event to everyone in the room — including you. Without the flag, your browser would receive that event and do a full reload, causing a flicker. The flag tells your browser to ignore the next event since it already applied the change.

**Q: What happens if two facilitators exist simultaneously?**
The facilitator link can be shared with others via the "Copy Facilitator Link" button. If two people have facilitator access, their actions are independent — there is no conflict resolution. The last write wins, which is consistent with the JSON file storage model.

---

### Testing & Quality

**Q: What is your test coverage and how did you test it?**
We have 28 automated tests covering board creation, note CRUD, voting (including toggle and multi-user), delete, export content, and all facilitator features (token validation, reveal toggle, lock, phase change, timer). Tests use Flask's built-in test client and pytest's `tmp_path` fixture to isolate each test with a clean temp directory for board files.

**Q: Why don't the tests cover the WebSocket/real-time functionality?**
Flask-SocketIO's real-time events are integration-level and require a running server with a WebSocket transport. The current tests use Flask's synchronous test client which doesn't support Socket.IO events. Testing this properly would require `pytest-socketio` or end-to-end browser tests with a tool like Playwright. This is a known gap.

**Q: What does the CI pipeline do?**
Every push to GitHub triggers a GitHub Actions workflow (`.github/workflows/ci.yml`) that installs dependencies and runs `pytest tests/ -v`. This ensures no broken code is merged without tests failing visibly.

---

### Deployment & Scalability

**Q: How would you deploy this to production?**
Run it behind a reverse proxy like nginx, which handles HTTPS and forwards requests to the Flask app running under gunicorn with the eventlet or gevent worker (required for Socket.IO). Example: `gunicorn --worker-class eventlet -w 1 app:app`.

**Q: Why only 1 worker for production?**
Socket.IO room state (`_board_rooms` dict) lives in memory. With multiple processes, each worker would have its own copy and they'd go out of sync. The fix is to use Socket.IO's Redis adapter, which syncs room state across processes. We haven't implemented that — it's a known scalability limitation.

**Q: Does the app scale to hundreds of boards?**
Each board is one file read per request. With hundreds of boards and low concurrent users, it's fine. At very high scale, the filesystem becomes a bottleneck — you'd want to migrate to SQLite or PostgreSQL and add caching.

**Q: What happens to boards over time? Is there any cleanup?**
No. Boards accumulate in the `boards/` directory indefinitely. There is no expiry, archiving, or admin interface. For production use, a cron job that deletes boards older than N days would be needed.
