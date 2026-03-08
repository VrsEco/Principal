import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.email_service import EmailService


def test_send_email_autowraps_corporate_html(monkeypatch):
    service = EmailService()
    service.provider = "local"
    captured = {}

    def fake_send_local(to_emails, subject, body, html_body=None, attachments=None):
        captured["to_emails"] = to_emails
        captured["subject"] = subject
        captured["body"] = body
        captured["html_body"] = html_body
        captured["attachments"] = attachments
        return True

    monkeypatch.setattr(service, "_send_local_email", fake_send_local)

    sent = service.send_email(
        to_emails=["destinatario@empresa.com"],
        subject="Resumo operacional",
        body="Olá Fabiano,\n\n- Item 1\n- Item 2\n\nAtenciosamente,\nSapiens",
    )

    assert sent is True
    assert captured["to_emails"] == ["destinatario@empresa.com"]
    assert "Sapiens • Versus Gestão Corporativa" in captured["html_body"]
    assert "cid:versus_signature_logo" in captured["html_body"]
    assert "Resumo operacional" in captured["html_body"]
    assert "<ul" in captured["html_body"]
    assert "Mensagem automática enviada pelo Sapiens." in captured["html_body"]


def test_send_email_preserves_explicit_html(monkeypatch):
    service = EmailService()
    service.provider = "local"
    captured = {}

    def fake_send_local(to_emails, subject, body, html_body=None, attachments=None):
        captured["html_body"] = html_body
        return True

    monkeypatch.setattr(service, "_send_local_email", fake_send_local)

    sent = service.send_email(
        to_emails=["destinatario@empresa.com"],
        subject="Assunto",
        body="Texto puro",
        html_body="<html><body><p>HTML customizado</p></body></html>",
    )

    assert sent is True
    assert captured["html_body"] == "<html><body><p>HTML customizado</p></body></html>"


def test_send_welcome_email_uses_official_layout(monkeypatch):
    service = EmailService()
    captured = {}

    def fake_send_email(to_emails, subject, body, html_body=None, attachments=None):
        captured["to_emails"] = to_emails
        captured["subject"] = subject
        captured["body"] = body
        captured["html_body"] = html_body
        return True

    monkeypatch.setattr(service, "send_email", fake_send_email)

    sent = service.send_welcome_email(
        participant_email="novo@empresa.com",
        participant_name="Maria",
        plan_name="Plano 2026",
    )

    assert sent is True
    assert captured["to_emails"] == ["novo@empresa.com"]
    assert "Bem-vindo ao Planejamento Estratégico - Plano 2026" == captured["subject"]
    assert "Sapiens Versus" in captured["html_body"]
    assert "Versus Gestão Corporativa" in captured["html_body"]
    assert "cid:versus_signature_logo" in captured["html_body"]
    assert "Bem-vindo ao Planejamento Estratégico" in captured["html_body"]
