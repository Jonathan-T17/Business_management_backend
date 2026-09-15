from types import SimpleNamespace

from django.core import mail
from users.utils import send_verification_email


def test_verification_email_uses_company_and_escapes_html(settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    user = SimpleNamespace(pk=123, email='invitee@example.test',
                           company=SimpleNamespace(name='Acme & <Partners>'))
    send_verification_email(user, 'test-token')
    message = mail.outbox[-1]
    assert 'Verify your account for Acme & <Partners>' in message.subject
    assert 'Welcome to Acme & <Partners>!' in message.body
    html = message.alternatives[0].content
    assert 'Welcome to Acme &amp; &lt;Partners&gt;' in html
    assert 'Welcome to SmartBiz AI' not in html
    assert '/verify-email/?uid=MTIz&token=test-token' in message.body
    assert message.to == [user.email]


def test_verification_email_without_company_keeps_platform_welcome(settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    user = SimpleNamespace(pk=124, email='platform@example.test', company=None)
    send_verification_email(user, 'test-token')
    assert mail.outbox[-1].subject == '[SmartBiz AI] Verify your account'
    assert 'Welcome to SmartBiz AI!' in mail.outbox[-1].body
