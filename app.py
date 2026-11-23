import json
import secrets
import string
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, abort

app = Flask(__name__)
BOARDS_DIR = Path("boards")
BOARDS_DIR.mkdir(exist_ok=True)

COLUMNS = ["went_well", "didnt_go_well", "action_items"]
COLUMN_LABELS = {
    "went_well": "What Went Well",
    "didnt_go_well": "What Didn't Go Well",
    "action_items": "Action Items",
}


def _board_path(board_id: str) -> Path:
    return BOARDS_DIR / f"{board_id}.json"


def _load_board(board_id: str) -> dict:
    path = _board_path(board_id)
    if not path.exists():
        abort(404)
    return json.loads(path.read_text())


def _save_board(board_id: str, data: dict) -> None:
    _board_path(board_id).write_text(json.dumps(data, indent=2))


def _new_id(length: int = 12) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/board/<board_id>")
def board(board_id):
    _load_board(board_id)   # 404 if missing
    return render_template("board.html", board_id=board_id)


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/boards", methods=["POST"])
def create_board():
    body = request.get_json(silent=True) or {}
    board_id = _new_id()
    data = {
        "id": board_id,
        "title": body.get("title", "Sprint Retrospective"),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "columns": {col: [] for col in COLUMNS},
    }
    _save_board(board_id, data)
    return jsonify({"id": board_id}), 201


@app.route("/api/boards/<board_id>", methods=["GET"])
def get_board(board_id):
    return jsonify(_load_board(board_id))


@app.route("/api/boards/<board_id>/notes", methods=["POST"])
def add_note(board_id):
    data = _load_board(board_id)
    body = request.get_json(silent=True) or {}

    column = body.get("column")
    text = (body.get("text") or "").strip()

    if column not in COLUMNS:
        return jsonify({"error": "Invalid column"}), 400
    if not text:
        return jsonify({"error": "Note text is required"}), 400
    if len(text) > 500:
        return jsonify({"error": "Note too long (max 500 characters)"}), 400

    note = {
        "id": _new_id(8),
        "text": text,
        "votes": 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    data["columns"][column].append(note)
    _save_board(board_id, data)
    return jsonify(note), 201


@app.route("/api/boards/<board_id>/notes/<note_id>/vote", methods=["POST"])
def vote_note(board_id, note_id):
    data = _load_board(board_id)
    for column in COLUMNS:
        for note in data["columns"][column]:
            if note["id"] == note_id:
                note["votes"] += 1
                _save_board(board_id, data)
                return jsonify({"votes": note["votes"]})
    return jsonify({"error": "Note not found"}), 404


@app.route("/api/boards/<board_id>/notes/<note_id>", methods=["DELETE"])
def delete_note(board_id, note_id):
    data = _load_board(board_id)
    for column in COLUMNS:
        notes = data["columns"][column]
        for i, note in enumerate(notes):
            if note["id"] == note_id:
                notes.pop(i)
                _save_board(board_id, data)
                return jsonify({"ok": True})
    return jsonify({"error": "Note not found"}), 404


@app.route("/api/boards/<board_id>/export", methods=["GET"])
def export_board(board_id):
    data = _load_board(board_id)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    counts = {col: len(data["columns"][col]) for col in COLUMNS}
    total = sum(counts.values())
    summary = " · ".join(f"{COLUMN_LABELS[col]}: {counts[col]}" for col in COLUMNS)
    lines = [
        f"# {data['title']}",
        f"> Exported on {today} · Board ID: `{board_id}` · **{total} notes total**",
        f"> {summary}",
        "",
    ]
    for col in COLUMNS:
        notes = data["columns"][col]
        lines.append(f"## {COLUMN_LABELS[col]} ({len(notes)})")
        if notes:
            sorted_notes = sorted(notes, key=lambda n: n["votes"], reverse=True)
            for note in sorted_notes:
                votes = f" _(+{note['votes']} votes)_" if note["votes"] else ""
                lines.append(f"- {note['text']}{votes}")
        else:
            lines.append("_No notes_")
        lines.append("")
    return "\n".join(lines), 200, {
        "Content-Type": "text/markdown",
        "Content-Disposition": f"attachment; filename=retroboard-{today}.md",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.run(debug=True, port=args.port)
