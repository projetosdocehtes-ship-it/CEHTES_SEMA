# email_service/views.py
from django.core.mail import send_mail
from django.http import JsonResponse


def send_email(request):
    subject = "Hello, Paulo"
    message = "Here is your message."
    email_from = "youremail@gmail.com"
    recipient_list = ["recipient@gmail.com"]

    send_mail(subject, message, email_from, recipient_list)

    return JsonResponse({"status": "Email sent"})
