from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings
from datetime import datetime

conf = ConnectionConfig(
    MAIL_USERNAME=str(settings.MAIL_USERNAME),
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=str(settings.MAIL_FROM),
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS,
)

async def _send_mail(subject: str, recipients: list[str], body: str):
    try:
        fm = FastMail(conf)
        msg = MessageSchema(subject=subject, recipients=recipients, body=body, subtype="html")
        await fm.send_message(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        raise e

def generate_otp_email_html(otp: int) -> str:
    """
    Generate a styled HTML email for OTP (e.g., for password reset).
    Args:
        otp (int): The one-time password to include in the email.
    Returns:
        str: HTML email body.
    """
    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8" />
        <title>Password Reset OTP</title>
        <style>
          body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f8;
            margin: 0;
            padding: 0;
          }}
          .container {{
            max-width: 480px;
            margin: 40px auto;
            background-color: #ffffff;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            overflow: hidden;
          }}
          .header {{
            background-color: #007bff;
            color: white;
            text-align: center;
            padding: 16px;
            font-size: 20px;
            font-weight: bold;
          }}
          .content {{
            padding: 24px;
            color: #333333;
            line-height: 1.6;
          }}
          .otp {{
            font-size: 28px;
            font-weight: bold;
            color: #007bff;
            text-align: center;
            margin: 24px 0;
            letter-spacing: 4px;
          }}
          .note {{
            font-size: 14px;
            color: #666666;
            text-align: center;
          }}
          .footer {{
            background-color: #f0f2f5;
            text-align: center;
            padding: 12px;
            font-size: 12px;
            color: #888888;
          }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            Password Reset Request
          </div>
          <div class="content">
            <p>Dear User,</p>
            <p>
              We received a request to reset your password. Please use the following
              One-Time Password (OTP) to proceed:
            </p>
            <div class="otp">{otp:06d}</div>
            <p class="note">
              ⚠️ This OTP is valid for <b>10 minutes</b>.<br />
              Do not share it with anyone for your account’s safety.
            </p>
            <p>If you didn’t request this, you can safely ignore this email.</p>
          </div>
          <div class="footer">
            &copy; {datetime.now().year} True Style. All rights reserved.
          </div>
        </div>
      </body>
    </html>
    """
    return html