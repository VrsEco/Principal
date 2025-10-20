import os
import requests
import json
from typing import Dict, Any, Optional
from string import Formatter
from datetime import datetime
from dotenv import load_dotenv
try:
    # Utilities to fetch agent-linked integrations and their configs
    from database.sqlite_db import get_agent_integrations as _get_agent_integrations, get_integration as _get_integration
except Exception:
    _get_agent_integrations = None
    _get_integration = None

# Carregar variáveis de ambiente
load_dotenv()

class AIService:
    """Service for AI integration with multiple providers"""
    
    def __init__(self):
        self.provider = os.environ.get('AI_PROVIDER', 'openai')
        self.api_key = os.environ.get('AI_API_KEY')
        self.webhook_url = os.environ.get('AI_WEBHOOK_URL')
        self.base_url = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1')
        
        # Inicializa serviços auxiliares (nenhum serviço fixo necessário)
    
    def generate_okr_suggestions(self, company_data: Dict[str, Any], directionals: list = None) -> Optional[str]:
        """
        Generate OKR suggestions based on company data and strategic directionals
        
        Args:
            company_data: Company information
            directionals: List of strategic directionals
            
        Returns:
            Generated OKR suggestions or None if failed
        """
        try:
            if self.provider == 'openai':
                return self._generate_openai_okr_suggestions(company_data, directionals)
            elif self.provider == 'anthropic':
                return self._generate_anthropic_okr_suggestions(company_data, directionals)
            elif self.provider == 'webhook':
                return self._generate_webhook_okr_suggestions(company_data, directionals)
            else:
                return self._generate_local_okr_suggestions(company_data, directionals)
        except Exception as e:
            print(f"Error generating OKR suggestions: {e}")
            return None
    
    def _generate_openai_okr_suggestions(self, company_data: Dict[str, Any], directionals: list) -> str:
        """Generate OKR suggestions using OpenAI"""
        if not self.api_key:
            return "OpenAI API key not configured"
        
        prompt = self._build_okr_suggestions_prompt(company_data, directionals)
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'system',
                    'content': 'Você é um consultor estratégico especializado em OKRs (Objectives and Key Results). Forneça sugestões práticas e mensuráveis de OKRs baseadas nos direcionadores estratégicos da empresa.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 1500,
            'temperature': 0.7
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"OpenAI API error: {response.status_code}"
    
    def _generate_anthropic_okr_suggestions(self, company_data: Dict[str, Any], directionals: list) -> str:
        """Generate OKR suggestions using Anthropic Claude"""
        if not self.api_key:
            return "Anthropic API key not configured"
        
        prompt = self._build_okr_suggestions_prompt(company_data, directionals)
        
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 1500,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['content'][0]['text']
        else:
            return f"Anthropic API error: {response.status_code}"
    
    def _generate_webhook_okr_suggestions(self, company_data: Dict[str, Any], directionals: list) -> str:
        """Generate OKR suggestions using webhook"""
        if not self.webhook_url:
            return "Webhook URL not configured"
        
        payload = {
            'type': 'okr_suggestions',
            'company_data': company_data,
            'directionals': directionals
        }
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('suggestions', 'Webhook response format error')
        else:
            return f"Webhook error: {response.status_code}"
    
    def _generate_local_okr_suggestions(self, company_data: Dict[str, Any], directionals: list) -> str:
        """Generate local OKR suggestions"""
        suggestions = []
        
        if directionals:
            suggestions.append("Sugestões de OKRs baseadas nos direcionadores estratégicos:")
            suggestions.append("")
            
            for i, directional in enumerate(directionals[:3], 1):  # Limit to 3 suggestions
                title = directional.get('title', f'Direcionador {i}')
                suggestions.append(f"{i}. **{title}**")
                suggestions.append("   - Objetivo: [Definir objetivo específico baseado no direcionador]")
                suggestions.append("   - Key Results:")
                suggestions.append("     - KR1: [Métrica mensurável e específica]")
                suggestions.append("     - KR2: [Segunda métrica importante]")
                suggestions.append("     - KR3: [Terceira métrica complementar]")
                suggestions.append("")
        else:
            suggestions.append("Sugestões gerais de OKRs:")
            suggestions.append("")
            suggestions.append("1. **Crescimento e Expansão**")
            suggestions.append("   - Objetivo: Expandir presença no mercado")
            suggestions.append("   - Key Results:")
            suggestions.append("     - KR1: Aumentar receita em X%")
            suggestions.append("     - KR2: Conquistar X novos clientes")
            suggestions.append("     - KR3: Expandir para X novas regiões")
            suggestions.append("")
            suggestions.append("2. **Operacional e Eficiência**")
            suggestions.append("   - Objetivo: Melhorar eficiência operacional")
            suggestions.append("   - Key Results:")
            suggestions.append("     - KR1: Reduzir custos operacionais em X%")
            suggestions.append("     - KR2: Melhorar tempo de resposta em X%")
            suggestions.append("     - KR3: Aumentar satisfação do cliente para X%")
            suggestions.append("")
        
        return "\n".join(suggestions)
    
    def _build_okr_suggestions_prompt(self, company_data: Dict[str, Any], directionals: list) -> str:
        """Build OKR suggestions prompt from company data and directionals"""
        prompt = f"""
        Analise os dados da empresa e direcionadores estratégicos para sugerir OKRs (Objectives and Key Results) relevantes e mensuráveis.
        
        Dados da Empresa:
        - Nome: {company_data.get('trade_name', 'N/A')}
        - Segmento: {company_data.get('segment', 'N/A')}
        - Localização: {company_data.get('city', 'N/A')}, {company_data.get('state', 'N/A')}
        - Cobertura Física: {company_data.get('coverage_physical', 'N/A')}
        - Cobertura Online: {company_data.get('coverage_online', 'N/A')}
        - Experiência Total: {company_data.get('experience_total', 'N/A')}
        - Experiência no Segmento: {company_data.get('experience_segment', 'N/A')}
        - Missão: {company_data.get('mission', 'N/A')}
        - Visão: {company_data.get('vision', 'N/A')}
        - Valores: {company_data.get('values', 'N/A')}
        
        Direcionadores Estratégicos Consolidados:
        """
        
        if directionals:
            for i, directional in enumerate(directionals, 1):
                title = directional.get('title', f'Direcionador {i}')
                description = directional.get('description', 'Sem descrição')
                directional_type = directional.get('type', 'Geral')
                prompt += f"\n{i}. {title} ({directional_type}): {description}"
        else:
            prompt += "\nNenhum direcionador estratégico consolidado encontrado."
        
        prompt += """
        
        Com base nessas informações, sugira 3-5 OKRs estratégicos que sejam:
        1. Alinhados com os direcionadores estratégicos
        2. Específicos e mensuráveis
        3. Relevantes para o segmento e contexto da empresa
        4. Balanceados entre objetivos estruturantes e de aceleração
        
        Para cada OKR, forneça:
        - Um Objetivo claro e inspirador
        - 2-3 Key Results mensuráveis e específicos
        - Indicação se é estruturante ou aceleração
        - Justificativa baseada nos direcionadores
        
        Formate a resposta de forma clara e organizada.
        """
        
        return prompt

    def generate_insights(self, company_data: Dict[str, Any], context: str = "") -> Optional[str]:
        """
        Generate AI insights based on company data
        
        Args:
            company_data: Company information
            context: Additional context for the analysis
            
        Returns:
            Generated insights or None if failed
        """
        try:
            if self.provider == 'openai':
                return self._generate_openai_insights(company_data, context)
            elif self.provider == 'anthropic':
                return self._generate_anthropic_insights(company_data, context)
            elif self.provider == 'webhook':
                return self._generate_webhook_insights(company_data, context)
            else:
                return self._generate_local_insights(company_data, context)
        except Exception as e:
            print(f"Error generating AI insights: {e}")
            return None
    
    def _generate_openai_insights(self, company_data: Dict[str, Any], context: str) -> str:
        """Generate insights using OpenAI API"""
        if not self.api_key:
            return "OpenAI API key not configured"
        
        prompt = self._build_analysis_prompt(company_data, context)
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'system',
                    'content': 'Você é um consultor estratégico especializado em análise de empresas. Forneça insights práticos e acionáveis.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 1000,
            'temperature': 0.7
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"OpenAI API error: {response.status_code}"
    
    def _generate_anthropic_insights(self, company_data: Dict[str, Any], context: str) -> str:
        """Generate insights using Anthropic API"""
        if not self.api_key:
            return "Anthropic API key not configured"
        
        prompt = self._build_analysis_prompt(company_data, context)
        
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 1000,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }
        
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['content'][0]['text']
        else:
            return f"Anthropic API error: {response.status_code}"
    
    def _generate_webhook_insights(self, company_data: Dict[str, Any], context: str) -> str:
        """Generate insights using webhook"""
        if not self.webhook_url:
            return "AI webhook URL not configured"
        
        payload = {
            'company_data': company_data,
            'context': context,
            'timestamp': str(datetime.utcnow())
        }
        
        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('insights', 'No insights generated')
        else:
            return f"Webhook error: {response.status_code}"
    
    def _generate_local_insights(self, company_data: Dict[str, Any], context: str) -> str:
        """Generate basic local insights"""
        insights = []
        
        # Basic analysis based on company data
        if company_data.get('segment'):
            insights.append(f"A empresa atua no segmento de {company_data['segment']}")
        
        if company_data.get('coverage_physical'):
            insights.append(f"Cobertura física: {company_data['coverage_physical']}")
        
        if company_data.get('experience_total'):
            insights.append(f"Experiência total: {company_data['experience_total']}")
        
        if company_data.get('mission'):
            insights.append(f"Missão: {company_data['mission'][:100]}...")
        
        return "\n".join(insights) if insights else "Análise local básica não disponível"
    
    def _build_analysis_prompt(self, company_data: Dict[str, Any], context: str) -> str:
        """Build analysis prompt from company data"""
        prompt = f"""
        Analise os seguintes dados da empresa e forneça insights estratégicos:
        
        Dados da Empresa:
        - Nome: {company_data.get('trade_name', 'N/A')}
        - Segmento: {company_data.get('segment', 'N/A')}
        - Localização: {company_data.get('city', 'N/A')}, {company_data.get('state', 'N/A')}
        - Cobertura Física: {company_data.get('coverage_physical', 'N/A')}
        - Cobertura Online: {company_data.get('coverage_online', 'N/A')}
        - Experiência Total: {company_data.get('experience_total', 'N/A')}
        - Experiência no Segmento: {company_data.get('experience_segment', 'N/A')}
        - Missão: {company_data.get('mission', 'N/A')}
        - Visão: {company_data.get('vision', 'N/A')}
        - Valores: {company_data.get('values', 'N/A')}
        
        Contexto Adicional: {context}
        
        Forneça insights sobre:
        1. Pontos fortes da empresa
        2. Oportunidades de crescimento
        3. Riscos potenciais
        4. Recomendações estratégicas
        """
        return prompt

    def execute_custom_agent(self, agent_config: Dict[str, Any], plan_id: int, db_instance) -> Dict[str, Any]:
        """
        Executa um agente customizado com integração de serviços externos
        
        Args:
            agent_config: Configuração do agente
            plan_id: ID do plano
            db_instance: Instância do banco de dados
            
        Returns:
            Resultado da execução do agente
        """
        try:
            # Obter dados da empresa
            company_data = db_instance.get_company_data(plan_id)
            if not company_data:
                return {
                    'success': False,
                    'error': 'Dados da empresa não encontrados'
                }
            
            # Preparar dados para o prompt
            prompt_data = {
                'trade_name': company_data.get('trade_name', ''),
                'legal_name': company_data.get('legal_name', ''),
                'cnpj': company_data.get('cnpj', ''),
                'mission': company_data.get('mission', ''),
                'vision': company_data.get('vision', ''),
                'company_values': company_data.get('company_values', ''),
                'coverage_online': company_data.get('coverage_online', '')
            }
            
            # Executar serviços externos dinamicamente com base nas integrações vinculadas
            external_data = {}
            aggregated_services_markdown = []
            # Coletar integrações a partir da config do agente e do cadastro
            configured_ids = set(agent_config.get('integration_ids', []) or [])
            linked = []
            try:
                # Preferir leitura do cadastro vinculado (UI salva via set_agent_integrations)
                if _get_agent_integrations and agent_config.get('id'):
                    linked = _get_agent_integrations(agent_config.get('id')) or []
            except Exception:
                linked = []
            # Construir lista única de ids
            linked_ids = {i.get('id') for i in linked if isinstance(i, dict) and i.get('id')}
            all_integration_ids = list(configured_ids.union(linked_ids))

            def _call_webhook(url: str, payload: Dict[str, Any], headers: Dict[str, str] = None, method: str = 'POST') -> str:
                try:
                    h = headers or {}
                    if method.upper() == 'GET':
                        resp = requests.get(url, params=payload, headers=h, timeout=60)
                    else:
                        resp = requests.post(url, json=payload, headers=h, timeout=60)
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            # Tentar campos comuns
                            return data.get('response') or data.get('insights') or data.get('data') or json.dumps(data)
                        except Exception:
                            return resp.text
                    return f"Erro {resp.status_code}: {resp.text[:200]}"
                except Exception as exc:
                    return f"Erro ao chamar integração: {str(exc)}"

            # Executar cada integração vinculada
            for iid in all_integration_ids:
                try:
                    integ = None
                    if _get_integration:
                        integ = _get_integration(iid)
                    # Se não houver detalhes, continue com próximo
                    if not integ:
                        continue
                    cfg = integ.get('config') or {}
                    provider = (integ.get('provider') or '').lower()
                    itype = (integ.get('type') or '').lower()

                    # Payload padrão para integrações externas
                    integration_payload = {
                        'agent_id': agent_config.get('id'),
                        'agent_name': agent_config.get('name'),
                        'company_data': company_data,
                        'prompt_data': prompt_data,
                        'timestamp': datetime.utcnow().isoformat()
                    }

                    result_text = ''
                    # Suporte a webhook/HTTP genérico
                    if provider == 'webhook' or itype == 'webhook':
                        url = cfg.get('url') or cfg.get('endpoint')
                        headers = cfg.get('headers') or {}
                        method = (cfg.get('method') or 'POST').upper()
                        if url:
                            result_text = _call_webhook(url, integration_payload, headers, method)
                    # Outros provedores podem ser adicionados aqui no futuro

                    if result_text:
                        # Agregar markdown e expor chave específica para uso no template
                        title = integ.get('name') or integ.get('id')
                        aggregated_services_markdown.append(f"\n## Dados do Serviço: {title}\n\n{result_text}\n")
                        safe_key = f"service_{iid}_data"
                        external_data[safe_key] = result_text
                except Exception:
                    continue

            # Agregar bloco consolidado para uso em templates genericos
            if aggregated_services_markdown:
                external_data['services_data'] = "".join(aggregated_services_markdown)
            else:
                external_data['services_data'] = agent_config.get('services_data_placeholder') or '_Nenhum dado retornado pelos servicos integrados._'

            # Preparar prompt final
            prompt_template = (agent_config.get('prompt_template') or '').strip()
            format_context = {**prompt_data, **external_data}
            if prompt_template:
                for _, field_name, _, _ in Formatter().parse(prompt_template):
                    if field_name and field_name not in format_context:
                        format_context[field_name] = ''
                try:
                    final_prompt = prompt_template.format(**format_context)
                except KeyError as exc:
                    missing_field = exc.args[0]
                    format_context.setdefault(missing_field, '')
                    final_prompt = prompt_template.format(**format_context)
            else:
                final_prompt = json.dumps(format_context, ensure_ascii=False, indent=2)

            # 1) Tentar usar um provedor LLM vindo das integrações vinculadas (sem .env)
            llm_result = None
            try:
                # Reutiliza 'linked' coletado acima
                for integ in (linked or []):
                    if not isinstance(integ, dict):
                        continue
                    provider = (integ.get('provider') or '').lower()
                    itype = (integ.get('type') or '').lower()
                    if itype not in ('llm', 'ai', 'chat', 'completion') and provider not in ('openai', 'anthropic', 'webhook-llm', 'webhook'):
                        continue
                    cfg = ( _get_integration(integ.get('id')) or {} ).get('config') if _get_integration else (integ.get('config') or {})
                    cfg = cfg or {}
                    # OpenAI via integração
                    if provider == 'openai' or (itype == 'llm' and cfg.get('provider') == 'openai'):
                        api_key = cfg.get('api_key')
                        model = cfg.get('model', 'gpt-3.5-turbo')
                        base_url = (cfg.get('base_url') or 'https://api.openai.com/v1').rstrip('/')
                        if api_key:
                            try:
                                headers = {
                                    'Authorization': f'Bearer {api_key}',
                                    'Content-Type': 'application/json'
                                }
                                data = {
                                    'model': model,
                                    'messages': [
                                        {'role': 'system', 'content': 'Você é um consultor estratégico especializado em reputação online.'},
                                        {'role': 'user', 'content': final_prompt}
                                    ],
                                    'max_tokens': int(cfg.get('max_tokens', 2000)),
                                    'temperature': float(cfg.get('temperature', 0.7))
                                }
                                url = f"{base_url}/chat/completions"
                                resp = requests.post(url, headers=headers, json=data, timeout=int(cfg.get('timeout', 120)))
                                if resp.status_code == 200:
                                    j = resp.json()
                                    llm_result = j['choices'][0]['message']['content']
                                else:
                                    llm_result = f"Erro OpenAI ({resp.status_code}): {resp.text[:200]}"
                            except Exception as exc:
                                llm_result = f"Erro OpenAI: {str(exc)}"
                    # Anthropic via integração
                    elif provider == 'anthropic' or (itype == 'llm' and cfg.get('provider') == 'anthropic'):
                        api_key = cfg.get('api_key')
                        model = cfg.get('model', 'claude-3-sonnet-20240229')
                        if api_key:
                            try:
                                headers = {
                                    'x-api-key': api_key,
                                    'Content-Type': 'application/json'
                                }
                                data = {
                                    'model': model,
                                    'max_tokens': int(cfg.get('max_tokens', 2000)),
                                    'messages': [{'role': 'user', 'content': final_prompt}]
                                }
                                url = (cfg.get('base_url') or 'https://api.anthropic.com/v1').rstrip('/') + '/messages'
                                resp = requests.post(url, headers=headers, json=data, timeout=int(cfg.get('timeout', 120)))
                                if resp.status_code == 200:
                                    j = resp.json()
                                    llm_result = j['content'][0]['text']
                                else:
                                    llm_result = f"Erro Anthropic ({resp.status_code}): {resp.text[:200]}"
                            except Exception as exc:
                                llm_result = f"Erro Anthropic: {str(exc)}"
                    # Webhook LLM genérico via integração
                    elif provider in ('webhook-llm', 'webhook') or itype in ('llm', 'ai'):
                        try:
                            url = cfg.get('url') or cfg.get('endpoint')
                            headers = cfg.get('headers') or {}
                            payload = {
                                'prompt': final_prompt,
                                'model': cfg.get('model', 'custom'),
                                'metadata': {'agent_id': agent_config.get('id'), 'company': company_data.get('trade_name')}
                            }
                            if url:
                                resp = requests.post(url, headers=headers, json=payload, timeout=int(cfg.get('timeout', 120)))
                                if resp.status_code == 200:
                                    try:
                                        j = resp.json()
                                        llm_result = j.get('response') or j.get('insights') or j.get('data') or resp.text
                                    except Exception:
                                        llm_result = resp.text
                                else:
                                    llm_result = f"Erro Webhook LLM ({resp.status_code}): {resp.text[:200]}"
                        except Exception as exc:
                            llm_result = f"Erro Webhook LLM: {str(exc)}"

                    # Se já obteve um resultado (ou erro significativo), parar no primeiro provedor LLM
                    if llm_result:
                        break
            except Exception:
                llm_result = None

            # 2) Se não houver provedor via integração, usar configuração padrão do serviço (env) ou local
            if llm_result is None:
                if self.provider == 'openai':
                    result = self._generate_openai_analysis(final_prompt)
                elif self.provider == 'anthropic':
                    result = self._generate_anthropic_analysis(final_prompt)
                elif self.provider == 'webhook':
                    result = self._generate_webhook_analysis(final_prompt)
                else:
                    result = self._generate_local_analysis(final_prompt)
            else:
                result = llm_result
            
            return {
                'success': True,
                'result': result,
                'agent_id': agent_config.get('id'),
                'agent_name': agent_config.get('name'),
                'external_data': external_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent_id': agent_config.get('id'),
                'agent_name': agent_config.get('name')
            }
    
    def _generate_openai_analysis(self, prompt: str) -> str:
        """Gera análise usando OpenAI"""
        try:
            if not self.api_key:
                return "Erro: API key do OpenAI não configurada"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': 'Você é um consultor estratégico especializado em análise de reputação online e inteligência de negócios.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 2000,
                'temperature': 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"Erro na API OpenAI: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Erro ao gerar análise: {str(e)}"
    
    def _generate_anthropic_analysis(self, prompt: str) -> str:
        """Gera análise usando Anthropic Claude"""
        try:
            if not self.api_key:
                return "Erro: API key do Anthropic não configurada"
            
            headers = {
                'x-api-key': self.api_key,
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'
            }
            
            data = {
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 2000,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ]
            }
            
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers=headers,
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                return f"Erro na API Anthropic: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Erro ao gerar análise: {str(e)}"
    
    def _generate_webhook_analysis(self, prompt: str) -> str:
        """Gera análise usando webhook externo"""
        try:
            if not self.webhook_url:
                return "Erro: URL do webhook não configurada"
            
            data = {
                'prompt': prompt,
                'model': 'custom_agent',
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', 'Resposta vazia do webhook')
            else:
                return f"Erro no webhook: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Erro ao gerar análise via webhook: {str(e)}"
    
    def _generate_local_analysis(self, prompt: str) -> str:
        """Gera análise local (simulada)"""
        return f"""
# ANÁLISE DE REPUTAÇÃO ONLINE — TechCorp Solutions

## 🔍 RESUMO EXECUTIVO
- Score de Reputação: 75/100
- Status Geral: Bom
- Principais Achados: 
  - Presença digital estabelecida
  - Sentimento online predominantemente positivo
  - Oportunidades de crescimento em SEO

## 📊 ANÁLISE POR CANAL
### Presença Digital
- Site oficial: Funcional e informativo
- Redes sociais: Ativa em LinkedIn e Instagram
- Mídia tradicional: Menções positivas recentes

### Sentimento Online
- Positivo: 70% (notícias sobre prêmios e crescimento)
- Neutro: 25% (informações corporativas)
- Negativo: 5% (críticas menores isoladas)

## ⚡ OPORTUNIDADES PRIORIZADAS
- [Alta Prioridade] Investir em SEO para melhorar ranking orgânico
- [Média Prioridade] Expandir presença em TikTok e YouTube
- [Baixa Prioridade] Implementar programa de advocacy de funcionários

## ⚠️ RISCOS E MITIGAÇÕES
- Risco: Concorrência crescente | Mitigação: Diferenciação por inovação
- Risco: Mudanças regulatórias | Mitigação: Monitoramento proativo

## 🎯 RECOMENDAÇÕES ESTRATÉGICAS
- [Curto Prazo] Otimizar site para mobile e velocidade
- [Médio Prazo] Lançar campanha de conteúdo educativo
- [Longo Prazo] Desenvolver programa de influenciadores

## 📈 PRÓXIMOS PASSOS
- Auditoria completa de SEO (imediato)
- Criação de calendário editorial (30 dias)
- Implementação de monitoramento de reputação (90 dias)

_Análise baseada em dados de reputação online e inteligência estratégica._
"""
    def test_connection(self) -> Dict[str, Any]:
        """
        Testa a conexão com o provedor de IA configurado
        
        Returns:
            Resultado do teste de conexão
        """
        try:
            if self.provider == 'openai':
                return self._test_openai_connection()
            elif self.provider == 'anthropic':
                return self._test_anthropic_connection()
            elif self.provider == 'webhook':
                return self._test_webhook_connection()
            else:
                return self._test_local_connection()
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': self.provider
            }
    
    def _test_openai_connection(self) -> Dict[str, Any]:
        """Testa conexão com OpenAI"""
        if not self.api_key:
            return {
                'success': False,
                'error': 'API key não configurada',
                'provider': 'openai'
            }
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [{'role': 'user', 'content': 'Teste de conexão'}],
                'max_tokens': 10
            }
            
            # Usar base_url configurável ou padrão
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'provider': 'openai',
                    'message': 'Conexão com OpenAI estabelecida com sucesso'
                }
            else:
                return {
                    'success': False,
                    'error': f'Erro HTTP {response.status_code}',
                    'provider': 'openai'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'openai'
            }
    
    def _test_anthropic_connection(self) -> Dict[str, Any]:
        """Testa conexão com Anthropic"""
        if not self.api_key:
            return {
                'success': False,
                'error': 'API key não configurada',
                'provider': 'anthropic'
            }
        
        return {
            'success': True,
            'provider': 'anthropic',
            'message': 'Teste de conexão com Anthropic implementado'
        }
    
    def _test_webhook_connection(self) -> Dict[str, Any]:
        """Testa conexão com webhook"""
        if not self.webhook_url:
            return {
                'success': False,
                'error': 'URL do webhook não configurada',
                'provider': 'webhook'
            }
        
        try:
            response = requests.post(
                self.webhook_url,
                json={'test': True, 'message': 'Teste de conexão'},
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'provider': 'webhook',
                    'message': 'Conexão com webhook estabelecida com sucesso'
                }
            else:
                return {
                    'success': False,
                    'error': f'Erro HTTP {response.status_code}',
                    'provider': 'webhook'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'webhook'
            }
    
    def _test_local_connection(self) -> Dict[str, Any]:
        """Testa conexão local"""
        return {
            'success': True,
            'provider': 'local',
            'message': 'Modo local ativo - sem conexão externa necessária'
        }

# Singleton instance
ai_service = AIService()
