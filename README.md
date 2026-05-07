# RigweAI Agency Platform

Full-stack AI agency platform. Flask + SQLite + vanilla JS. JWT auth with 3 roles: Admin, Staff, Client.

## Setup

```bash
cd ai-agency-platform
python -m venv venv
# Windows:
venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your `ANTHROPIC_API_KEY`:

```
cp .env.example .env
```

## Initialize database

```bash
python db/init_db.py
```

Creates `agency.db` and seeds default admin:
- Email: `admin@rigweai.com`
- Password: `admin123`

**Change the admin password after first login.**

## Run

```bash
python app.py
```

App runs at `http://localhost:5000`

## Role routing

| Role | After login |
|---|---|
| Admin | `/admin/dashboard` |
| Staff | `/staff/dashboard` |
| Client | `/client/dashboard` |

## Features

- **Admin**: Create/manage users (all roles), create/assign projects, view all requests & stats
- **Staff**: View assigned projects, update service request status and output
- **Client**: View own projects, AI content generator, AI chat, file processor (PDF/DOCX/TXT/CSV/PNG/JPG)

## AI Tools (client-facing)

| Tool | Route | Description |
|---|---|---|
| Content Generator | `/client/content-gen` | Submit brief → Claude generates copy |
| AI Chat | `/client/chat` | Live chat with Claude, conversation history |
| File Processor | `/client/file-processor` | Upload file → Claude analyzes/summarizes |

## Tests

```bash
pytest tests/ -v
```

## Pages

| Route | Description |
|---|---|
| `/login` | Login |
| `/dashboard` | Role-based redirect |
| `/profile` | Change password / user info |
| `/forgot-password` | Forgot password |
| `/admin/<page>` | Admin portal pages |
| `/staff/<page>` | Staff portal pages |
| `/client/<page>` | Client portal pages |

## Environment Variables

| Key | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `JWT_SECRET` | Yes | — | Random 256-bit hex string |
| `FLASK_ENV` | No | `development` | Set `production` in prod |
| `PORT` | No | `5000` | Server port |
| `UPLOAD_MAX_MB` | No | `10` | Max file upload size (MB) |
| `SMTP_HOST` | No | — | SMTP server (leave blank to disable email) |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | — | SMTP username |
| `SMTP_PASS` | No | — | SMTP password |
| `SMTP_FROM` | No | `noreply@rigweai.com` | From address |
| `SMTP_TLS` | No | `true` | Enable STARTTLS |
| `NOTIFY_ADMIN_EMAIL` | No | — | Admin notification address |

## Stack

- Python 3.11+, Flask 3, SQLite
- `anthropic` SDK (claude-sonnet-4-6)
- Vanilla JS/HTML/CSS, no frontend build step
- JWT in httpOnly cookie (XSS-safe)
