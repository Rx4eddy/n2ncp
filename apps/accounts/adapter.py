from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        from apps.notifications.models import EmailOutbox

        message = self.render_mail(template_prefix, email, context)
        EmailOutbox.objects.create(recipient=email, subject=message.subject, body=message.body)
