# RigweAI Agency Platform — Project Rules

## Stack
- Backend: Python 3.11+, Flask 3, SQLite
- Frontend: Vanilla JS/HTML/CSS (no build tools)
- AI: Anthropic SDK, model `claude-sonnet-4-6`
- Auth: JWT in httpOnly cookies

## Brand
- Primary: `#4B5320` | Secondary: `#FFFFFF` | Accent: `#6B7B3A`

## DB
- SQLite at `agency.db` (dev). Schema in `db/schema.sql`. Init via `python db/init_db.py`.
- Direct sqlite3 connections per-request (no ORM).

## Auth
- 3 roles: `admin`, `staff`, `client`
- `@require_role(*roles)` decorator in `middleware/auth_middleware.py`
- Admin: full access. Staff: full except user management. Client: own data + AI tools.

## Bug protocol
One bug at a time. Read → fix → verify. No batching.

## File uploads
Max 10MB. Allowed: pdf, docx, txt, csv, png, jpg, jpeg. Stored in `uploads/` (gitignored).

## Ports
Default: 5000. Read from `.env PORT=`.
