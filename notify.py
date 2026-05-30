"""
Sends a clickable email notification with the ngrok URL.
Called automatically by start_auto.bat after the tunnel is established.

Requires in .env:
    GMAIL_APP_PASSWORD=your_16_char_app_password
"""
import os
import sys
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FROM_EMAIL = 'trader.mo143@gmail.com'
TO_EMAIL   = 'trader.mo143@gmail.com'


def send_notification(url: str) -> bool:
    app_password = os.getenv('GMAIL_APP_PASSWORD', '').strip().replace(' ', '')
    if not app_password:
        print("GMAIL_APP_PASSWORD not set in .env — skipping email notification")
        return False

    # ── Plain text version ────────────────────────────────────────────────────
    plain = f"""Trading Agent is ready for today's review.

Open this URL from any browser, anywhere:

  {url}

Leave the username blank and enter your UI_PASSWORD.

Today's scan is complete. Charts and setups are ready for your approval.
"""

    # ── HTML version ──────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#0d1117;font-family:'Segoe UI',Arial,sans-serif;color:#c9d1d9;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="max-width:520px;margin:32px auto;background:#161b22;
                border:1px solid #30363d;border-radius:10px;overflow:hidden;">
    <tr>
      <td style="padding:28px 32px 20px;">
        <div style="font-size:1.3rem;font-weight:700;color:#f0f6ff;margin-bottom:6px;">
          ⬡ Trading Agent Ready
        </div>
        <div style="font-size:0.9rem;color:#8b949e;">
          Today's scan is complete. Your setups are waiting for review.
        </div>
      </td>
    </tr>
    <tr>
      <td style="padding:0 32px 28px;">
        <a href="{url}"
           style="display:inline-block;background:#238636;color:#ffffff;
                  text-decoration:none;padding:13px 28px;border-radius:7px;
                  font-size:1rem;font-weight:600;margin-bottom:18px;">
          Open Trading Agent →
        </a>
        <div style="font-size:0.8rem;color:#8b949e;margin-top:10px;">
          Or copy this URL into any browser:<br>
          <span style="color:#79b8ff;">{url}</span>
        </div>
        <div style="font-size:0.78rem;color:#8b949e;margin-top:14px;
                    padding-top:14px;border-top:1px solid #21262d;">
          Leave username blank · Enter your UI_PASSWORD
        </div>
      </td>
    </tr>
  </table>
</body>
</html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = '📈 Trading Agent Ready — Review Now'
    msg['From']    = FROM_EMAIL
    msg['To']      = TO_EMAIL
    msg.attach(MIMEText(plain, 'plain'))
    msg.attach(MIMEText(html,  'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(FROM_EMAIL, app_password)
            server.send_message(msg)
        print(f"Email sent to {TO_EMAIL}")
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False


if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:5000'
    success = send_notification(url)
    sys.exit(0 if success else 1)
