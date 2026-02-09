import requests
from django.conf import settings
from email.utils import parseaddr


def send_brevo_email(to_email, subject, html_content):
    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    data = {
        "sender": {
            "name": "AI Interview Platform",
            # settings.DEFAULT_FROM_EMAIL can be either "name <email>" or "email"
            "email": (parseaddr(getattr(settings, "DEFAULT_FROM_EMAIL", ""))[1] or "aimockinterview07@gmail.com")
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": "AI Interview Platform Email"
    }

    response = requests.post(url, json=data, headers=headers)

    # 🔥 LOG RESPONSE
    print("BREVO STATUS:", response.status_code)
    print("BREVO RESPONSE:", response.text)

    return response.status_code == 201
