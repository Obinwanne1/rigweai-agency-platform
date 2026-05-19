import smtplib
import logging
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

log = logging.getLogger(__name__)


def _is_configured() -> bool:
    return bool(Config.SMTP_HOST and Config.SMTP_USER and Config.SMTP_PASS)


def _send(to: list[str], subject: str, html: str) -> None:
    if not _is_configured():
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.ehlo()
            if Config.SMTP_TLS:
                server.starttls()
            if Config.SMTP_USER and Config.SMTP_PASS:
                server.login(Config.SMTP_USER, Config.SMTP_PASS)
            server.sendmail(Config.SMTP_FROM, to, msg.as_string())
    except Exception:
        log.warning("Failed to send email '%s' to %s", subject, to)


def send_async(to: list[str], subject: str, html: str) -> None:
    """Fire-and-forget — does not block the request."""
    if not _is_configured():
        return
    threading.Thread(target=_send, args=(to, subject, html), daemon=True).start()


# ── Templates ──────────────────────────────────────────────────────────

def notify_new_request(client_name: str, req_type: str, prompt: str,
                        request_id: int, notify_emails: list[str]) -> None:
    if not notify_emails:
        return
    import html as _html
    subject = f"[RigweAI] New {req_type} request from {client_name}"
    dashboard_url = f"{Config.BASE_URL}/staff/projects"
    safe_name = _html.escape(client_name)
    safe_type = _html.escape(req_type.capitalize())
    safe_prompt = _html.escape(prompt[:500]) + ("…" if len(prompt) > 500 else "")
    body = f"""
    <div style="font-family:sans-serif; max-width:560px; margin:0 auto;">
      <div style="background:#448440; padding:20px 24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#fff; margin:0; font-size:1.1rem;">New Service Request</h2>
      </div>
      <div style="background:#f9f9f5; border:1px solid #d4d9c0; border-top:none;
                  border-radius:0 0 8px 8px; padding:24px;">
        <table style="width:100%; font-size:0.9rem; border-collapse:collapse;">
          <tr><td style="padding:6px 0; color:#666; width:120px;">Client</td>
              <td style="padding:6px 0; font-weight:600;">{safe_name}</td></tr>
          <tr><td style="padding:6px 0; color:#666;">Type</td>
              <td style="padding:6px 0;">{safe_type}</td></tr>
          <tr><td style="padding:6px 0; color:#666;">Request #</td>
              <td style="padding:6px 0;">#{request_id}</td></tr>
        </table>
        <div style="margin-top:16px; padding:12px 16px; background:#fff;
                    border:1px solid #d4d9c0; border-radius:6px;
                    font-size:0.88rem; color:#333; line-height:1.6;">
          <strong>Prompt:</strong><br>{safe_prompt}
        </div>
        <div style="margin-top:20px;">
          <a href="{dashboard_url}"
             style="background:#448440; color:#fff; padding:10px 18px;
                    border-radius:6px; text-decoration:none; font-size:0.88rem;">
            View in Dashboard →
          </a>
        </div>
      </div>
      <p style="font-size:0.75rem; color:#999; margin-top:12px; text-align:center;">
        RigweAI Agency Platform
      </p>
    </div>
    """
    send_async(notify_emails, subject, body)


def send_password_reset(to_email: str, name: str, token: str) -> bool:
    """Send password reset email. Returns True if sent, False if SMTP not configured."""
    if not _is_configured():
        return False
    import html as _html
    reset_url = f"{Config.BASE_URL}/reset-password?token={token}"
    safe_name = _html.escape(name)
    subject = "[RigweAI] Reset your password"
    body = f"""
    <div style="font-family:sans-serif; max-width:560px; margin:0 auto;">
      <div style="background:#407E3C; padding:20px 24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#fff; margin:0; font-size:1.1rem;">Password Reset Request</h2>
      </div>
      <div style="background:#f9f9f5; border:1px solid #d4d9c0; border-top:none;
                  border-radius:0 0 8px 8px; padding:24px;">
        <p style="font-size:0.9rem; color:#333;">Hi {safe_name},</p>
        <p style="font-size:0.9rem; color:#333; line-height:1.6;">
          We received a request to reset your RigweAI Agency password.
          Click the button below to set a new password. This link expires in <strong>1 hour</strong>.
        </p>
        <div style="margin:24px 0;">
          <a href="{reset_url}"
             style="background:#407E3C; color:#fff; padding:12px 24px;
                    border-radius:6px; text-decoration:none; font-size:0.9rem; font-weight:600;">
            Reset Password →
          </a>
        </div>
        <p style="font-size:0.82rem; color:#888; line-height:1.6;">
          If you didn't request this, ignore this email — your password won't change.
        </p>
      </div>
      <p style="font-size:0.75rem; color:#999; margin-top:12px; text-align:center;">
        RigweAI Agency Platform
      </p>
    </div>
    """
    send_async([to_email], subject, body)
    return True


def notify_request_completed(client_email: str, client_name: str,
                               req_type: str, request_id: int) -> None:
    import html as _html
    dashboard_url = f"{Config.BASE_URL}/client/dashboard"
    safe_name = _html.escape(client_name)
    safe_type = _html.escape(req_type)
    subject = f"[RigweAI] Your {req_type} request #{request_id} is ready"
    body = f"""
    <div style="font-family:sans-serif; max-width:560px; margin:0 auto;">
      <div style="background:#448440; padding:20px 24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#fff; margin:0; font-size:1.1rem;">Request Complete</h2>
      </div>
      <div style="background:#f9f9f5; border:1px solid #d4d9c0; border-top:none;
                  border-radius:0 0 8px 8px; padding:24px;">
        <p style="font-size:0.9rem; color:#333;">Hi {safe_name},</p>
        <p style="font-size:0.9rem; color:#333;">
          Your <strong>{safe_type}</strong> request <strong>#{request_id}</strong>
          has been completed. Log in to view the output.
        </p>
        <div style="margin-top:20px;">
          <a href="{dashboard_url}"
             style="background:#448440; color:#fff; padding:10px 18px;
                    border-radius:6px; text-decoration:none; font-size:0.88rem;">
            View Output →
          </a>
        </div>
      </div>
      <p style="font-size:0.75rem; color:#999; margin-top:12px; text-align:center;">
        RigweAI Agency Platform
      </p>
    </div>
    """
    send_async([client_email], subject, body)
