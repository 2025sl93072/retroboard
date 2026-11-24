import json
import pytest
from app import app, BOARDS_DIR


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("app.BOARDS_DIR", tmp_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Board creation ────────────────────────────────────────────────────────────

def test_create_board_returns_id(client):
    res = client.post("/api/boards", json={"title": "Test Sprint"})
    assert res.status_code == 201
    data = res.get_json()
    assert "id" in data
    assert len(data["id"]) == 12


def test_create_board_default_title(client):
    res = client.post("/api/boards", json={})
    assert res.status_code == 201


def test_get_board(client):
    res  = client.post("/api/boards", json={"title": "My Retro"})
    bid  = res.get_json()["id"]
    res2 = client.get(f"/api/boards/{bid}")
    assert res2.status_code == 200
    data = res2.get_json()
    assert data["title"] == "My Retro"
    assert "went_well" in data["columns"]
    assert "didnt_go_well" in data["columns"]
    assert "action_items" in data["columns"]


def test_get_board_not_found(client):
    res = client.get("/api/boards/doesnotexist")
    assert res.status_code == 404


# ── Notes ─────────────────────────────────────────────────────────────────────

def _make_board(client, title="Retro"):
    res = client.post("/api/boards", json={"title": title})
    return res.get_json()["id"]


def test_add_note(client):
    bid = _make_board(client)
    res = client.post(f"/api/boards/{bid}/notes",
                      json={"column": "went_well", "text": "Great teamwork"})
    assert res.status_code == 201
    note = res.get_json()
    assert note["text"] == "Great teamwork"
    assert note["votes"] == 0


def test_add_note_invalid_column(client):
    bid = _make_board(client)
    res = client.post(f"/api/boards/{bid}/notes",
                      json={"column": "not_a_column", "text": "hi"})
    assert res.status_code == 400


def test_add_note_empty_text(client):
    bid = _make_board(client)
    res = client.post(f"/api/boards/{bid}/notes",
                      json={"column": "went_well", "text": "   "})
    assert res.status_code == 400


def test_add_note_too_long(client):
    bid = _make_board(client)
    res = client.post(f"/api/boards/{bid}/notes",
                      json={"column": "went_well", "text": "x" * 501})
    assert res.status_code == 400


def test_note_appears_in_board(client):
    bid = _make_board(client)
    client.post(f"/api/boards/{bid}/notes",
                json={"column": "action_items", "text": "Fix the CI"})
    board = client.get(f"/api/boards/{bid}").get_json()
    texts = [n["text"] for n in board["columns"]["action_items"]]
    assert "Fix the CI" in texts


# ── Voting ────────────────────────────────────────────────────────────────────

def test_vote_note(client):
    bid = _make_board(client)
    nid = client.post(f"/api/boards/{bid}/notes",
                      json={"column": "went_well", "text": "Good demo"}).get_json()["id"]
    res = client.post(f"/api/boards/{bid}/notes/{nid}/vote", json={"user_token": "user1"})
    assert res.status_code == 200
    assert res.get_json()["votes"] == 1
    assert res.get_json()["action"] == "added"


def test_vote_increments(client):
    bid = _make_board(client)
    nids = [
        client.post(f"/api/boards/{bid}/notes",
                    json={"column": "went_well", "text": f"note {i}"}).get_json()["id"]
        for i in range(3)
    ]
    for nid in nids:
        client.post(f"/api/boards/{bid}/notes/{nid}/vote", json={"user_token": "user1"})
    board = client.get(f"/api/boards/{bid}").get_json()
    total_votes = sum(n["votes"] for n in board["columns"]["went_well"])
    assert total_votes == 3


def test_vote_note_not_found(client):
    bid = _make_board(client)
    res = client.post(f"/api/boards/{bid}/notes/fakeid/vote", json={"user_token": "user1"})
    assert res.status_code == 404


def test_toggle_vote_removes(client):
    bid = _make_board(client)
    nid = client.post(f"/api/boards/{bid}/notes",
                      json={"column": "went_well", "text": "x"}).get_json()["id"]
    client.post(f"/api/boards/{bid}/notes/{nid}/vote", json={"user_token": "user1"})
    res = client.post(f"/api/boards/{bid}/notes/{nid}/vote", json={"user_token": "user1"})
    assert res.status_code == 200
    assert res.get_json()["votes"] == 0
    assert res.get_json()["action"] == "removed"


def test_different_users_can_each_vote(client):
    bid = _make_board(client)
    nid = client.post(f"/api/boards/{bid}/notes",
                      json={"column": "went_well", "text": "x"}).get_json()["id"]
    client.post(f"/api/boards/{bid}/notes/{nid}/vote", json={"user_token": "user1"})
    client.post(f"/api/boards/{bid}/notes/{nid}/vote", json={"user_token": "user2"})
    board = client.get(f"/api/boards/{bid}").get_json()
    assert board["columns"]["went_well"][0]["votes"] == 2


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_note(client):
    bid = _make_board(client)
    nid = client.post(f"/api/boards/{bid}/notes",
                      json={"column": "didnt_go_well", "text": "Bad deploy"}).get_json()["id"]
    res = client.delete(f"/api/boards/{bid}/notes/{nid}")
    assert res.status_code == 200
    board = client.get(f"/api/boards/{bid}").get_json()
    ids = [n["id"] for n in board["columns"]["didnt_go_well"]]
    assert nid not in ids


def test_delete_note_not_found(client):
    bid = _make_board(client)
    res = client.delete(f"/api/boards/{bid}/notes/fakeid")
    assert res.status_code == 404


# ── Export ────────────────────────────────────────────────────────────────────

def test_export_returns_markdown(client):
    bid = _make_board(client, "Export Test")
    client.post(f"/api/boards/{bid}/notes",
                json={"column": "went_well", "text": "Good sprint"})
    res = client.get(f"/api/boards/{bid}/export")
    assert res.status_code == 200
    assert b"Export Test" in res.data
    assert b"Good sprint" in res.data
    assert b"What Went Well" in res.data


def test_export_includes_all_columns(client):
    bid = _make_board(client)
    res = client.get(f"/api/boards/{bid}/export")
    text = res.data.decode()
    assert "What Went Well" in text
    assert "What Didn't Go Well" in text
    assert "Action Items" in text
