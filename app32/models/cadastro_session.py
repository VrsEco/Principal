"""
Modelo para sessões de cadastro em andamento
Armazena dados coletados durante o processo de cadastro assistido

⚠️ PostgreSQL ONLY - SQLite não é suportado
Este sistema usa APENAS PostgreSQL conforme política do projeto
"""
from datetime import datetime
from . import db
from flask_login import current_user


class CadastroSession(db.Model):
    """
    Sessão de cadastro em andamento
    
    ⚠️ PostgreSQL ONLY - SQLite não é suportado
    Este modelo usa db.JSON que é tipo nativo PostgreSQL
    """
    
    __tablename__ = 'cadastro_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tipo_cadastro = db.Column(db.String(20), nullable=False)  # 'real' ou 'modelo'
    estado = db.Column(db.String(50), default='inicial')  # Estado atual do cadastro
    dados_coletados = db.Column(db.JSON, default={})  # PostgreSQL JSON type - SQLite não suportado
    empresa_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)  # Se continuando cadastro existente
    campo_atual = db.Column(db.String(50), nullable=True)  # Campo que está sendo preenchido
    progresso = db.Column(db.Integer, default=0)  # Percentual de progresso
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relacionamentos
    user = db.relationship('User', backref='cadastro_sessions')
    empresa = db.relationship('Company', backref='cadastro_sessions')
    
    def to_dict(self):
        """Serializa para dict"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'tipo_cadastro': self.tipo_cadastro,
            'estado': self.estado,
            'dados_coletados': self.dados_coletados or {},
            'empresa_id': self.empresa_id,
            'campo_atual': self.campo_atual,
            'progresso': self.progresso,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_dados(self, novos_dados: dict):
        """Atualiza dados coletados fazendo merge"""
        dados_atual = self.dados_coletados or {}
        dados_atual.update(novos_dados)
        self.dados_coletados = dados_atual
        self.updated_at = datetime.utcnow()
    
    @staticmethod
    def criar_sessao(user_id: int, tipo_cadastro: str, empresa_id: int = None) -> 'CadastroSession':
        """Cria nova sessão de cadastro"""
        session = CadastroSession(
            user_id=user_id,
            tipo_cadastro=tipo_cadastro,
            estado='inicial',
            dados_coletados={},
            empresa_id=empresa_id
        )
        db.session.add(session)
        db.session.commit()
        return session
    
    @staticmethod
    def buscar_sessao_ativa(user_id: int, tipo_cadastro: str = None) -> 'CadastroSession':
        """Busca sessão ativa do usuário"""
        query = CadastroSession.query.filter_by(
            user_id=user_id,
            is_deleted=False
        )
        
        if tipo_cadastro:
            query = query.filter_by(tipo_cadastro=tipo_cadastro)
        
        # Buscar a mais recente
        return query.order_by(CadastroSession.updated_at.desc()).first()
    
    @staticmethod
    def listar_sessoes_pendentes(user_id: int) -> list:
        """Lista todas as sessões pendentes do usuário"""
        sessoes = CadastroSession.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).order_by(CadastroSession.updated_at.desc()).all()
        
        return [s.to_dict() for s in sessoes]

