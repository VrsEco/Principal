"""
Seed da Base de Conhecimento (RAG) do Gestão Versus.

Este script popula o ChromaDB com o manual de uso do sistema, conceitos de
gestão, artigos de apoio, contatos de consultores e regras de negócio.

Execute: python src/intelligence/seed_knowledge.py
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.intelligence.rag import knowledge_base


# =============================================================================
# KNOWLEDGE BASE DO GESTÃO VERSUS
# Organizado por categorias, cada entrada é um "documento" vetorizado
# =============================================================================

DOCUMENTOS = [

    # =========================================================================
    # MÓDULO: MAPA DE PROCESSOS
    # =========================================================================
    {
        "text": (
            "MÓDULO: Mapa de Processos\n"
            "O Mapa de Processos (ou Arquitetura de Processos) é a espinha dorsal operacional de uma empresa. "
            "Ele organiza todos os Processos em uma hierarquia de 3 níveis:\n"
            "  1. ÁREA DE PROCESSO: Agrupamento macro (ex: Financeiro, Comercial, Operações, RH).\n"
            "  2. MACROPROCESSO: Subárea temática dentro de uma Área (ex: dentro de 'Financeiro' → 'Contas a Pagar', 'Contas a Receber').\n"
            "  3. PROCESSO: A atividade específica com POP (Procedimento Operacional Padrão) e passos detalhados.\n\n"
            "COMO CRIAR NO SISTEMA:\n"
            "- Acesse o menu lateral: Processos > Mapa de Processos.\n"
            "- Clique em '+ Nova Área' para iniciar a hierarquia.\n"
            "- Ou solicite ao Agente Sapiens: ele criará as Áreas, Macros e Processos diretamente via chat.\n\n"
            "ARTIGO DE REFERÊNCIA: https://versus.com.br/artigos/mapa-de-processos\n"
            "CONSULTOR ESPECIALISTA: Fale com seu consultor designado via Telegram ou e-mail."
        ),
        "metadata": {"categoria": "processos", "modulo": "mapa_processos", "tipo": "conceito"}
    },
    {
        "text": (
            "BOAS PRÁTICAS: Mapa de Processos\n"
            "Antes de cadastrar processos no sistema, recomenda-se:\n"
            "1. Levantar todas as atividades da empresa em um workshop presencial ou online.\n"
            "2. Agrupar as atividades por tema (ex: todas as atividades de vendas → Área Comercial).\n"
            "3. Identificar o 'Dono do Processo' (responsável pela atualização e conformidade).\n"
            "4. Definir a periodicidade: o processo é diário, semanal, mensal?\n"
            "5. Levantar os passos e responsáveis de cada atividade para montar o POP.\n\n"
            "NÍVEL DE MATURIDADE:\n"
            "- Nível 1 (Inicial): Processos existem apenas na cabeça das pessoas.\n"
            "- Nível 2 (Documentado): Processos documentados, mas não monitorados.\n"
            "- Nível 3 (Controlado): Processos medidos com indicadores.\n"
            "- Nível 4 (Otimizado): Melhoria contínua com base em dados.\n"
            "- Nível 5 (Inovador): Automatização e inteligência artificial integrados."
        ),
        "metadata": {"categoria": "processos", "modulo": "mapa_processos", "tipo": "boas_praticas"}
    },

    # =========================================================================
    # MÓDULO: PLANEJAMENTO ESTRATÉGICO (PEV)
    # =========================================================================
    {
        "text": (
            "MÓDULO: Planejamento Estratégico Visionário (PEV)\n"
            "O PEV é o plano de longo prazo da empresa (3 a 5 anos). Ele define:\n"
            "  - MISSÃO: Por que a empresa existe? Qual problema ela resolve?\n"
            "  - VISÃO: Onde a empresa quer chegar em X anos?\n"
            "  - VALORES: Quais princípios guiam as decisões?\n"
            "  - POSICIONAMENTO: Qual é o diferencial competitivo no mercado?\n"
            "  - ANÁLISE SWOT: Forças, Fraquezas, Oportunidades e Ameaças.\n\n"
            "COMO ACESSAR NO SISTEMA:\n"
            "- Menu: Planejamento > Crescimento (Growth) ou Implantação.\n"
            "- O sistema guia o preenchimento seção por seção.\n\n"
            "ARTIGO DE REFERÊNCIA: https://versus.com.br/artigos/planejamento-estrategico\n"
            "DICA: O Agente Estrategista pode ajudar a redigir a Missão, Visão e Valores com base no perfil da empresa."
        ),
        "metadata": {"categoria": "planejamento", "modulo": "pev", "tipo": "conceito"}
    },
    {
        "text": (
            "MÓDULO: OKRs (Objectives and Key Results)\n"
            "OKR é uma metodologia de gestão de metas que conecta os objetivos estratégicos às ações do dia a dia.\n"
            "  - OBJETIVO (O): Qualitativo, inspirador, de curto prazo (trimestral). Ex: 'Tornar-se referência regional em atendimento'.\n"
            "  - RESULTADO-CHAVE (KR): Quantitativo e mensurável. Ex: 'Atingir NPS de 70' ou 'Reduzir tempo de resposta para 2h'.\n\n"
            "REGRAS DE OURO dos OKRs:\n"
            "1. Máximo de 5 Objetivos por ciclo.\n"
            "2. Cada Objetivo deve ter no máximo 3-5 KRs.\n"
            "3. OKRs desafiadores: 70% de atingimento já é considerado sucesso.\n"
            "4. Revisão semanal (check-in) e avaliação trimestral.\n\n"
            "COMO CADASTRAR NO SISTEMA:\n"
            "- Menu: Planejamento > OKRs Globais ou OKRs por Área.\n"
            "- Ou peça ao Agente Estrategista para sugerir OKRs com base nos dados da empresa."
        ),
        "metadata": {"categoria": "planejamento", "modulo": "okrs", "tipo": "conceito"}
    },

    # =========================================================================
    # MÓDULO: PROJETOS
    # =========================================================================
    {
        "text": (
            "MÓDULO: Gestão de Projetos\n"
            "No Gestão Versus, Projetos são iniciativas de prazo definido com tarefas (atividades) atribuídas a colaboradores.\n\n"
            "ESTRUTURA:\n"
            "  - PROJETO: Container principal (ex: 'Lançamento do Produto X').\n"
            "  - TAREFA (Atividade): Ação específica vinculada ao projeto (ex: 'Criar landing page').\n"
            "  - COLABORADORES: Cada tarefa pode ter múltiplos responsáveis.\n"
            "  - HORAS: Registro de horas trabalhadas por tarefa e colaborador.\n\n"
            "STATUS DISPONÍVEIS:\n"
            "  not_started → in_progress → in_review → completed | cancelled\n\n"
            "COMO CRIAR:\n"
            "- Menu: Projetos > Novo Projeto.\n"
            "- Ou via Reunião: ao finalizar uma reunião, as atividades decididas viram tarefas de projeto automaticamente.\n\n"
            "ARTIGO DE REFERÊNCIA: https://versus.com.br/artigos/gestao-de-projetos"
        ),
        "metadata": {"categoria": "projetos", "modulo": "projetos", "tipo": "conceito"}
    },

    # =========================================================================
    # MÓDULO: MEU TRABALHO (MY WORK)
    # =========================================================================
    {
        "text": (
            "MÓDULO: Meu Trabalho\n"
            "'Meu Trabalho' é a central de atividades do colaborador. Ela agrega:\n"
            "  - Tarefas de Projetos atribuídas ao usuário.\n"
            "  - Instâncias de Processos (rotinas/POPs) agendadas para o usuário.\n\n"
            "FUNCIONALIDADES:\n"
            "  - Visualização por Status: Abertas, Em Andamento, Concluídas, Atrasadas.\n"
            "  - Filtros por Empresa, Projeto e Processo.\n"
            "  - Registro de horas trabalhadas por atividade.\n"
            "  - Upload de evidências (fotos, documentos) ao concluir.\n\n"
            "COMO ACESSAR: Menu > Meu Trabalho.\n"
            "DICA: O Agente Operations pode consultar as suas atividades via chat e alertar sobre prazos próximos.\n"
            "DICA: Pelo Telegram, você pode dizer 'Sapiens, quais são minhas atividades de hoje?' e receber a lista."
        ),
        "metadata": {"categoria": "tarefas", "modulo": "my_work", "tipo": "conceito"}
    },

    # =========================================================================
    # MÓDULO: REUNIÕES
    # =========================================================================
    {
        "text": (
            "MÓDULO: Gestão de Reuniões\n"
            "O módulo de Reuniões permite planejar, executar e documentar reuniões gerenciais com geração automática de ATA.\n\n"
            "CICLO DE VIDA DE UMA REUNIÃO:\n"
            "  1. RASCUNHO (draft): Criação com título, data, convidados e pauta.\n"
            "  2. EM ANDAMENTO (in_progress): Reunião iniciada, partipantes confirmados, pontos discutidos registrados.\n"
            "  3. CONCLUÍDA (completed): Reunião encerrada, ATA gerada, atividades criadas no projeto vinculado.\n\n"
            "FUNCIONALIDADES:\n"
            "  - Envio de convite por e-mail e WhatsApp para participantes.\n"
            "  - Cadastro de pautas pré-definidas (Banco de Pautas).\n"
            "  - Criação automática de um Projeto vinculado à reunião.\n"
            "  - Sincronização de atividades decididas como tarefas no projeto.\n"
            "  - Envio da ATA por e-mail e WhatsApp ao encerrar.\n\n"
            "COMO USAR VIA CHAT:\n"
            "'Sapiens, crie uma reunião sobre Revisão de Metas para amanhã às 14h com Pedro e Ana.'"
        ),
        "metadata": {"categoria": "reunioes", "modulo": "reunioes", "tipo": "conceito"}
    },

    # =========================================================================
    # MÓDULO: INDICADORES (KPIs)
    # =========================================================================
    {
        "text": (
            "MÓDULO: Indicadores de Desempenho (KPIs)\n"
            "Indicadores são métricas que medem o desempenho da empresa em áreas estratégicas.\n\n"
            "TIPOS DE INDICADORES:\n"
            "  - Financeiros: Faturamento, Margem Bruta, EBITDA, Inadimplência.\n"
            "  - Operacionais: Tempo de Ciclo, Taxa de Conformidade de Processos, SLA.\n"
            "  - Comerciais: Taxa de Conversão, CAC (Custo de Aquisição de Cliente), LTV.\n"
            "  - RH: Turnover, Absenteísmo, NPS interno (satisfação da equipe).\n\n"
            "COMO CADASTRAR NO SISTEMA:\n"
            "- Menu: Indicadores > Novo Indicador.\n"
            "- Defina: Nome, Unidade (%, R$, unidades), Meta, Periodicidade e Responsável.\n\n"
            "ARTIGO: https://versus.com.br/artigos/indicadores-de-desempenho\n"
            "DICA: O Agente Estrategista pode sugerir KPIs relevantes para o setor da sua empresa."
        ),
        "metadata": {"categoria": "indicadores", "modulo": "kpis", "tipo": "conceito"}
    },

    # =========================================================================
    # MÓDULO: USUÁRIOS E PERMISSÕES
    # =========================================================================
    {
        "text": (
            "MÓDULO: Gestão de Usuários e Permissões\n"
            "O sistema possui 3 perfis de acesso (roles):\n\n"
            "  1. ADMIN: Acesso total. Pode criar usuários, configurar empresas, ver todos os dados.\n"
            "  2. COLLABORATOR (Colaborador): Acesso às suas tarefas, processos e indicadores. Não vê dados financeiros sensíveis.\n"
            "  3. CLIENT (Cliente): Acesso limitado. Pode consultar dashboards e relatórios autorizados. Pode interagir com o Sapiens.\n\n"
            "COMO CRIAR USUÁRIOS:\n"
            "- Menu: Admin > Usuários > Novo Usuário.\n"
            "- Via Chat: 'Sapiens, cadastre o usuário João Silva com e-mail joao@empresa.com como colaborador'.\n\n"
            "VINCULAÇÃO EMPRESA-USUÁRIO:\n"
            "Um usuário pode estar vinculado a MÚLTIPLAS empresas. Cada vínculo é um 'Employee' (colaborador).\n"
            "Para vincular: Admin > Usuários > Selecionar Usuário > Vincular Empresa."
        ),
        "metadata": {"categoria": "usuarios", "modulo": "usuarios_permissoes", "tipo": "conceito"}
    },

    # =========================================================================
    # REGRAS DE NEGÓCIO E APROVAÇÕES
    # =========================================================================
    {
        "text": (
            "REGRAS DE APROVAÇÃO E LIMITES DE AUTORIZAÇÃO:\n"
            "1. Compras acima de R$ 5.000 requerem aprovação de 2 diretores e 3 cotações documentadas.\n"
            "2. Alteração de prazo de atividade de outro colaborador requer autorização do supervisor direto.\n"
            "3. Desativação de empresa só pode ser feita por administradores do sistema.\n"
            "4. Exclusão de usuários segue o fluxo: Inativação → Período de quarentena (30 dias) → Exclusão definitiva.\n"
            "5. Pagamentos agendados para sábado ou domingo são automaticamente movidos para a segunda-feira seguinte.\n"
            "6. Notas fiscais acima de R$ 10.000 precisam de aprovação de dois diretores antes do lançamento.\n"
            "7. Para erros de conexão com a SEFAZ, o sistema tentará novamente 3 vezes antes de gerar alerta."
        ),
        "metadata": {"categoria": "regras", "modulo": "aprovacoes", "tipo": "regra_negocio"}
    },
    {
        "text": (
            "REGRAS DE CONFORMIDADE FISCAL:\n"
            "1. XMLs de NF-e sem o campo 'xMotivo' preenchido em casos de rejeição não são aceitos.\n"
            "2. Apurações de impostos mensais devem ser concluídas até o dia 20 do mês seguinte.\n"
            "3. O SPED Fiscal deve ser transmitido até o último dia útil do mês subsequente ao período.\n"
            "4. Guias de ICMS-ST devem ser pagas até o dia 9 do mês seguinte.\n"
            "5. A folha de pagamento deve ser aprovada pelo RH-Gerente antes de qualquer lançamento bancário."
        ),
        "metadata": {"categoria": "fiscal", "modulo": "conformidade_fiscal", "tipo": "regra_negocio"}
    },

    # =========================================================================
    # DICAS DE USO DO SAPIENS (Meta-conhecimento)
    # =========================================================================
    {
        "text": (
            "COMO USAR O AGENTE SAPIENS (Guia Rápido):\n"
            "O Sapiens pode ser acionado pelo chat do sistema ou pelo Telegram/WhatsApp.\n\n"
            "EXEMPLOS DE COMANDOS QUE ELE ENTENDE:\n"
            "  - 'Sapiens, como eu crio um processo?'\n"
            "  - 'Sapiens, quais são minhas tarefas hoje?'\n"
            "  - 'Sapiens, cadastre a Área Financeiro para mim.'\n"
            "  - 'Sapiens, terminei a atividade X, marque como concluída.'\n"
            "  - 'Sapiens, quanto tempo falta para o prazo do projeto Y?'\n"
            "  - 'Sapiens, encontrei um erro na tela Z, veja o print: [imagem]'\n"
            "  - 'Sapiens, chame o consultor para me ajudar com o organograma.'\n\n"
            "O QUE O SAPIENS NÃO FAZ (por segurança):\n"
            "  - Não deleta registros permanentemente.\n"
            "  - Não acessa dados de outras empresas.\n"
            "  - Não realiza pagamentos ou transações financeiras.\n"
            "  - Não altera permissões de outros usuários sem autorização de Admin."
        ),
        "metadata": {"categoria": "sapiens", "modulo": "guia_uso", "tipo": "tutorial"}
    },

    # =========================================================================
    # MÓDULO: EFICIÊNCIA E ANÁLISE DE COLABORADORES
    # =========================================================================
    {
        "text": (
            "MÓDULO: Análise de Eficiência\n"
            "A Análise de Eficiência avalia o desempenho de cada colaborador com base em:\n"
            "  - SCORE REAL: Pontos ganhos pelas entregas concluídas no prazo.\n"
            "  - SCORE POTENCIAL: Pontos totais das atividades que o colaborador poderia ter concluído.\n"
            "  - EFICIÊNCIA (%): Score Real / Score Potencial × 100.\n\n"
            "INTERPRETAÇÃO:\n"
            "  - Acima de 80%: Alto desempenho.\n"
            "  - Entre 60-80%: Desempenho regular, atenção ao volume de trabalho.\n"
            "  - Abaixo de 60%: Sobrecarga ou baixo engajamento. Investigar causa raiz.\n\n"
            "COMO ACESSAR: Menu > Eficiência > Análise por Colaborador.\n"
            "DICA: O Agente Operations pode gerar um relatório de eficiência via chat: "
            "'Sapiens, como está a eficiência da equipe este mês?'"
        ),
        "metadata": {"categoria": "eficiencia", "modulo": "analise_eficiencia", "tipo": "conceito"}
    },

    # =========================================================================
    # ONBOARDING: PRIMEIROS PASSOS
    # =========================================================================
    {
        "text": (
            "ONBOARDING: Primeiros Passos com o Gestão Versus\n"
            "Sequência recomendada para novos clientes:\n\n"
            "SEMANA 1 - Configuração Base:\n"
            "  1. Cadastrar a empresa (CNPJ, Segmento, Logo).\n"
            "  2. Criar os usuários (Admin, Gestores, Colaboradores).\n"
            "  3. Configurar o Plano Estratégico (Missão, Visão, Valores).\n\n"
            "SEMANA 2 - Estrutura Operacional:\n"
            "  4. Montar o Mapa de Processos (Áreas → Macros → Processos).\n"
            "  5. Cadastrar os primeiros POPs com seus passos.\n"
            "  6. Criar os primeiros Projetos em andamento.\n\n"
            "SEMANA 3 - Inteligência:\n"
            "  7. Configurar Indicadores de Desempenho (KPIs).\n"
            "  8. Ativar os OKRs do ciclo atual.\n"
            "  9. Treinar a equipe no 'Meu Trabalho'.\n\n"
            "SEMANA 4 - Autonomia:\n"
            " 10. Ativar o Agente Sapiens para suporte da equipe.\n"
            " 11. Configurar alertas automáticos de prazo.\n"
            " 12. Realizar a primeira Reunião Gerencial pelo sistema.\n\n"
            "CONSULTOR: Seu consultor designado acompanha cada etapa. Contate via suporte@gestaoversus.com.br"
        ),
        "metadata": {"categoria": "onboarding", "modulo": "primeiros_passos", "tipo": "tutorial"}
    },
]


def seed():
    """Popula a base de conhecimento com todos os documentos do Gestão Versus."""
    print(f"\n🌱 Iniciando seed da KnowledgeBase...")
    print(f"📚 Total de documentos a inserir: {len(DOCUMENTOS)}\n")

    textos = [doc["text"] for doc in DOCUMENTOS]
    metadados = [doc["metadata"] for doc in DOCUMENTOS]

    success = knowledge_base.add_documents(textos, metadados)

    if success:
        print(f"\n✅ KnowledgeBase populada com sucesso!")
        print(f"   {len(DOCUMENTOS)} documentos vetorizados e armazenados no ChromaDB.")
        print(f"   O Agente Sapiens agora tem acesso ao Manual Completo do Gestão Versus.\n")
    else:
        print(f"\n❌ Erro ao popular a KnowledgeBase. Verifique os logs acima.\n")


if __name__ == "__main__":
    seed()
