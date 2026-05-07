---
name: ai-agency-platform
description: Scaffold full-stack AI agency platform — Flask/SQLite/vanilla JS, JWT auth, Claude API, admin panel, staff portal, client portal.
---

## TRIGGER
Phrases: "build ai agency platform", "scaffold agency site", "create client portal with AI services", "deploy-agency-platform"

## PLATFORM OVERVIEW

Full-stack AI agency platform. Flask 3 + SQLite + vanilla JS. JWT auth with 3 roles.

**Stack:** Python 3.11+, Flask 3, SQLite, Anthropic SDK (`claude-sonnet-4-6`), vanilla JS/HTML/CSS, JWT in httpOnly cookie.

**Brand:** Primary `#407E3C` | Secondary `#FFFFFF` | Accent `#5a9e56`

---

## ROLES & ACCESS

| Role | Dashboard | Capabilities |
|------|-----------|-------------|
| Admin | `/admin/dashboard` | Full access: users, projects, requests, stats, AI tools |
| Staff | `/staff/dashboard` | Assigned projects, update request status/output |
| Client | `/client/dashboard` | Own projects, AI tools (chat, content gen, file processor) |

---

## FEATURES

### Admin
- Dashboard stats: total users, clients, staff, projects, requests, pending requests
- Create / list / update / deactivate / delete users (all roles)
- Create / list / update / delete projects (assign client + staff)
- View all service requests across all clients (last 100)

### Staff
- View assigned projects (admin sees all)
- View service requests per project
- Update request status (`pending` → `in_progress` → `completed` → `failed`)
- Set output text on completed requests
- Email notification sent to client on completion

### Client
- View own projects with assigned staff name
- Submit service requests (content / chat / file types)
- AI Content Generator: prompt + optional context → Claude-generated copy
- AI Chat: persistent multi-turn chat with Claude, titled conversation history
- File Processor: upload file → Claude analyzes/summarizes (PDF, DOCX, TXT, CSV, PNG, JPG, JPEG)

### Auth
- Login / logout with httpOnly JWT cookie
- Change password (requires current password)
- Forgot password page at `/forgot-password`
- Profile page at `/profile`
- Token expiry: 24h (configurable via `JWT_EXPIRY_HOURS`)
- Cookie `secure=True` in production, `False` in dev

---

## API ENDPOINTS

### Auth `/api/auth`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/login` | — | Login, sets JWT cookie |
| POST | `/logout` | Any | Clears JWT cookie |
| GET | `/me` | Any | Current user info |
| POST | `/change-password` | Any | Change own password |

### Admin `/api/admin`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/stats` | admin/staff | Dashboard counts |
| GET | `/users` | admin/staff | List all users |
| POST | `/users` | admin | Create user |
| PATCH | `/users/<id>` | admin | Update user (name/role/password/is_active) |
| DELETE | `/users/<id>` | admin | Delete user |
| GET | `/projects` | admin/staff | List all projects with client+staff names |
| POST | `/projects` | admin/staff | Create project |
| PATCH | `/projects/<id>` | admin/staff | Update project |
| DELETE | `/projects/<id>` | admin | Delete project |
| GET | `/requests` | admin/staff | List last 100 requests |

### Staff `/api/staff`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/projects` | admin/staff | List projects (scoped to staff's own) |
| GET | `/projects/<id>/requests` | admin/staff | Requests for a project |
| PATCH | `/requests/<id>` | admin/staff | Update request status/output |

### Client `/api/client`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/projects` | client/admin/staff | Own projects |
| GET | `/requests` | client/admin/staff | Own service requests |
| POST | `/requests` | client | Submit service request |
| GET | `/conversations` | client/admin | List chat conversations |

### AI Tools `/api/ai`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/generate` | any | Content generation (prompt + context) |
| POST | `/chat` | any | Multi-turn chat, saves conversation |
| GET | `/conversations/<id>` | any | Load conversation message history |
| POST | `/process-file` | any | Upload + analyze file with Claude |

---

## SECURITY FIXES (applied 2026-05-06)

| Fix | Location | Detail |
|-----|----------|--------|
| Template path traversal | `app.py` | `_safe_page()` guards `<path:page>` with `[a-zA-Z0-9_-]+` allowlist |
| Cookie secure flag | `routes/auth.py` | `secure=not Config.DEBUG` — prevents transmission over HTTP in prod |
| Cookie expiry sync | `routes/auth.py` | `max_age=Config.JWT_EXPIRY_HOURS * 3600` — tied to config, not hardcoded |
| DB connection leaks | All route files | `try/finally conn.close()` on every route across `admin`, `staff`, `client`, `auth`, `ai` |

---

## DB SCHEMA (SQLite)

- `users` — id, email, password_hash, name, role, is_active, created_at
- `projects` — id, client_id, staff_id, title, description, status, created_at
- `files` — id, user_id, filename, original_name, file_type, size, path, created_at
- `service_requests` — id, project_id, client_id, type, prompt, file_id, status, output_text, created_at
- `conversations` — id, client_id, title, messages (JSON), created_at, updated_at

---

## CHAT HISTORY BEHAVIOUR

- New conversation: title auto-set to first user message (60 char truncate + ellipsis)
- History list shows title + date + time (`toLocaleDateString()` + `toLocaleTimeString()`)
- Clicking a conversation fetches full message history via `GET /api/ai/conversations/<id>` and renders in UI
- Last 40 messages kept per conversation (token bloat prevention)

---

## SETUP

```bash
cd ai-agency-platform
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # Fill in ANTHROPIC_API_KEY and JWT_SECRET
python db/init_db.py
python app.py
```

Default admin: `admin@rigweai.com` / `admin123` — **change password after first login**

App runs at `http://localhost:5000`

---

## ENV VARS

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `JWT_SECRET` | Yes | — | Random 256-bit hex string |
| `FLASK_ENV` | No | `development` | Set `production` in prod |
| `PORT` | No | `5000` | Server port |
| `UPLOAD_MAX_MB` | No | `10` | Max file upload size |
| `SMTP_HOST` | No | — | Leave blank to disable email |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | No | — | SMTP username |
| `SMTP_PASS` | No | — | SMTP password |
| `SMTP_FROM` | No | `noreply@rigweai.com` | From address |
| `SMTP_TLS` | No | `true` | Enable STARTTLS |
| `NOTIFY_ADMIN_EMAIL` | No | — | Admin notification email |
