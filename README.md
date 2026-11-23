# RetroBoard

> Lightweight self-hosted retrospective tool for dev teams. No login. No account. Just a link.

[![CI](https://github.com/2025sl93072/retroboard/actions/workflows/ci.yml/badge.svg)](https://github.com/2025sl93072/retroboard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

---

## The Problem

Teams use Miro, Mural, and Confluence for retrospectives — all proprietary, expensive, and overkill. Setting them up requires accounts, invites, and subscriptions. There is no self-hosted, open-source retrospective tool that works instantly with just a shared link.

**RetroBoard** fixes this. Run it locally or on a server, create a board in one click, share the URL with your team. No login. No database. No configuration.

---

## Features

- Create a retro board instantly — get a shareable URL
- Three columns: **What Went Well**, **What Didn't Go Well**, **Action Items**
- Add sticky notes to any column
- Upvote notes anonymously
- Delete notes
- Export the full board to Markdown
- JSON file storage — no database needed
- Self-hosted — run anywhere with Python

---

## Setup

**Requirements:** Python 3.10+

```bash
git clone https://github.com/2025sl93072/retroboard.git
cd retroboard
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in your browser.

---

## Usage

1. Open the app → type a board name → click **Create Board**
2. Share the URL with your team (click **⎘ Copy Link**)
3. Everyone adds notes to the three columns
4. Upvote the notes that matter most
5. Click **↓ Export** to download a Markdown summary

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Project Structure

```
retroboard/
├── app.py              # Flask backend
├── static/
│   ├── style.css       # All styling
│   └── app.js          # Frontend logic
├── templates/
│   ├── index.html      # Landing page
│   └── board.html      # Retro board
├── tests/
│   └── test_app.py     # Backend tests
├── boards/             # JSON board storage (auto-created, gitignored)
└── requirements.txt
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT License. See [LICENSE](LICENSE).

---

## Authors

- [2025sl93072](https://github.com/2025sl93072)
- [2025sl93094](https://github.com/2025sl93094)
