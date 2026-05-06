import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


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
    except Exception as e:
        # Log but never crash the request
        print(f"[email] Failed to send '{subject}': {e}")


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
    subject = f"[RigweAI] New {req_type} request from {client_name}"
    html = f"""
    <div style="font-family:sans-serif; max-width:560px; margin:0 auto;">
      <div style="background:#448440; padding:20px 24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#fff; margin:0; font-size:1.1rem;">New Service Request</h2>
      </div>
      <div style="background:#f9f9f5; border:1px solid #d4d9c0; border-top:none;
                  border-radius:0 0 8px 8px; padding:24px;">
        <table style="width:100%; font-size:0.9rem; border-collapse:collapse;">
          <tr><td style="padding:6px 0; color:#666; width:120px;">Client</td>
              <td style="padding:6px 0; font-weight:600;">{client_name}</td></tr>
          <tr><td style="padding:6px 0; color:#666;">Type</td>
              <td style="padding:6px 0;">{req_type.capitalize()}</td></tr>
          <tr><td style="padding:6px 0; color:#666;">Request #</td>
              <td style="padding:6px 0;">#{request_id}</td></tr>
        </table>
        <div style="margin-top:16px; padding:12px 16px; background:#fff;
                    border:1px solid #d4d9c0; border-radius:6px;
                    font-size:0.88rem; color:#333; line-height:1.6;">
          <strong>Prompt:</strong><br>{prompt[:500]}{'…' if len(prompt) > 500 else ''}
        </div>
        <div style="margin-top:20px;">
          <a href="http://localhost:5000/staff/projects"
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
    send_async(notify_emails, subject, html)


def notify_request_completed(client_email: str, client_name: str,
                               req_type: str, request_id: int) -> None:
    subject = f"[RigweAI] Your {req_type} request #{request_id} is ready"
    html = f"""
    <div style="font-family:sans-serif; max-width:560px; margin:0 auto;">
      <div style="background:#448440; padding:20px 24px; border-radius:8px 8px 0 0;">
        <h2 style="color:#fff; margin:0; font-size:1.1rem;">Request Complete</h2>
      </div>
      <div style="background:#f9f9f5; border:1px solid #d4d9c0; border-top:none;
                  border-radius:0 0 8px 8px; padding:24px;">
        <p style="font-size:0.9rem; color:#333;">Hi {client_name},</p>
        <p style="font-size:0.9rem; color:#333;">
          Your <strong>{req_type}</strong> request <strong>#{request_id}</strong>
          has been completed. Log in to view the output.
        </p>
        <div style="margin-top:20px;">
          <a href="http://localhost:5000/client/dashboard"
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
    send_async([client_email], subject, html)
