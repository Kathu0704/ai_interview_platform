import requests
from django.conf import settings


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
            "email": "noreply@brevo.com"
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    response = requests.post(url, json=data, headers=headers)
    print("BREVO STATUS:", response.status_code)
    print("BREVO RESPONSE:", response.text)

    return response.status_code == 201
