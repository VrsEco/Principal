"""
Módulo My Work - Gestão de Atividades Pessoais, de Equipe e Empresariais
"""
from flask import Blueprint

my_work_bp = Blueprint(
    'my_work',
    __name__,
    url_prefix='/my-work'
)

from . import routes

