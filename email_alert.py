import smtplib
from email.message import EmailMessage
from datetime import datetime
import os

# Email server configuration (based on your PHP SMTP settings)
EMAIL_ADDRESS = "dummy@cse.iitk.ac.in"  # replace with your full email address
EMAIL_PASSWORD = "dummy"  # replace with your email password
SMTP_SERVER = "dummy.cse.iitk.ac.in"
SMTP_PORT = 587  # SSL port

# List of recipients — add all emails you want alerts sent to
RECIPIENTS = [
    "user1@cse.iitk.ac.in",
    "user2@cse.iitk.ac.in",
    "user3@cse.iitk.ac.in"
]

# video_dir , video_file , reason
def send_email_alert(video_file, reason):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f" Door Violation Detected: {reason}"
    body = (f"Violation detected!\n\n"
            f"Reason: {reason}\n"
            f"Timestamp: {timestamp}\n"
            #f"Video file: {os.path.join(video_dir, video_file)}\n\n"
            f"Please check immediately.")

    msg = EmailMessage()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = ", ".join(RECIPIENTS)
    msg['Subject'] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f" Alert email sent to {', '.join(RECIPIENTS)}")
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")
#send_email_alert("test.mp4","dog detected")