import datetime

from django.db import models


class EmailLog(models.Model):
    to = models.EmailField()
    subject: str = models.CharField(max_length=255)
    body = models.TextField()
    sent_at: datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Email to {self.to} at {self.sent_at}"
