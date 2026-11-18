from django.contrib import admin

from apps.email_service.models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("id", "to", "subject", "body", "sent_at")
    list_filter = ("sent_at",)
