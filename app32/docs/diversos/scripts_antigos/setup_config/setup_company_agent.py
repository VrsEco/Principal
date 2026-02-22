#!/usr/bin/env python3
"""
Script para criar agente de análise da empresa diretamente no banco
"""

import sqlite3
import json
from datetime import datetime


def create_company_analysis_agent():
    """Criar agente para análise da empresa diretamente no banco"""
    print("🤖 Criando agente de análise da empresa...")

    try:
        conn = sqlite3.connect("pevapp22.db")
        cursor = conn.cursor()

        # Verificar se a tabela ai_agents existe
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_agents'"
        )
        if not cursor.fetchone():
            print("❌ Tabela ai_agents não encontrada")
            return False

        # Dados do agente
        agent_data = {
            "name": "Analista de Identidade Empresarial",
            "description": "Agente especializado em análise da identidade e posicionamento da empresa",
            "page": "company",
            "section": "analyses",
            "button_text": "Analisar Identidade",
            "prompt_template": """Você é um analista especializado em identidade empresarial. 

Analise os seguintes dados da empresa:
- Nome Fantasia: {trade_name}
- Razão Social: {legal_name}
- Setor: {industry}
- Localização: {location}
- Descrição: {description}

Com base nesses dados, forneça uma análise estruturada incluindo:

1. **IDENTIDADE VISUAL E MARCA**
   - Avaliação do nome da empresa
   - Sugestões de posicionamento de marca
   - Identidade visual recomendada

2. **POSICIONAMENTO NO MERCADO**
   - Análise do setor de atuação
   - Oportunidades de mercado
   - Diferenciação competitiva

3. **PRESENÇA DIGITAL**
   - Estratégia para site corporativo
   - Presença em redes sociais
   - Marketing digital recomendado

4. **RECOMENDAÇÕES ESTRATÉGICAS**
   - Próximos passos para fortalecer a identidade
   - Ações prioritárias
   - Métricas de acompanhamento

Seja específico e prático nas recomendações.""",
            "required_fields": "trade_name,legal_name,industry,location,description",
            "optional_fields": "website,social_media,mission,vision,values",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # Inserir agente
        cursor.execute(
            """
            INSERT INTO ai_agents (
                name, description, page, section, button_text, 
                prompt_template, required_fields, optional_fields, 
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                agent_data["name"],
                agent_data["description"],
                agent_data["page"],
                agent_data["section"],
                agent_data["button_text"],
                agent_data["prompt_template"],
                agent_data["required_fields"],
                agent_data["optional_fields"],
                agent_data["status"],
                agent_data["created_at"],
                agent_data["updated_at"],
            ),
        )

        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"✅ Agente criado com sucesso! ID: {agent_id}")
        print(f"📝 Nome: {agent_data['name']}")
        print(f"🎯 Página: {agent_data['page']}/{agent_data['section']}")
        print(f"🔘 Botão: {agent_data['button_text']}")

        return agent_id

    except Exception as e:
        print(f"❌ Erro ao criar agente: {e}")
        return False


def create_sample_company_data():
    """Criar dados de empresa de exemplo"""
    print("\n🏢 Criando dados de empresa de exemplo...")

    try:
        conn = sqlite3.connect("pevapp22.db")
        cursor = conn.cursor()

        # Verificar se a tabela company_data existe
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='company_data'"
        )
        if not cursor.fetchone():
            print("❌ Tabela company_data não encontrada")
            return False

        # Dados da empresa de exemplo
        company_data = {
            "plan_id": 1,
            "trade_name": "TechCorp Solutions",
            "legal_name": "TechCorp Soluções Tecnológicas Ltda",
            "industry": "Tecnologia da Informação",
            "location": "São Paulo, SP",
            "description": "Empresa especializada em soluções tecnológicas para médias e grandes empresas",
            "website": "https://techcorp.com.br",
            "social_media": "LinkedIn, Instagram, Facebook",
            "mission": "Transformar negócios através da tecnologia",
            "vision": "Ser referência em soluções tecnológicas no Brasil",
            "values": "Inovação, Qualidade, Transparência, Colaboração",
        }

        # Verificar se já existe dados para o plano
        cursor.execute(
            "SELECT id FROM company_data WHERE plan_id = ?", (company_data["plan_id"],)
        )
        existing = cursor.fetchone()

        if existing:
            print("⚠️ Dados da empresa já existem para este plano")
            return True

        # Inserir dados da empresa
        cursor.execute(
            """
            INSERT INTO company_data (
                plan_id, trade_name, legal_name, industry, location, 
                description, website, social_media, mission, vision, values
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                company_data["plan_id"],
                company_data["trade_name"],
                company_data["legal_name"],
                company_data["industry"],
                company_data["location"],
                company_data["description"],
                company_data["website"],
                company_data["social_media"],
                company_data["mission"],
                company_data["vision"],
                company_data["values"],
            ),
        )

        conn.commit()
        conn.close()

        print("✅ Dados da empresa criados com sucesso!")
        print(f"🏢 Empresa: {company_data['trade_name']}")
        print(f"🏭 Setor: {company_data['industry']}")
        print(f"📍 Localização: {company_data['location']}")

        return True

    except Exception as e:
        print(f"❌ Erro ao criar dados da empresa: {e}")
        return False


def main():
    """Função principal"""
    print("🚀 CONFIGURANDO AGENTE DE ANÁLISE DA EMPRESA")
    print("=" * 60)

    # 1. Criar dados de empresa de exemplo
    company_ok = create_sample_company_data()

    # 2. Criar agente de análise
    agent_ok = create_company_analysis_agent()

    print("\n" + "=" * 60)
    print("📋 RESUMO DA CONFIGURAÇÃO:")
    print(f"✅ Dados da empresa: {'OK' if company_ok else 'FALHA'}")
    print(f"✅ Agente criado: {'OK' if agent_ok else 'FALHA'}")

    if company_ok and agent_ok:
        print(f"\n🎯 PRÓXIMOS PASSOS:")
        print(f"1. Acesse: http://127.0.0.1:5002/dashboard")
        print(f"2. Vá para a seção 'Agentes de IA'")
        print(f"3. Encontre o agente 'Analista de Identidade Empresarial'")
        print(f"4. Acesse um planejamento: http://127.0.0.1:5002/plans/1/company")
        print(f"5. Clique em 'Analisar Identidade' para testar")
        print(f"\n📊 O agente analisará:")
        print(f"   - Identidade visual e marca")
        print(f"   - Posicionamento no mercado")
        print(f"   - Presença digital")
        print(f"   - Recomendações estratégicas")
    else:
        print(f"\n❌ Configuração incompleta. Verifique os erros acima.")


if __name__ == "__main__":
    main()
