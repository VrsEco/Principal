"""Páginas públicas, sem autenticação, exigidas por integrações externas.

O Google exige URLs públicas de página inicial e de Política de Privacidade
para publicar apps OAuth. Estas rotas não leem sessão, banco nem dados de
cliente e precisam permanecer acessíveis a visitantes anônimos.
"""

from flask import Blueprint, render_template

public_pages_bp = Blueprint("public_pages", __name__)

PUBLIC_PAGE_ENDPOINTS = ("public_pages.privacy_policy",)


@public_pages_bp.get("/privacidade")
@public_pages_bp.get("/privacy")
def privacy_policy():
    return render_template("public/privacy_policy.html", last_updated="03/10/2026")
