"""
Serviço de Agente de Cadastro - MVP
Fornece cadastro assistido e análise de completude de empresas
"""
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from models import db
from models.cadastro_session import CadastroSession
from models.company import Company
from models.user import User

logger = logging.getLogger(__name__)


class CadastroAgentService:
    """Serviço para cadastro assistido e análise de completude"""

    # Campos obrigatórios
    CAMPOS_OBRIGATORIOS = ['name', 'client_code']
    
    # Campos recomendados (alta prioridade)
    CAMPOS_RECOMENDADOS_ALTA = ['legal_name', 'cnpj', 'segment']
    
    # Campos recomendados (média prioridade)
    CAMPOS_RECOMENDADOS_MEDIA = ['city', 'state', 'coverage_physical', 'coverage_online']
    
    # Campos recomendados (baixa prioridade)
    CAMPOS_RECOMENDADOS_BAIXA = ['experience_total', 'experience_segment']
    
    # Campos opcionais (MVV)
    CAMPOS_OPCIONAIS = ['mission', 'vision', 'values']

    # Mapeamento de impactos
    IMPACTOS = {
        'name': {
            'criticidade': 'CRÍTICO',
            'impacto_pev': 'Bloqueia criação de empresa',
            'impacto_grv': 'Bloqueia criação de empresa',
            'impacto_relatorios': 'Bloqueia todos os relatórios',
            'recomendacao': 'Preencher imediatamente'
        },
        'client_code': {
            'criticidade': 'CRÍTICO',
            'impacto_pev': 'Bloqueia criação de empresa',
            'impacto_grv': 'Bloqueia criação de empresa',
            'impacto_relatorios': 'Bloqueia todos os relatórios',
            'recomendacao': 'Preencher imediatamente'
        },
        'legal_name': {
            'criticidade': 'ALTO',
            'impacto_pev': 'Relatórios formais incompletos',
            'impacto_grv': 'Documentação legal incompleta',
            'impacto_relatorios': 'Relatórios para stakeholders incompletos',
            'recomendacao': 'Preencher antes de gerar relatórios formais'
        },
        'cnpj': {
            'criticidade': 'ALTO',
            'impacto_pev': 'Análises fiscais e contábeis limitadas',
            'impacto_grv': 'Validação de dados fiscais impossível',
            'impacto_relatorios': 'Relatórios contábeis incompletos',
            'recomendacao': 'Preencher para análises fiscais completas'
        },
        'segment': {
            'criticidade': 'MÉDIO',
            'impacto_pev': 'Análises de mercado e benchmarking limitadas',
            'impacto_grv': 'Comparações setoriais impossíveis',
            'impacto_relatorios': 'Relatórios de mercado incompletos',
            'recomendacao': 'Preencher para análises setoriais'
        },
        'city': {
            'criticidade': 'MÉDIO',
            'impacto_pev': 'Análises regionais limitadas',
            'impacto_grv': 'Análises geográficas incompletas',
            'impacto_relatorios': 'Relatórios regionais incompletos',
            'recomendacao': 'Preencher para análises geográficas'
        },
        'state': {
            'criticidade': 'MÉDIO',
            'impacto_pev': 'Análises regionais limitadas',
            'impacto_grv': 'Análises geográficas incompletas',
            'impacto_relatorios': 'Relatórios regionais incompletos',
            'recomendacao': 'Preencher para análises geográficas'
        },
        'mission': {
            'criticidade': 'MÉDIO',
            'impacto_pev': 'Planejamento estratégico incompleto',
            'impacto_grv': 'Alinhamento de objetivos limitado',
            'impacto_relatorios': 'Relatórios estratégicos sem contexto de missão',
            'recomendacao': 'Preencher para PEV completo'
        },
        'vision': {
            'criticidade': 'MÉDIO',
            'impacto_pev': 'Planejamento estratégico sem visão de futuro',
            'impacto_grv': 'Objetivos de longo prazo não definidos',
            'impacto_relatorios': 'Relatórios estratégicos sem direcionamento',
            'recomendacao': 'Preencher para PEV completo'
        },
        'values': {
            'criticidade': 'BAIXO',
            'impacto_pev': 'Planejamento estratégico sem valores definidos',
            'impacto_grv': 'Alinhamento cultural limitado',
            'impacto_relatorios': 'Relatórios estratégicos sem valores',
            'recomendacao': 'Preencher quando possível'
        }
    }

    def __init__(self):
        """Inicializa o serviço"""
        pass

    def processar_conversa(self, mensagem: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa mensagem conversacional do usuário.
        
        Args:
            mensagem: Mensagem do usuário (texto livre)
            contexto: Contexto da conversa (estado, dados coletados, etc)
            
        Returns:
            Dict com resposta do agente
        """
        estado = contexto.get('estado', 'inicial')
        dados_coletados = dict(contexto.get('dados_coletados', {}))  # Criar cópia para não modificar o original
        tipo_cadastro = contexto.get('tipo_cadastro')
        
        mensagem_lower = mensagem.lower().strip()
        
        # Interpretar intenções do usuário
        if self._contem_palavra(mensagem_lower, ['pular', 'pule', 'skip', 'próximo', 'proximo']):
            resposta = self._pular_pergunta(estado, dados_coletados, tipo_cadastro)
        elif self._contem_palavra(mensagem_lower, ['o que falta', 'que falta', 'faltando', 'incompleto']):
            resposta = self._responder_o_que_falta(dados_coletados, contexto.get('empresa_id'))
        elif self._contem_palavra(mensagem_lower, ['impacto', 'afeta', 'consequência', 'consequencia']):
            resposta = self._responder_impacto(dados_coletados, contexto.get('empresa_id'))
        elif self._contem_palavra(
            mensagem_lower,
            [
                'testar sistema',
                'verificar sistema',
                'checar sistema',
                'diagnostico do sistema',
                'diagnóstico do sistema',
                'status do sistema',
                'status geral',
                'saude do sistema',
                'saúde do sistema',
                'testar funcionalidades',
                'diagnostico geral',
                'diagnóstico geral',
            ],
        ):
            resposta = self._diagnosticar_sistema(dados_coletados)
        elif self._contem_palavra(mensagem_lower, ['confirmar', 'confirmo', 'sim', 'correto', 'ok']):
            resposta = self._confirmar_dados(estado, dados_coletados, tipo_cadastro)
        # Processar por estado
        elif estado == 'cadastrando_usuario':
            resposta = self._processar_cadastro_usuario(mensagem, dados_coletados, tipo_cadastro)
        elif estado == 'aguardando_cnpj':
            resposta = self._processar_cnpj(mensagem, dados_coletados, tipo_cadastro)
        elif estado == 'aguardando_campo':
            campo = contexto.get('campo_atual')
            if campo:
                resposta = self._processar_resposta_campo(campo, mensagem, dados_coletados, tipo_cadastro)
            else:
                resposta = self._extrair_informacoes(mensagem, estado, dados_coletados, tipo_cadastro)
        else:
            # Estado padrão: tentar extrair informações
            resposta = self._extrair_informacoes(mensagem, estado, dados_coletados, tipo_cadastro)
        
        # Garantir que dados_coletados sempre seja retornado
        if 'dados_coletados' not in resposta:
            resposta['dados_coletados'] = dados_coletados
        
        return resposta

    def _contem_palavra(self, texto: str, palavras: List[str]) -> bool:
        """Verifica se texto contém alguma das palavras"""
        return any(palavra in texto for palavra in palavras)

    def _processar_cadastro_usuario(self, mensagem: str, dados_coletados: Dict, tipo_cadastro: str) -> Dict[str, Any]:
        """Processa cadastro de usuário"""
        # Extrair login e senha do formato "login:email@exemplo.com senha:senha123"
        login_match = re.search(r'login[:\s]+([^\s]+)', mensagem, re.IGNORECASE)
        senha_match = re.search(r'senha[:\s]+([^\s]+)', mensagem, re.IGNORECASE)
        
        if not login_match or not senha_match:
            return {
                'mensagem': 'Por favor, informe no formato: login:seu@email.com senha:suasenha',
                'estado': 'cadastrando_usuario',
                'dados_coletados': dados_coletados
            }
        
        email = login_match.group(1).strip()
        senha = senha_match.group(1).strip()
        
        # Validar email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return {
                'mensagem': 'Email inválido. Por favor, informe um email válido.',
                'estado': 'cadastrando_usuario',
                'dados_coletados': dados_coletados
            }
        
        # Validar senha
        if len(senha) < 6:
            return {
                'mensagem': 'Senha deve ter pelo menos 6 caracteres.',
                'estado': 'cadastrando_usuario',
                'dados_coletados': dados_coletados
            }
        
        # Criar usuário
        try:
            from services.user_employee_service import UserEmployeeService
            from models.user import User
            
            # Verificar se usuário já existe
            usuario_existente = User.query.filter_by(email=email).first()
            if usuario_existente:
                return {
                    'mensagem': f'Usuário com email {email} já existe. Deseja usar este usuário ou informar outro?',
                    'estado': 'usuario_existente',
                    'dados_coletados': dados_coletados,
                    'opcoes': [
                        { 'text': 'Usar este usuário', 'action': 'usar_usuario_existente' },
                        { 'text': 'Informar outro email', 'action': 'novo_email' }
                    ]
                }
            
            # Criar usuário temporário (será vinculado à empresa depois)
            dados_coletados['usuario'] = {
                'email': email,
                'senha': senha,
                'name': email.split('@')[0]  # Nome padrão do email
            }
            
            return {
                'mensagem': f'✅ Usuário {email} será criado. Agora vamos cadastrar a empresa. Digite o CNPJ da empresa:',
                'estado': 'aguardando_cnpj',
                'dados_coletados': dados_coletados
            }
        except Exception as e:
            logger.error(f"Erro ao processar cadastro de usuário: {e}")
            return {
                'mensagem': f'Erro ao processar: {str(e)}. Tente novamente.',
                'estado': 'cadastrando_usuario',
                'dados_coletados': dados_coletados
            }

    def _processar_cnpj(self, mensagem: str, dados_coletados: Dict, tipo_cadastro: str) -> Dict[str, Any]:
        """Processa CNPJ e busca dados na internet"""
        cnpj_limpo = self._limpar_cnpj(mensagem)
        
        if not cnpj_limpo or len(cnpj_limpo) != 14:
            return {
                'mensagem': 'CNPJ inválido. Por favor, digite um CNPJ válido (14 dígitos).',
                'estado': 'aguardando_cnpj'
            }
        
        if not self._validar_cnpj_digitos(cnpj_limpo):
            return {
                'mensagem': 'CNPJ inválido (dígitos verificadores incorretos). Por favor, verifique o CNPJ.',
                'estado': 'aguardando_cnpj'
            }
        
        # Buscar dados do CNPJ
        dados_empresa = self._buscar_dados_cnpj(cnpj_limpo)
        
        if dados_empresa:
            # Gerar código alfanumérico automático
            codigo = self._gerar_codigo_alfanumerico()
            
            # Mesclar dados da empresa com dados coletados
            dados_coletados['cnpj'] = cnpj_limpo
            dados_coletados['client_code'] = codigo
            dados_coletados['name'] = dados_empresa.get('name', '')
            dados_coletados['legal_name'] = dados_empresa.get('legal_name', '')
            dados_coletados['city'] = dados_empresa.get('city', '')
            dados_coletados['state'] = dados_empresa.get('state', '')
            dados_coletados['segment'] = dados_empresa.get('segment', '')
            
            return {
                'mensagem': f'✅ Encontrei os dados da empresa! Código gerado automaticamente: **{codigo}**\n\nConfirme os dados abaixo:',
                'estado': 'confirmando_dados_empresa',
                'dados_coletados': dados_coletados,
                'dados_preview': {
                    'Razão Social': dados_empresa.get('legal_name', 'N/A'),
                    'Nome Fantasia': dados_empresa.get('name', 'N/A'),
                    'CNPJ': self._formatar_cnpj(cnpj_limpo),
                    'Código Cliente': codigo,
                    'Cidade': dados_empresa.get('city', 'N/A'),
                    'Estado': dados_empresa.get('state', 'N/A')
                },
                'acoes': [
                    { 'text': '✅ Confirmar', 'action': 'confirmar_dados_empresa', 'type': 'primary', 'data': dados_coletados },
                    { 'text': '✏️ Editar', 'action': 'editar_dados_empresa', 'type': 'secondary' }
                ]
            }
        else:
            # Se não encontrou, pedir dados manualmente
            codigo = self._gerar_codigo_alfanumerico()
            dados_coletados['cnpj'] = cnpj_limpo
            dados_coletados['client_code'] = codigo
            
            return {
                'mensagem': f'Não consegui encontrar os dados automaticamente. Código gerado: **{codigo}**. Vamos preencher manualmente. Qual é o nome fantasia da empresa?',
                'estado': 'aguardando_campo',
                'campo_atual': 'name',
                'dados_coletados': dados_coletados.copy()  # Retornar cópia para garantir que não seja modificado
            }

    def _buscar_dados_cnpj(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Busca dados da empresa por CNPJ na internet.
        Usa API pública (ex: ReceitaWS, BrasilAPI, etc)
        """
        try:
            import requests
            
            # Tentar ReceitaWS (gratuita, mas com limite)
            try:
                url = f'https://www.receitaws.com.br/v1/{cnpj}'
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') != 'ERROR':
                        return {
                            'name': data.get('fantasia') or data.get('nome', ''),
                            'legal_name': data.get('nome', ''),
                            'cnpj': cnpj,
                            'city': data.get('municipio', ''),
                            'state': data.get('uf', ''),
                            'segment': data.get('atividade_principal', [{}])[0].get('text', '') if data.get('atividade_principal') else ''
                        }
            except Exception as e:
                logger.warning(f"Erro ao buscar na ReceitaWS: {e}")
            
            # Tentar BrasilAPI como fallback
            try:
                url = f'https://brasilapi.com.br/api/cnpj/v1/{cnpj}'
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'name': data.get('fantasia') or data.get('razao_social', ''),
                        'legal_name': data.get('razao_social', ''),
                        'cnpj': cnpj,
                        'city': data.get('municipio', ''),
                        'state': data.get('uf', ''),
                        'segment': data.get('cnae_fiscal', {}).get('descricao', '') if data.get('cnae_fiscal') else ''
                    }
            except Exception as e:
                logger.warning(f"Erro ao buscar na BrasilAPI: {e}")
            
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar dados do CNPJ: {e}")
            return None

    def _gerar_codigo_alfanumerico(self) -> str:
        """Gera código alfanumérico automático (3 caracteres)"""
        import random
        import string
        
        # Gerar código único
        # Limitar tentativas para evitar loop infinito
        max_tentativas = 100
        tentativas = 0
        
        while tentativas < max_tentativas:
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
            
            # Verificar se já existe (com tratamento de erro)
            try:
                from config_database import get_db
                db_helper = get_db()
                empresas = db_helper.get_companies()
                
                codigos_existentes = [e.get('client_code') for e in empresas if e.get('client_code')]
                if codigo not in codigos_existentes:
                    return codigo
            except Exception as e:
                logger.warning(f"Erro ao verificar código existente: {e}. Usando código gerado.")
                return codigo  # Se der erro, retorna o código mesmo assim
            
            tentativas += 1
        
        # Se não encontrou código único após muitas tentativas, retorna um com timestamp
        import time
        return f"{''.join(random.choices(string.ascii_uppercase, k=2))}{int(time.time()) % 1000}"

    def _formatar_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ com máscara"""
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

    def _pular_pergunta(self, estado: str, dados_coletados: Dict, tipo_cadastro: str) -> Dict[str, Any]:
        """Pula a pergunta atual e vai para a próxima"""
        proximo_campo = self._identificar_proximo_campo(dados_coletados)
        
        if proximo_campo:
            return {
                'mensagem': f'Ok, pulando. {self._gerar_mensagem_solicitacao(proximo_campo, tipo_cadastro)}',
                'estado': 'aguardando_campo',
                'campo_atual': proximo_campo,
                'dados_coletados': dados_coletados
            }
        else:
            return {
                'mensagem': 'Todos os campos obrigatórios foram coletados. Deseja finalizar o cadastro?',
                'estado': 'pronto_para_finalizar',
                'dados_coletados': dados_coletados,
                'acoes': [
                    { 'text': '✅ Finalizar', 'action': 'finalizar_cadastro', 'type': 'primary' },
                    { 'text': '➕ Adicionar mais dados', 'action': 'adicionar_dados_opcionais', 'type': 'secondary' }
                ]
            }

    def _responder_o_que_falta(self, dados_coletados: Dict, empresa_id: Optional[int] = None) -> Dict[str, Any]:
        """Responde o que está faltando no cadastro"""
        if empresa_id:
            # Analisar empresa existente
            analise = self.analisar_completude(empresa_id)
            if analise['status'] == 'sucesso':
                faltantes = analise['campos_faltantes']
                mensagem = '📋 **Campos faltantes:**\n\n'
                
                if faltantes.get('obrigatorios'):
                    mensagem += '🔴 **Obrigatórios:**\n'
                    for campo in faltantes['obrigatorios']:
                        mensagem += f'  • {self._obter_nome_campo(campo)}\n'
                
                if faltantes.get('recomendados_alta'):
                    mensagem += '\n🟠 **Recomendados (Alta):**\n'
                    for campo in faltantes['recomendados_alta']:
                        mensagem += f'  • {self._obter_nome_campo(campo)}\n'
                
                return {
                    'mensagem': mensagem,
                    'estado': 'respondendo_duvida',
                    'dados_coletados': dados_coletados
                }
        else:
            # Analisar dados coletados no momento
            faltantes = []
            for campo in self.CAMPOS_OBRIGATORIOS:
                if campo not in dados_coletados or not dados_coletados[campo]:
                    faltantes.append(campo)
            
            if faltantes:
                mensagem = '📋 **Ainda falta preencher:**\n\n'
                for campo in faltantes:
                    mensagem += f'  • {self._obter_nome_campo(campo)}\n'
                return {
                    'mensagem': mensagem,
                    'estado': 'respondendo_duvida',
                    'dados_coletados': dados_coletados
                }
            else:
                return {
                    'mensagem': '✅ Todos os campos obrigatórios já foram preenchidos!',
                    'estado': 'respondendo_duvida',
                    'dados_coletados': dados_coletados
                }

    def _responder_impacto(self, dados_coletados: Dict, empresa_id: Optional[int] = None) -> Dict[str, Any]:
        """Responde sobre o impacto dos dados faltantes"""
        if empresa_id:
            analise = self.analisar_completude(empresa_id)
            if analise['status'] == 'sucesso':
                impactos = analise.get('impactos', {})
                mensagem = '📊 **Impactos dos dados faltantes:**\n\n'
                
                for campo, impacto in impactos.items():
                    mensagem += f'**{self._obter_nome_campo(campo)}:**\n'
                    mensagem += f'  • Criticidade: {impacto.get("criticidade", "N/A")}\n'
                    mensagem += f'  • Impacto PEV: {impacto.get("impacto_pev", "N/A")}\n'
                    mensagem += f'  • Impacto GRV: {impacto.get("impacto_grv", "N/A")}\n'
                    mensagem += f'  • Impacto Relatórios: {impacto.get("impacto_relatorios", "N/A")}\n\n'
                
                return {
                    'mensagem': mensagem,
                    'estado': 'respondendo_duvida',
                    'dados_coletados': dados_coletados
                }
        
        return {
            'mensagem': 'Para analisar impactos, preciso de uma empresa cadastrada. Deseja continuar o cadastro?',
            'estado': 'respondendo_duvida',
            'dados_coletados': dados_coletados
        }

    def _diagnosticar_sistema(self, dados_coletados: Dict) -> Dict[str, Any]:
        """Executa um rápido diagnóstico do sistema disponível via agente"""
        checks: List[Dict[str, str]] = []
        healthy = True

        def add_check(title: str, status: str, detail: str) -> None:
            nonlocal healthy
            checks.append({'title': title, 'status': status, 'detail': detail})
            if status != 'ok':
                healthy = False

        # Verifica a conexão com o banco
        try:
            db.session.execute("SELECT 1")
            add_check("Banco de dados", "ok", "Conexão ativa e responsiva")
        except Exception as exc:
            db.session.rollback()
            add_check("Banco de dados", "fail", f"Erro de conexão: {exc}")

        # Verifica se há usuários cadastrados
        try:
            total_users = User.query.count()
            if total_users:
                add_check("Usuários cadastrados", "ok", f"{total_users} usuário(s) disponível(eis)")
            else:
                add_check(
                    "Usuários cadastrados",
                    "warn",
                    "Nenhum usuário encontrado. Cadastre ao menos um admin antes de continuar.",
                )
        except Exception as exc:
            db.session.rollback()
            add_check("Usuários cadastrados", "fail", f"Erro ao consultar usuários: {exc}")

        # Verifica se há empresas ativas
        try:
            total_companies = Company.query.count()
            if total_companies:
                add_check("Empresas cadastradas", "ok", f"{total_companies} empresa(s) registrada(s)")
            else:
                add_check(
                    "Empresas cadastradas",
                    "warn",
                    "Nenhuma empresa cadastrada. Crie ao menos uma empresa para começar.",
                )
        except Exception as exc:
            db.session.rollback()
            add_check("Empresas cadastradas", "fail", f"Erro ao consultar empresas: {exc}")

        # Verifica sessões de cadastro pendentes
        try:
            pendentes = CadastroSession.query.filter_by(is_deleted=False).count()
            detalhe = (
                f"{pendentes} sessão(ões) pendente(s)"
                if pendentes
                else "Nenhuma sessão pendente encontrada"
            )
            add_check("Sessões de cadastro", "ok", detalhe)
        except Exception as exc:
            db.session.rollback()
            add_check("Sessões de cadastro", "fail", f"Erro ao acessar sessões: {exc}")

        lines = ["🔍 Diagnóstico do sistema:", ""]
        for check in checks:
            emoji = {
                'ok': '✅',
                'warn': '⚠️',
                'fail': '❌'
            }.get(check['status'], 'ℹ️')
            lines.append(f"{emoji} {check['title']}: {check['detail']}")

        lines.append("")
        lines.append(
            "✅ Tudo pronto para continuar os cadastros."
            if healthy
            else "⚠️ Algumas verificações precisam ser revisadas antes de seguir."
        )

        return {
            'mensagem': "\n".join(lines),
            'estado': 'respondendo_duvida',
            'dados_coletados': dados_coletados,
            'diagnostico': checks,
        }

    def _obter_nome_campo(self, campo: str) -> str:
        """Retorna nome amigável do campo"""
        nomes = {
            'name': 'Nome Fantasia',
            'client_code': 'Código do Cliente',
            'legal_name': 'Razão Social',
            'cnpj': 'CNPJ',
            'segment': 'Segmento',
            'city': 'Cidade',
            'state': 'Estado'
        }
        return nomes.get(campo, campo)

    def _processar_resposta_campo(self, campo: str, valor: str, dados_coletados: Dict, tipo_cadastro: str) -> Dict[str, Any]:
        """Processa resposta para um campo específico"""
        validacao = self._validar_campo(campo, valor)
        
        if not validacao['valido']:
            return {
                'mensagem': f'❌ {validacao["mensagem"]}',
                'estado': 'aguardando_campo',
                'campo_atual': campo,
                'dados_coletados': dados_coletados
            }
        
        dados_coletados[campo] = valor.strip() if isinstance(valor, str) else valor
        proximo_campo = self._identificar_proximo_campo(dados_coletados)
        
        if proximo_campo:
            return {
                'mensagem': f'✅ {self._obter_nome_campo(campo)} salvo! {self._gerar_mensagem_solicitacao(proximo_campo, tipo_cadastro)}',
                'estado': 'aguardando_campo',
                'campo_atual': proximo_campo,
                'dados_coletados': dados_coletados
            }
        else:
            return {
                'mensagem': '✅ Todos os campos obrigatórios foram coletados! Deseja finalizar o cadastro?',
                'estado': 'pronto_para_finalizar',
                'dados_coletados': dados_coletados,
                'acoes': [
                    { 'text': '✅ Finalizar', 'action': 'finalizar_cadastro', 'type': 'primary' }
                ]
            }

    def _extrair_informacoes(self, mensagem: str, estado: str, dados_coletados: Dict, tipo_cadastro: str) -> Dict[str, Any]:
        """Tenta extrair informações da mensagem livre"""
        # Tentar identificar CNPJ
        cnpj_match = re.search(r'\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}', mensagem)
        if cnpj_match:
            return self._processar_cnpj(cnpj_match.group(0), dados_coletados, tipo_cadastro)
        
        # Se está aguardando um campo, tentar usar a mensagem como resposta
        if estado == 'aguardando_campo':
            campo = dados_coletados.get('campo_atual')
            if campo:
                return self._processar_resposta_campo(campo, mensagem, dados_coletados, tipo_cadastro)
        
        # Se está cadastrando colaboradores
        if estado == 'cadastrando_colaboradores':
            return self._processar_colaborador(mensagem, dados_coletados, tipo_cadastro)
        
        return {
            'mensagem': 'Não entendi. Você pode reformular sua pergunta ou escolher uma opção acima?',
            'estado': estado,
            'dados_coletados': dados_coletados
        }

    def _processar_colaborador(self, mensagem: str, dados_coletados: Dict, tipo_cadastro: str) -> Dict[str, Any]:
        """Processa cadastro de colaborador"""
        # Extrair nome do colaborador
        nome_match = re.search(r'nome[:\s]+([^\n]+)', mensagem, re.IGNORECASE)
        if not nome_match:
            # Tentar pegar o nome diretamente
            nome = mensagem.strip()
        else:
            nome = nome_match.group(1).strip()
        
        if not nome or len(nome) < 2:
            return {
                'mensagem': 'Por favor, informe o nome do colaborador.',
                'estado': 'cadastrando_colaboradores',
                'dados_coletados': dados_coletados
            }
        
        # Verificar se quer vincular com usuário
        vincular_match = re.search(r'(sim|não|nao|s|n)', mensagem.lower())
        vincular = vincular_match and vincular_match.group(1) in ['sim', 's']
        
        colaborador = {
            'name': nome,
            'vincular_usuario': vincular
        }
        
        if 'colaboradores' not in dados_coletados:
            dados_coletados['colaboradores'] = []
        
        dados_coletados['colaboradores'].append(colaborador)
        
        return {
            'mensagem': f'✅ Colaborador "{nome}" adicionado! Deseja adicionar mais colaboradores? (sim/não)',
            'estado': 'perguntando_mais_colaboradores',
            'dados_coletados': dados_coletados
        }

    def continuar_cadastro_empresa(self, empresa_id: int) -> Dict[str, Any]:
        """Continua cadastro de uma empresa existente"""
        try:
            company = Company.query.get(empresa_id)
            if not company:
                return {
                    'mensagem': 'Empresa não encontrada.',
                    'estado': 'erro'
                }
            
            # Analisar o que falta
            validacao = self._validar_completude(company, [])
            faltantes = validacao['campos_faltantes']
            
            # Converter empresa para dict
            dados_coletados = {
                'name': company.name,
                'client_code': getattr(company, 'client_code', None),
                'legal_name': company.legal_name,
                'cnpj': company.cnpj,
                'segment': company.segment,
                'city': company.city,
                'state': company.state
            }
            
            # Identificar próximo campo faltante
            proximo_campo = None
            if faltantes.get('obrigatorios'):
                proximo_campo = faltantes['obrigatorios'][0]
            elif faltantes.get('recomendados_alta'):
                proximo_campo = faltantes['recomendados_alta'][0]
            
            if proximo_campo:
                return {
                    'mensagem': f'Vamos continuar o cadastro de "{company.name}". Falta preencher: {self._obter_nome_campo(proximo_campo)}. {self._gerar_mensagem_solicitacao(proximo_campo, "real")}',
                    'estado': 'aguardando_campo',
                    'campo_atual': proximo_campo,
                    'dados_coletados': dados_coletados,
                    'empresa_id': empresa_id
                }
            else:
                return {
                    'mensagem': f'✅ O cadastro de "{company.name}" está completo! Todos os campos obrigatórios foram preenchidos.',
                    'estado': 'cadastro_completo',
                    'empresa_id': empresa_id
                }
        except Exception as e:
            logger.error(f"Erro ao continuar cadastro: {e}")
            return {
                'mensagem': f'Erro ao continuar cadastro: {str(e)}',
                'estado': 'erro'
            }

    def _confirmar_dados(self, estado: str, dados_coletados: Dict, tipo_cadastro: str) -> Dict[str, Any]:
        """Confirma dados e avança"""
        if estado == 'confirmando_dados_empresa':
            # Dados já estão em dados_coletados, avançar para próximo passo
            proximo_campo = self._identificar_proximo_campo(dados_coletados)
            
            if proximo_campo:
                return {
                    'mensagem': f'✅ Dados confirmados! {self._gerar_mensagem_solicitacao(proximo_campo, tipo_cadastro)}',
                    'estado': 'aguardando_campo',
                    'campo_atual': proximo_campo,
                    'dados_coletados': dados_coletados
                }
            else:
                return {
                    'mensagem': '✅ Dados confirmados! Deseja finalizar o cadastro?',
                    'estado': 'pronto_para_finalizar',
                    'dados_coletados': dados_coletados,
                    'acoes': [
                        { 'text': '✅ Finalizar', 'action': 'finalizar_cadastro', 'type': 'primary' }
                    ]
                }
        
        return {
            'mensagem': 'Confirmação processada. Continuando...',
            'estado': estado,
            'dados_coletados': dados_coletados
        }

    def listar_cadastros_pendentes(self) -> List[Dict[str, Any]]:
        """Lista cadastros em andamento"""
        try:
            # Buscar empresas incompletas (sem todos os campos obrigatórios)
            empresas = Company.query.filter(
                Company.name.isnot(None)
            ).all()
            
            cadastros = []
            for empresa in empresas:
                # Verificar completude
                validacao = self._validar_completude(empresa, [])
                if not validacao['completo']:
                    percentual = self._calcular_percentual_completude(empresa, [])
                    cadastros.append({
                        'id': empresa.id,
                        'empresa_nome': empresa.name,
                        'progresso': percentual,
                        'campos_faltantes': len(validacao['campos_faltantes']['obrigatorios'])
                    })
            
            return cadastros
        except Exception as e:
            logger.error(f"Erro ao listar cadastros pendentes: {e}")
            return []

    def finalizar_cadastro_completo(self, dados_coletados: Dict, tipo_cadastro: str, session_id: int = None) -> Dict[str, Any]:
        """
        Finaliza cadastro completo: cria usuário + empresa + employee
        
        Args:
            dados_coletados: Dados coletados durante o cadastro
            tipo_cadastro: Tipo de cadastro ('real' ou 'modelo')
            session_id: ID da sessão (opcional, para marcar como concluída)
        """
        try:
            from services.user_employee_service import UserEmployeeService
            from models.cadastro_session import CadastroSession
            
            # Validar dados obrigatórios
            if 'usuario' not in dados_coletados:
                return {
                    'status': 'erro',
                    'mensagem': 'Dados do usuário não encontrados'
                }
            
            usuario_data = dados_coletados['usuario']
            
            # Validar empresa
            if 'name' not in dados_coletados or not dados_coletados['name']:
                return {
                    'status': 'erro',
                    'mensagem': 'Nome da empresa é obrigatório'
                }
            
            if 'client_code' not in dados_coletados or not dados_coletados['client_code']:
                return {
                    'status': 'erro',
                    'mensagem': 'Código do cliente é obrigatório'
                }
            
            # Preparar dados da empresa para create_company (usa 'industry')
            company_data_db = {
                'name': dados_coletados['name'].strip(),
                'client_code': dados_coletados['client_code'].strip().upper(),
                'legal_name': dados_coletados.get('legal_name', '').strip() or None,
                'industry': dados_coletados.get('segment', '').strip() or None,  # create_company usa 'industry'
                'size': None,
                'description': None
            }
            
            # Criar empresa primeiro usando create_company para garantir client_code
            from config_database import get_db
            db_helper = get_db()
            
            # Criar empresa via database helper
            company_id = db_helper.create_company(company_data_db)
            
            if not company_id:
                return {
                    'status': 'erro',
                    'mensagem': 'Erro ao criar empresa'
                }
            
            # Buscar empresa criada
            company = Company.query.get(company_id)
            if not company:
                return {
                    'status': 'erro',
                    'mensagem': 'Empresa criada mas não encontrada'
                }
            
            # Atualizar campos adicionais (CNPJ, cidade, estado, etc)
            company.cnpj = dados_coletados.get('cnpj') or None
            company.city = dados_coletados.get('city', '').strip() or None
            company.state = dados_coletados.get('state', '').strip() or None
            company.coverage_physical = dados_coletados.get('coverage_physical') or None
            company.coverage_online = dados_coletados.get('coverage_online') or None
            company.experience_total = dados_coletados.get('experience_total') or None
            company.experience_segment = dados_coletados.get('experience_segment') or None
            company.mission = dados_coletados.get('mission') or None
            company.vision = dados_coletados.get('vision') or None
            company.values = dados_coletados.get('values') or None
            db.session.commit()
            
            # Criar usuário
            from models.user import User
            from models.employee import Employee
            
            user = User(
                name=usuario_data.get('name', usuario_data['email'].split('@')[0]),
                email=usuario_data['email'],
                role='client'
            )
            user.set_password(usuario_data['senha'])
            db.session.add(user)
            db.session.flush()
            
            # Criar employee
            employee = Employee(
                user_id=user.id,
                company_id=company.id,
                name=user.name,
                email=user.email,
                status='active'
            )
            db.session.add(employee)
            db.session.commit()
            
            # Marcar sessão como concluída se fornecida
            if session_id:
                try:
                    from models.cadastro_session import CadastroSession
                    session = CadastroSession.query.get(session_id)
                    if session:
                        session.is_deleted = True  # Soft delete
                        db.session.commit()
                except Exception as e:
                    logger.warning(f"Erro ao marcar sessão como concluída: {e}")
            
            return {
                'status': 'sucesso',
                'mensagem': f'✅ Cadastro completo realizado com sucesso!\n\nUsuário: {user.email}\nEmpresa: {company.name}\nCódigo: {company_data_db["client_code"]}',
                'usuario_id': user.id,
                'empresa_id': company.id,
                'employee_id': employee.id,
                'proximos_passos': [
                    'Cadastrar colaboradores adicionais',
                    'Criar plano estratégico (PEV)',
                    'Configurar indicadores e métricas'
                ]
            }
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao finalizar cadastro completo: {e}")
            return {
                'status': 'erro',
                'mensagem': f'Erro ao finalizar cadastro: {str(e)}'
            }

    def iniciar_cadastro(self, tipo: str = 'real', dados_iniciais: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Inicia processo de cadastro guiado.
        
        Args:
            tipo: 'exemplo' ou 'real'
            dados_iniciais: Dict com dados já conhecidos (opcional)
            
        Returns:
            Dict com status e próximo passo
        """
        dados_coletados = dados_iniciais or {}
        
        # Identificar próximo campo a solicitar
        proximo_campo = self._identificar_proximo_campo(dados_coletados)
        
        if proximo_campo:
            return {
                'status': 'coletando_dados',
                'tipo': tipo,
                'proximo_campo': proximo_campo,
                'mensagem': self._gerar_mensagem_solicitacao(proximo_campo, tipo),
                'dados_coletados': dados_coletados,
                'progresso': self._calcular_progresso(dados_coletados)
            }
        else:
            # Todos os dados obrigatórios coletados, pode finalizar
            return {
                'status': 'pronto_para_criar',
                'tipo': tipo,
                'dados_coletados': dados_coletados,
                'mensagem': 'Todos os dados obrigatórios foram coletados. Deseja criar a empresa agora?',
                'progresso': 100
            }

    def processar_resposta(self, dados_coletados: Dict, campo: str, valor: Any, tipo: str = 'real') -> Dict[str, Any]:
        """
        Processa resposta do usuário para um campo específico.
        
        Args:
            dados_coletados: Dict com dados já coletados
            campo: Nome do campo sendo preenchido
            valor: Valor fornecido pelo usuário
            tipo: 'exemplo' ou 'real'
            
        Returns:
            Dict com status e próximo passo
        """
        # Validar valor
        validacao = self._validar_campo(campo, valor)
        
        if not validacao['valido']:
            return {
                'status': 'erro_validacao',
                'campo': campo,
                'mensagem': validacao['mensagem'],
                'dados_coletados': dados_coletados
            }
        
        # Adicionar valor aos dados coletados
        dados_coletados[campo] = valor
        
        # Identificar próximo campo
        proximo_campo = self._identificar_proximo_campo(dados_coletados)
        
        if proximo_campo:
            return {
                'status': 'coletando_dados',
                'tipo': tipo,
                'proximo_campo': proximo_campo,
                'mensagem': self._gerar_mensagem_solicitacao(proximo_campo, tipo),
                'dados_coletados': dados_coletados,
                'progresso': self._calcular_progresso(dados_coletados)
            }
        else:
            return {
                'status': 'pronto_para_criar',
                'tipo': tipo,
                'dados_coletados': dados_coletados,
                'mensagem': 'Todos os dados obrigatórios foram coletados. Deseja criar a empresa agora?',
                'progresso': 100
            }

    def finalizar_cadastro(self, dados: Dict, tipo: str = 'real') -> Dict[str, Any]:
        """
        Finaliza cadastro criando a empresa.
        
        Args:
            dados: Dict com todos os dados coletados
            tipo: 'exemplo' ou 'real'
            
        Returns:
            Dict com resultado do cadastro
        """
        try:
            # Validar dados obrigatórios
            for campo in self.CAMPOS_OBRIGATORIOS:
                if campo not in dados or not dados[campo]:
                    return {
                        'status': 'erro',
                        'mensagem': f'Campo obrigatório faltando: {campo}'
                    }
            
            # Validar client_code
            client_code = dados.get('client_code', '').strip().upper()
            if not re.match(r'^[A-Z0-9]{1,3}$', client_code):
                return {
                    'status': 'erro',
                    'mensagem': 'Código do cliente deve ter de 1 a 3 caracteres (letras ou números)'
                }
            
            # Usar a função do database helper para criar empresa
            # (que já trata client_code corretamente)
            from config_database import get_db
            db_helper = get_db()
            
            company_data = {
                'name': dados['name'].strip(),
                'client_code': client_code,
                'legal_name': dados.get('legal_name', '').strip() or None,
                'industry': dados.get('segment', '').strip() or None,
                'size': None,  # Não coletado no MVP
                'description': None  # Não coletado no MVP
            }
            
            # Criar empresa via helper
            company_id = db_helper.create_company(company_data)
            
            if not company_id:
                return {
                    'status': 'erro',
                    'mensagem': 'Erro ao criar empresa no banco de dados'
                }
            
            # Atualizar campos adicionais via SQLAlchemy (se necessário)
            company = Company.query.get(company_id)
            if company:
                # Atualizar campos que não estão no create_company
                company.cnpj = self._limpar_cnpj(dados.get('cnpj')) or None
                company.city = dados.get('city', '').strip() or None
                company.state = dados.get('state', '').strip() or None
                company.coverage_physical = dados.get('coverage_physical', '').strip() or None
                company.coverage_online = dados.get('coverage_online', '').strip() or None
                company.experience_total = dados.get('experience_total', '').strip() or None
                company.experience_segment = dados.get('experience_segment', '').strip() or None
                company.mission = dados.get('mission', '').strip() or None
                company.vision = dados.get('vision', '').strip() or None
                company.values = dados.get('values', '').strip() or None
                
                db.session.commit()
            
            return {
                'status': 'sucesso',
                'company_id': company_id,
                'mensagem': f"Empresa {'exemplo' if tipo == 'exemplo' else ''} cadastrada com sucesso!",
                'proximos_passos': self._sugerir_proximos_passos(company_id, dados)
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar empresa: {e}")
            return {
                'status': 'erro',
                'mensagem': f'Erro ao criar empresa: {str(e)}'
            }

    def analisar_completude(self, company_id: int) -> Dict[str, Any]:
        """
        Analisa completude do cadastro de uma empresa.
        
        Args:
            company_id: ID da empresa
            
        Returns:
            Dict com análise de completude e impactos
        """
        try:
            # Buscar empresa
            company = Company.query.get(company_id)
            if not company:
                return {
                    'status': 'erro',
                    'mensagem': 'Empresa não encontrada'
                }
            
            # Validar completude
            validacao = self._validar_completude(company, [])
            
            # Analisar impacto
            impactos = self._analisar_impactos(validacao['campos_faltantes'])
            
            # Calcular percentual
            percentual = self._calcular_percentual_completude(company, [])
            
            # Gerar relatório
            relatorio = self._gerar_relatorio(validacao, impactos, percentual, company)
            
            return {
                'status': 'sucesso',
                'company_id': company_id,
                'company_name': company.name,
                'completude_percentual': percentual,
                'status_completude': 'completo' if validacao['completo'] else 'incompleto',
                'campos_faltantes': validacao['campos_faltantes'],
                'impactos': impactos,
                'relatorio': relatorio
            }
            
        except Exception as e:
            logger.error(f"Erro ao analisar completude: {e}")
            return {
                'status': 'erro',
                'mensagem': f'Erro ao analisar completude: {str(e)}'
            }

    def _identificar_proximo_campo(self, dados_coletados: Dict) -> Optional[str]:
        """Identifica próximo campo a solicitar"""
        # Se há dados de empresa aninhados, usar eles
        dados_empresa = dados_coletados.get('empresa', {})
        dados_para_verificar = { **dados_coletados, **dados_empresa }
        
        # Primeiro: campos obrigatórios
        for campo in self.CAMPOS_OBRIGATORIOS:
            valor = dados_para_verificar.get(campo)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                return campo
        
        # Depois: campos recomendados (alta prioridade)
        for campo in self.CAMPOS_RECOMENDADOS_ALTA:
            if campo not in dados_coletados or not dados_coletados[campo]:
                return campo
        
        # Depois: campos recomendados (média prioridade)
        for campo in self.CAMPOS_RECOMENDADOS_MEDIA:
            if campo not in dados_coletados or not dados_coletados[campo]:
                return campo
        
        # Por último: campos opcionais (MVV)
        for campo in self.CAMPOS_OPCIONAIS:
            if campo not in dados_coletados or not dados_coletados[campo]:
                return campo
        
        return None

    def _validar_campo(self, campo: str, valor: Any) -> Dict[str, Any]:
        """Valida valor de um campo específico"""
        if not valor or (isinstance(valor, str) and not valor.strip()):
            return {
                'valido': False,
                'mensagem': f'O campo {campo} não pode estar vazio'
            }
        
        # Validações específicas
        if campo == 'client_code':
            valor_limpo = str(valor).strip().upper()
            if not re.match(r'^[A-Z0-9]{1,3}$', valor_limpo):
                return {
                    'valido': False,
                    'mensagem': 'Código do cliente deve ter de 1 a 3 caracteres (letras ou números)'
                }
        
        if campo == 'cnpj':
            cnpj_limpo = self._limpar_cnpj(valor)
            if not cnpj_limpo or len(cnpj_limpo) != 14:
                return {
                    'valido': False,
                    'mensagem': 'CNPJ deve ter 14 dígitos'
                }
            # Validar dígitos verificadores
            if not self._validar_cnpj_digitos(cnpj_limpo):
                return {
                    'valido': False,
                    'mensagem': 'CNPJ inválido (dígitos verificadores incorretos)'
                }
        
        if campo == 'state' and valor:
            estado = str(valor).strip().upper()
            if len(estado) != 2:
                return {
                    'valido': False,
                    'mensagem': 'Estado deve ter 2 caracteres (ex: SP, RJ)'
                }
            # Validar se é um estado válido do Brasil
            estados_validos = [
                'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
                'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
                'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
            ]
            if estado not in estados_validos:
                return {
                    'valido': False,
                    'mensagem': 'Estado inválido. Use a sigla de 2 letras (ex: SP, RJ, MG)'
                }
        
        if campo == 'city' and valor:
            cidade = str(valor).strip()
            if len(cidade) < 2:
                return {
                    'valido': False,
                    'mensagem': 'Nome da cidade muito curto'
                }
        
        if campo == 'segment' and valor:
            segmento = str(valor).strip()
            if len(segmento) < 2:
                return {
                    'valido': False,
                    'mensagem': 'Nome do segmento muito curto'
                }
        
        return {'valido': True}
    
    def _validar_cnpj_digitos(self, cnpj: str) -> bool:
        """Valida os dígitos verificadores do CNPJ"""
        if len(cnpj) != 14:
            return False
        
        # Elimina CNPJs conhecidos como inválidos (todos os dígitos iguais)
        if cnpj == cnpj[0] * 14:
            return False
        
        # Validação dos dígitos verificadores
        tamanho = len(cnpj) - 2
        numeros = cnpj[:tamanho]
        digitos = cnpj[tamanho:]
        soma = 0
        pos = tamanho - 7
        
        # Primeiro dígito verificador
        for i in range(tamanho):
            soma += int(numeros[i]) * pos
            pos -= 1
            if pos < 2:
                pos = 9
        
        resultado = soma % 11
        if resultado < 2:
            digito1 = 0
        else:
            digito1 = 11 - resultado
        
        if digito1 != int(digitos[0]):
            return False
        
        # Segundo dígito verificador
        tamanho = tamanho + 1
        numeros = cnpj[:tamanho]
        soma = 0
        pos = tamanho - 7
        
        for i in range(tamanho):
            soma += int(numeros[i]) * pos
            pos -= 1
            if pos < 2:
                pos = 9
        
        resultado = soma % 11
        if resultado < 2:
            digito2 = 0
        else:
            digito2 = 11 - resultado
        
        return digito2 == int(digitos[1])

    def _gerar_mensagem_solicitacao(self, campo: str, tipo: str) -> str:
        """Gera mensagem para solicitar campo específico"""
        prefixo = "Empresa exemplo: " if tipo == 'exemplo' else ""
        
        mensagens = {
            'name': f"{prefixo}Qual é o nome fantasia da empresa?",
            'client_code': "Qual é o código do cliente? (1 a 3 caracteres, letras ou números)",
            'legal_name': "Qual é a razão social da empresa?",
            'cnpj': "Qual é o CNPJ da empresa? (formato: XX.XXX.XXX/XXXX-XX)",
            'segment': "Qual é o segmento/indústria da empresa?",
            'city': "Em qual cidade a empresa está localizada?",
            'state': "Em qual estado? (sigla de 2 letras, ex: SP, RJ)",
            'coverage_physical': "Qual a cobertura física da empresa? (micro, local, regional, nacional, internacional)",
            'coverage_online': "A empresa tem presença online? (sim, não, parcial)",
            'experience_total': "Há quantos anos a empresa existe? (ex: 12 anos)",
            'experience_segment': "Há quantos anos a empresa atua neste segmento? (ex: 8 anos)",
            'mission': "Qual é a missão da empresa?",
            'vision': "Qual é a visão da empresa?",
            'values': "Quais são os valores da empresa?"
        }
        
        return mensagens.get(campo, f"Por favor, informe o campo {campo}")

    def _calcular_progresso(self, dados_coletados: Dict) -> int:
        """Calcula percentual de progresso do cadastro"""
        total_campos = len(self.CAMPOS_OBRIGATORIOS) + len(self.CAMPOS_RECOMENDADOS_ALTA)
        campos_preenchidos = 0
        
        for campo in self.CAMPOS_OBRIGATORIOS + self.CAMPOS_RECOMENDADOS_ALTA:
            if campo in dados_coletados and dados_coletados[campo]:
                campos_preenchidos += 1
        
        return int((campos_preenchidos / total_campos) * 100) if total_campos > 0 else 0

    def _validar_completude(self, company: Company, company_data_list: List = None) -> Dict[str, Any]:
        """Valida completude do cadastro"""
        faltantes_obrigatorios = []
        faltantes_recomendados_alta = []
        faltantes_recomendados_media = []
        faltantes_recomendados_baixa = []
        faltantes_opcionais = []
        
        # Validar campos obrigatórios
        for campo in self.CAMPOS_OBRIGATORIOS:
            valor = getattr(company, campo, None)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                faltantes_obrigatorios.append(campo)
        
        # Validar campos recomendados
        for campo in self.CAMPOS_RECOMENDADOS_ALTA:
            valor = getattr(company, campo, None)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                faltantes_recomendados_alta.append(campo)
        
        for campo in self.CAMPOS_RECOMENDADOS_MEDIA:
            valor = getattr(company, campo, None)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                faltantes_recomendados_media.append(campo)
        
        for campo in self.CAMPOS_RECOMENDADOS_BAIXA:
            valor = getattr(company, campo, None)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                faltantes_recomendados_baixa.append(campo)
        
        # Validar campos opcionais (MVV)
        for campo in self.CAMPOS_OPCIONAIS:
            valor = getattr(company, campo, None)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                faltantes_opcionais.append(campo)
        
        return {
            'completo': len(faltantes_obrigatorios) == 0,
            'campos_faltantes': {
                'obrigatorios': faltantes_obrigatorios,
                'recomendados_alta': faltantes_recomendados_alta,
                'recomendados_media': faltantes_recomendados_media,
                'recomendados_baixa': faltantes_recomendados_baixa,
                'opcionais': faltantes_opcionais
            }
        }

    def _analisar_impactos(self, campos_faltantes: Dict) -> Dict[str, Dict]:
        """Analisa impacto de cada campo faltante"""
        impactos = {}
        
        # Combinar todos os campos faltantes
        todos_faltantes = (
            campos_faltantes.get('obrigatorios', []) +
            campos_faltantes.get('recomendados_alta', []) +
            campos_faltantes.get('recomendados_media', []) +
            campos_faltantes.get('recomendados_baixa', []) +
            campos_faltantes.get('opcionais', [])
        )
        
        for campo in todos_faltantes:
            impacto = self.IMPACTOS.get(campo, {
                'criticidade': 'DESCONHECIDO',
                'impacto_pev': 'A ser analisado',
                'impacto_grv': 'A ser analisado',
                'impacto_relatorios': 'A ser analisado',
                'recomendacao': 'Verificar necessidade'
            })
            impactos[campo] = impacto
        
        return impactos

    def _calcular_percentual_completude(self, company: Company, company_data_list: List = None) -> int:
        """Calcula percentual de completude"""
        todos_campos = (
            self.CAMPOS_OBRIGATORIOS +
            self.CAMPOS_RECOMENDADOS_ALTA +
            self.CAMPOS_RECOMENDADOS_MEDIA +
            self.CAMPOS_RECOMENDADOS_BAIXA +
            self.CAMPOS_OPCIONAIS
        )
        
        campos_preenchidos = 0
        for campo in todos_campos:
            valor = getattr(company, campo, None)
            if valor and (not isinstance(valor, str) or valor.strip()):
                campos_preenchidos += 1
        
        return int((campos_preenchidos / len(todos_campos)) * 100) if todos_campos else 0

    def _gerar_relatorio(self, validacao: Dict, impactos: Dict, percentual: int, company: Company) -> str:
        """Gera relatório textual de completude"""
        linhas = []
        linhas.append(f"📊 ANÁLISE DE COMPLETUDE - {company.name}")
        linhas.append("=" * 60)
        linhas.append(f"\n✅ Completude: {percentual}%")
        
        if validacao['completo']:
            linhas.append("\n🎉 Parabéns! Todos os campos obrigatórios estão preenchidos.")
        else:
            linhas.append("\n⚠️ ATENÇÃO: Alguns campos obrigatórios estão faltando!")
        
        # Campos obrigatórios faltantes
        if validacao['campos_faltantes']['obrigatorios']:
            linhas.append("\n🔴 CAMPOS OBRIGATÓRIOS FALTANTES:")
            for campo in validacao['campos_faltantes']['obrigatorios']:
                impacto = impactos.get(campo, {})
                linhas.append(f"  • {campo}: {impacto.get('recomendacao', 'Preencher imediatamente')}")
        
        # Campos recomendados faltantes
        if validacao['campos_faltantes']['recomendados_alta']:
            linhas.append("\n🟠 CAMPOS RECOMENDADOS (ALTA PRIORIDADE):")
            for campo in validacao['campos_faltantes']['recomendados_alta']:
                impacto = impactos.get(campo, {})
                linhas.append(f"  • {campo}: {impacto.get('recomendacao', 'Recomendado preencher')}")
        
        # Impactos
        if impactos:
            linhas.append("\n📋 IMPACTOS IDENTIFICADOS:")
            for campo, impacto in impactos.items():
                linhas.append(f"\n  {campo.upper()}:")
                linhas.append(f"    • Criticidade: {impacto.get('criticidade', 'N/A')}")
                linhas.append(f"    • Impacto PEV: {impacto.get('impacto_pev', 'N/A')}")
                linhas.append(f"    • Impacto GRV: {impacto.get('impacto_grv', 'N/A')}")
                linhas.append(f"    • Impacto Relatórios: {impacto.get('impacto_relatorios', 'N/A')}")
        
        return "\n".join(linhas)

    def _sugerir_proximos_passos(self, company_id: int, dados: Dict) -> List[str]:
        """Sugere próximos passos após cadastro"""
        passos = [
            f"Criar um plano estratégico para a empresa (ID: {company_id})",
            "Cadastrar colaboradores da empresa",
            "Configurar indicadores e métricas"
        ]
        
        # Se MVV não foi preenchido, sugerir
        if not dados.get('mission') or not dados.get('vision'):
            passos.insert(0, "Completar Missão, Visão e Valores (MVV) da empresa")
        
        return passos

    def _limpar_cnpj(self, cnpj: str) -> Optional[str]:
        """Remove formatação do CNPJ"""
        if not cnpj:
            return None
        return re.sub(r'[^0-9]', '', str(cnpj))

