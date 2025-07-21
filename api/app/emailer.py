import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


GMAIL_TO_ADDRESS = "shreyas.jukanti@gmail.com"
GMAIL_FROM_ADDRESS = "ecologicaljourney.notify@gmail.com"
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_feedback_email(feedback: dict):
    msg = EmailMessage()
    msg["Subject"] = "🚨 New Feedback Received"
    msg["From"] = GMAIL_FROM_ADDRESS
    msg["To"] = GMAIL_TO_ADDRESS

    # Extract data
    text = feedback.get("text", "No message provided.")
    submitted_at_raw = feedback.get("submitted_at", datetime.utcnow())

    if submitted_at_raw.tzinfo is None:
        submitted_at_raw = submitted_at_raw.replace(tzinfo=ZoneInfo("UTC"))
    submitted_at_pacific = submitted_at_raw.astimezone(ZoneInfo("America/Los_Angeles"))
    submitted_at = submitted_at_pacific.strftime("%A, %B %d, %Y at %-I:%M %p %Z")

    # Build the HTML body
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.05);">
          <h2 style="color: #333;">📩 New Feedback Received</h2>
          <p><strong>Submitted at:</strong> {submitted_at}</p>
          <hr />
          <p style="font-size: 16px; color: #444;"><strong>Message:</strong><br />{text}</p>
        </div>
      </body>
    </html>
    """

    msg.set_content(
        f"New Feedback:\n\nMessage: {text}\nSubmitted at: {submitted_at}"
    )  # fallback plain text
    msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_FROM_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        print("✅ Feedback email sent.")
    except Exception as e:
        print("❌ Failed to send feedback email:", str(e))
