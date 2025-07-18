import os
import smtplib
from email.message import EmailMessage
from fastapi import BackgroundTasks
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

    content = f"New Feedback:\n\n{feedback}"
    msg.set_content(content)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_FROM_ADDRESS, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        print("✅ Feedback email sent.")
    except Exception as e:
        print("❌ Failed to send feedback email:", str(e))
