from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend

from apps.email_service.models import EmailLog


class LoggedEmailBackend(SmtpEmailBackend):
    def send_messages(self, email_messages):
        for message in email_messages:
            EmailLog.objects.create(
                to=", ".join(message.to),
                subject=message.subject,
                body=message.body,
            )
        return super().send_messages(email_messages)
