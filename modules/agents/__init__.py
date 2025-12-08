"""
Módulo de Agentes IA
"""
import logging
import io
from flask import Blueprint, render_template, request, jsonify, send_file, make_response
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

agents_bp = Blueprint('agents', __name__, url_prefix='/agents')


@agents_bp.route('/cadastro', endpoint='agents_cadastro_page')
@login_required
def cadastro_agent_page():
    """Página do Agente de Cadastro Conversacional"""
    return render_template('agents_cadastro.html', active_id='agent-cadastro')


@agents_bp.route('/api/conversar', methods=['POST'])
@login_required
def api_conversar():
    """Endpoint para conversação com o agente"""
    try:
        from services.cadastro_agent_service import CadastroAgentService
        from models.cadastro_session import CadastroSession
        from models import db
        from flask_login import current_user
        
        payload = request.get_json(silent=True) or {}
        mensagem = payload.get('mensagem', '').strip()
        session_id = payload.get('session_id')  # ID da sessão persistida
        
        if not mensagem:
            return jsonify({
                'success': False,
                'error': 'Mensagem não fornecida'
            }), 400
        
        # Buscar ou criar sessão
        if session_id:
            session = CadastroSession.query.get(session_id)
            if not session or session.user_id != current_user.id:
                return jsonify({
                    'success': False,
                    'error': 'Sessão não encontrada'
                }), 404
        else:
            # Criar nova sessão
            tipo_cadastro = payload.get('tipo_cadastro')
            if tipo_cadastro not in ['real', 'modelo']:
                tipo_cadastro = 'real'
            session = CadastroSession.criar_sessao(current_user.id, tipo_cadastro)
            session_id = session.id
        
        # Preparar contexto da sessão
        contexto = {
            'estado': session.estado,
            'dados_coletados': session.dados_coletados or {},
            'tipo_cadastro': session.tipo_cadastro,
            'empresa_id': session.empresa_id,
            'campo_atual': session.campo_atual
        }
        
        # Processar mensagem
        service = CadastroAgentService()
        resposta = service.processar_conversa(mensagem, contexto)
        
        # Atualizar sessão com novos dados
        if 'dados_coletados' in resposta:
            session.update_dados(resposta['dados_coletados'])
        
        if 'estado' in resposta:
            session.estado = resposta['estado']
        
        if 'campo_atual' in resposta:
            session.campo_atual = resposta.get('campo_atual')
        
        if 'empresa_id' in resposta:
            session.empresa_id = resposta.get('empresa_id')
        
        # Calcular progresso
        from services.cadastro_agent_service import CadastroAgentService
        service_temp = CadastroAgentService()
        progresso = service_temp._calcular_progresso(session.dados_coletados or {})
        session.progresso = progresso
        
        db.session.commit()
        
        # Adicionar session_id na resposta
        resposta['session_id'] = session.id
        
        return jsonify({
            'success': True,
            'data': resposta
        })
    except Exception as e:
        logger.error(f"Erro ao processar conversa: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/validacao-geral', methods=['POST'])
@login_required
def api_validacao_geral():
    """Analisa a completude do cadastro de uma empresa existente."""
    try:
        from services.cadastro_agent_service import CadastroAgentService
        from models.company import Company

        payload = request.get_json(silent=True) or {}
        empresa_query = (payload.get('empresa') or payload.get('empresa_nome') or payload.get('texto') or '').strip()
        company_id = payload.get('company_id')

        if not empresa_query and not company_id:
            return jsonify({
                'success': False,
                'error': 'Informe o nome ou ID da empresa para validar.'
            }), 400

        company = None
        if company_id:
            company = Company.query.get(company_id)
        else:
            query_ilike = f"%{empresa_query}%"
            company = Company.query.filter(Company.name.ilike(query_ilike)).first()
            if not company:
                company = Company.query.filter(Company.client_code.ilike(empresa_query)).first()
            if not company and empresa_query.isdigit():
                company = Company.query.filter(Company.cnpj.ilike(f"%{empresa_query}%")).first()

        if not company:
            return jsonify({
                'success': False,
                'error': 'Empresa não encontrada para a validação.'
            }), 404

        service = CadastroAgentService()
        resultado = service.analisar_completude(company.id)

        if resultado.get('status') != 'sucesso':
            return jsonify({
                'success': False,
                'error': resultado.get('mensagem', 'Erro ao analisar completude.')
            }), 400

        impacto_lines = []
        impactos = resultado.get('impactos') or {}
        if impactos:
            impacto_lines.append('Impactos registrados:')
            for campo, impacto in list(impactos.items())[:3]:
                impacto_lines.append(
                    f"- {campo}: criticidade {impacto.get('criticidade')}, {impacto.get('recomendacao')}"
                )

        mensagem = [
            f"Análise da empresa {resultado.get('company_name')} ({resultado.get('status_completude')}):",
            f"- Completude geral: {resultado.get('completude_percentual')}%",
        ]

        if impacto_lines:
            mensagem.extend(impacto_lines)

        mensagem.append(resultado.get('relatorio') or '')
        texto_final = '\n'.join([linha for linha in mensagem if linha])

        return jsonify({
            'success': True,
            'data': {
                'mensagem': texto_final,
                'estado': 'inicial',
                'company_id': company.id,
                'company_name': resultado.get('company_name'),
                'completude_percentual': resultado.get('completude_percentual'),
                'status_completude': resultado.get('status_completude'),
                'campos_faltantes': resultado.get('campos_faltantes'),
                'impactos': resultado.get('impactos'),
                'relatorio': resultado.get('relatorio')
            }
        })
    except Exception as e:
        logger.error(f"Erro ao validar empresa: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/cadastros-pendentes', methods=['GET'])
@login_required
def api_cadastros_pendentes():
    """Lista cadastros em andamento (sessões de cadastro)"""
    try:
        from models.cadastro_session import CadastroSession
        from flask_login import current_user
        
        sessoes = CadastroSession.listar_sessoes_pendentes(current_user.id)
        
        # Formatar para o formato esperado pelo frontend
        cadastros = []
        for sessao in sessoes:
            dados = sessao.get('dados_coletados', {})
            nome_empresa = dados.get('name') or dados.get('legal_name') or 'Empresa sem nome'
            cadastros.append({
                'id': sessao['id'],
                'empresa_nome': nome_empresa,
                'progresso': sessao.get('progresso', 0),
                'tipo_cadastro': sessao.get('tipo_cadastro'),
                'estado': sessao.get('estado'),
                'updated_at': sessao.get('updated_at')
            })
        
        return jsonify({
            'success': True,
            'data': cadastros
        })
    except Exception as e:
        logger.error(f"Erro ao listar cadastros pendentes: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/sessao/<int:session_id>', methods=['GET'])
@login_required
def api_buscar_sessao(session_id):
    """Busca uma sessão de cadastro específica"""
    try:
        from models.cadastro_session import CadastroSession
        from flask_login import current_user
        
        session = CadastroSession.query.get(session_id)
        
        if not session or session.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'data': session.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro ao buscar sessão: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/finalizar-cadastro', methods=['POST'])
@login_required
def api_finalizar_cadastro():
    """Finaliza cadastro completo (usuário + empresa + employee)"""
    try:
        from services.cadastro_agent_service import CadastroAgentService
        
        payload = request.get_json(silent=True) or {}
        session_id = payload.get('session_id')
        dados = payload.get('dados', {})
        tipo = payload.get('tipo', 'real')
        
        # Se há session_id, buscar dados da sessão
        if session_id:
            from models.cadastro_session import CadastroSession
            session = CadastroSession.query.get(session_id)
            if session and session.user_id == current_user.id:
                dados = session.dados_coletados or {}
                tipo = session.tipo_cadastro
        
        service = CadastroAgentService()
        resultado = service.finalizar_cadastro_completo(dados, tipo, session_id)
        
        if resultado['status'] == 'sucesso':
            return jsonify({
                'success': True,
                'data': resultado
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('mensagem', 'Erro ao finalizar cadastro')
            }), 400
    except Exception as e:
        logger.error(f"Erro ao finalizar cadastro: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/continuar-cadastro/<int:empresa_id>', methods=['GET'])
@login_required
def api_continuar_cadastro(empresa_id):
    """Continua cadastro de uma empresa existente"""
    try:
        from services.cadastro_agent_service import CadastroAgentService
        
        service = CadastroAgentService()
        resultado = service.continuar_cadastro_empresa(empresa_id)
        
        return jsonify({
            'success': True,
            'data': resultado
        })
    except Exception as e:
        logger.error(f"Erro ao continuar cadastro: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/teste-conformidade', methods=['POST'])
@login_required
def api_teste_conformidade():
    """Executa o teste de conformidade usando o catálogo de endereçamento."""
    try:
        from services.app_compliance_service import AppComplianceService

        payload = request.get_json(silent=True) or {}
        scope = payload.get('scope', 'full')
        page_code = payload.get('page_code')
        test_context = payload.get('test_context') or {}
        filtro = (payload.get('filter') or 'all').lower()
        limit = payload.get('limit')
        try:
            highlight_limit = max(1, min(int(limit), 15)) if limit else 5
        except (TypeError, ValueError):
            highlight_limit = 5

        service = AppComplianceService()
        relatorio = service.run(
            scope=scope,
            page_code=page_code,
            probe_routes=True,
            probe_user_id=current_user.id,
            persist=True,
            test_context=test_context,
        )
        mensagem = service.format_message(
            relatorio,
            highlight_limit=highlight_limit,
            severity=filtro,
        )
        preview = service.build_preview(relatorio)

        data = {
            'mensagem': mensagem,
            'estado': 'teste_conformidade',
            'relatorio': relatorio,
            'filtro': filtro,
        }
        if relatorio.get('report_id'):
            data['relatorio_id'] = relatorio['report_id']
        if relatorio.get('test_context'):
            data['test_context'] = relatorio['test_context']
        if preview:
            data['dados_preview'] = preview

        if relatorio.get('results'):
            acoes = data.setdefault('acoes', [])
            acoes.append(
                {
                    'text': 'Ver detalhes completos',
                    'action': 'mostrar_relatorio_conformidade',
                    'type': 'secondary',
                }
            )
            acoes.append(
                {
                    'text': 'Ver histórico recente',
                    'action': 'ver_historico_conformidade',
                    'type': 'secondary',
                }
            )
            if relatorio.get('report_id'):
                acoes.append(
                    {
                        'text': 'Exportar TXT',
                        'action': 'exportar_relatorio_txt',
                        'type': 'secondary',
                        'data': {'filter': filtro},
                    }
                )
                acoes.append(
                    {
                        'text': 'Exportar PDF',
                        'action': 'exportar_relatorio_pdf',
                        'type': 'secondary',
                        'data': {'filter': filtro},
                    }
                )

        return jsonify({'success': True, 'data': data})
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error("Erro ao executar teste de conformidade: %s", exc)
        return jsonify({
            'success': False,
            'error': 'Falha ao executar o teste de conformidade.'
        }), 500


@agents_bp.route('/api/teste-conformidade/historico', methods=['GET'])
@login_required
def api_teste_conformidade_historico():
    """Lista os últimos relatórios de conformidade salvos pelo usuário."""
    try:
        from models.app_compliance_report import AppComplianceReport

        reports = (
            AppComplianceReport.query.filter(
                (AppComplianceReport.user_id == current_user.id)
                | (AppComplianceReport.user_id.is_(None))
            )
            .order_by(AppComplianceReport.generated_at.desc())
            .limit(10)
            .all()
        )

        historico = []
        for report in reports:
            historico.append(
                {
                    'id': report.id,
                    'scope': report.scope,
                    'requested_code': report.requested_code,
                    'generated_at': report.generated_at.isoformat() if report.generated_at else None,
                    'total_pages': report.total_pages,
                    'ok': report.ok_count,
                    'warn': report.warn_count,
                    'fail': report.fail_count,
                    'test_context': (report.overview or {}).get('test_context') if report.overview else None,
                }
            )

        return jsonify({'success': True, 'data': historico})
    except Exception as exc:
        logger.error("Erro ao listar histórico de conformidade: %s", exc)
        return jsonify({'success': False, 'error': 'Não foi possível carregar o histórico.'}), 500


@agents_bp.route('/api/teste-conformidade/<int:report_id>', methods=['GET'])
@login_required
def api_teste_conformidade_relatorio(report_id: int):
    """Retorna detalhes completos de um relatório salvo."""
    try:
        from models.app_compliance_report import AppComplianceReport
        from services.app_compliance_service import AppComplianceService

        report = AppComplianceReport.query.get_or_404(report_id)
        if report.user_id and report.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Relatório não disponível.'}), 403

        relatorio = _serialize_compliance_report(report)
        service = AppComplianceService()
        mensagem = service.format_message(relatorio)
        preview = service.build_preview(relatorio)
        data = {
            'mensagem': mensagem,
            'relatorio': relatorio,
            'relatorio_id': report.id,
            'filtro': 'all',
        }
        if relatorio.get('test_context'):
            data['test_context'] = relatorio['test_context']
        if preview:
            data['dados_preview'] = preview

        return jsonify({'success': True, 'data': data})
    except Exception as exc:
        logger.error("Erro ao carregar relatório %s: %s", report_id, exc)
        return jsonify({'success': False, 'error': 'Não foi possível abrir o relatório informado.'}), 500


@agents_bp.route('/api/teste-conformidade/<int:report_id>/export', methods=['GET'])
@login_required
def api_teste_conformidade_export(report_id: int):
    """Exporta um relatório salvo."""
    try:
        from models.app_compliance_report import AppComplianceReport
        from services.app_compliance_service import AppComplianceService

        formato = (request.args.get('format') or 'txt').lower()
        filtro = (request.args.get('filter') or 'all').lower()

        report = AppComplianceReport.query.get_or_404(report_id)
        if report.user_id and report.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Relatório não disponível.'}), 403

        relatorio = _serialize_compliance_report(report)
        service = AppComplianceService()

        if formato == 'pdf':
            try:
                pdf_bytes = service.generate_pdf_report(relatorio, severity=filtro)
            except RuntimeError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400
            buffer = io.BytesIO(pdf_bytes)
            buffer.seek(0)
            filename = f"relatorio_conformidade_{report_id}_{filtro}.pdf"
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename,
            )

        texto = service.generate_text_report(relatorio, severity=filtro)
        response = make_response(texto)
        filename = f"relatorio_conformidade_{report_id}_{filtro}.txt"
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=\"{filename}\"'
        return response
    except Exception as exc:
        logger.error("Erro ao exportar relatório %s: %s", report_id, exc)
        return jsonify({'success': False, 'error': 'Não foi possível exportar o relatório.'}), 500


def _serialize_compliance_report(report):
    return {
        'report_id': report.id,
        'scope': report.scope,
        'requested_code': report.requested_code,
        'generated_at': report.generated_at.isoformat() if report.generated_at else None,
        'overview': report.overview
        or {
            'total_pages': report.total_pages,
            'ok': report.ok_count,
            'warn': report.warn_count,
            'fail': report.fail_count,
        },
        'results': [
            {
                'page_code': item.page_code,
                'page_name': item.page_name,
                'page_route': item.page_route,
                'status': item.status,
                'primary_issue': item.primary_issue,
                'checks': item.checks,
            }
            for item in report.items
        ],
        'test_context': (report.overview or {}).get('test_context') if report.overview else None,
    }


@agents_bp.route('/api/buscar-cnpj/<cnpj>', methods=['GET'])
@login_required
def api_buscar_cnpj(cnpj):
    """Busca dados da empresa por CNPJ"""
    try:
        from services.cadastro_agent_service import CadastroAgentService
        
        service = CadastroAgentService()
        cnpj_limpo = service._limpar_cnpj(cnpj)
        
        if not cnpj_limpo or len(cnpj_limpo) != 14:
            return jsonify({
                'success': False,
                'error': 'CNPJ inválido'
            }), 400
        
        dados = service._buscar_dados_cnpj(cnpj_limpo)
        
        if dados:
            return jsonify({
                'success': True,
                'data': dados
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Dados não encontrados'
            }), 404
    except Exception as e:
        logger.error(f"Erro ao buscar CNPJ: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===================================================================
# CRUD TRADICIONAL DE CADASTROS (Sessões de Cadastro)
# ===================================================================

@agents_bp.route('/cadastros', endpoint='cadastros_list')
@login_required
def cadastros_list():
    """Lista todas as sessões de cadastro do usuário"""
    from models.cadastro_session import CadastroSession
    from flask_login import current_user
    
    sessoes = CadastroSession.query.filter_by(
        user_id=current_user.id,
        is_deleted=False
    ).order_by(CadastroSession.updated_at.desc()).all()
    
    return render_template('cadastros_list.html', sessoes=sessoes, active_id='cadastros-list')


@agents_bp.route('/cadastros/new', endpoint='cadastros_new')
@login_required
def cadastros_new():
    """Formulário para criar nova sessão de cadastro"""
    return render_template('cadastro_form.html', form_mode='create', sessao=None, active_id='cadastros-new')


@agents_bp.route('/cadastros/<int:session_id>', endpoint='cadastros_view')
@login_required
def cadastros_view(session_id):
    """Visualizar/editar sessão de cadastro"""
    from models.cadastro_session import CadastroSession
    from flask_login import current_user
    
    sessao = CadastroSession.query.get_or_404(session_id)
    
    # Verificar se pertence ao usuário
    if sessao.user_id != current_user.id:
        from flask import abort
        abort(403)
    
    return render_template('cadastro_form.html', form_mode='edit', sessao=sessao, active_id='cadastros-view')


# APIs REST para CRUD tradicional
@agents_bp.route('/api/cadastros', methods=['GET'])
@login_required
def api_cadastros_list():
    """Lista sessões de cadastro (API)"""
    try:
        from models.cadastro_session import CadastroSession
        from flask_login import current_user
        
        sessoes = CadastroSession.query.filter_by(
            user_id=current_user.id,
            is_deleted=False
        ).order_by(CadastroSession.updated_at.desc()).all()
        
        return jsonify({
            'success': True,
            'data': [s.to_dict() for s in sessoes]
        })
    except Exception as e:
        logger.error(f"Erro ao listar cadastros: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/cadastros', methods=['POST'])
@login_required
def api_cadastros_create():
    """Cria nova sessão de cadastro"""
    try:
        from models.cadastro_session import CadastroSession
        from models import db
        from flask_login import current_user
        
        payload = request.get_json(silent=True) or {}
        tipo_cadastro = payload.get('tipo_cadastro', 'real')
        
        if tipo_cadastro not in ['real', 'modelo']:
            return jsonify({
                'success': False,
                'error': 'Tipo de cadastro inválido. Use "real" ou "modelo"'
            }), 400
        
        sessao = CadastroSession.criar_sessao(current_user.id, tipo_cadastro)
        
        return jsonify({
            'success': True,
            'data': sessao.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Erro ao criar cadastro: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/cadastros/<int:session_id>', methods=['GET'])
@login_required
def api_cadastros_get(session_id):
    """Busca sessão de cadastro específica"""
    try:
        from models.cadastro_session import CadastroSession
        from flask_login import current_user
        
        sessao = CadastroSession.query.get(session_id)
        
        if not sessao:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404
        
        if sessao.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403
        
        return jsonify({
            'success': True,
            'data': sessao.to_dict()
        })
    except Exception as e:
        logger.error(f"Erro ao buscar cadastro: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/cadastros/<int:session_id>', methods=['PUT'])
@login_required
def api_cadastros_update(session_id):
    """Atualiza sessão de cadastro"""
    try:
        from models.cadastro_session import CadastroSession
        from models import db
        from flask_login import current_user
        from datetime import datetime
        
        sessao = CadastroSession.query.get(session_id)
        
        if not sessao:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404
        
        if sessao.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403
        
        payload = request.get_json(silent=True) or {}
        
        # Atualizar campos permitidos
        if 'tipo_cadastro' in payload:
            if payload['tipo_cadastro'] not in ['real', 'modelo']:
                return jsonify({
                    'success': False,
                    'error': 'Tipo de cadastro inválido'
                }), 400
            sessao.tipo_cadastro = payload['tipo_cadastro']
        
        if 'estado' in payload:
            sessao.estado = payload['estado']
        
        if 'dados_coletados' in payload:
            sessao.update_dados(payload['dados_coletados'])
        
        if 'empresa_id' in payload:
            sessao.empresa_id = payload['empresa_id']
        
        if 'campo_atual' in payload:
            sessao.campo_atual = payload['campo_atual']
        
        if 'progresso' in payload:
            sessao.progresso = payload['progresso']
        
        sessao.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': sessao.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar cadastro: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agents_bp.route('/api/cadastros/<int:session_id>', methods=['DELETE'])
@login_required
def api_cadastros_delete(session_id):
    """Exclui sessão de cadastro (soft delete)"""
    try:
        from models.cadastro_session import CadastroSession
        from models import db
        from flask_login import current_user
        from datetime import datetime
        
        sessao = CadastroSession.query.get(session_id)
        
        if not sessao:
            return jsonify({
                'success': False,
                'error': 'Sessão não encontrada'
            }), 404
        
        if sessao.user_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Acesso negado'
            }), 403
        
        # Soft delete
        sessao.is_deleted = True
        sessao.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sessão excluída com sucesso'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir cadastro: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

