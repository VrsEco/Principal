#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PEVAPP24 - Create AI Agents Table
Script to create the ai_agents table in SQLite database
"""

import sqlite3
import os
from datetime import datetime


def create_ai_agents_table():
    """Create ai_agents table in SQLite database"""

    # Database file path
    db_path = "pevapp22.db"

    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create ai_agents table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                version TEXT DEFAULT '1.0',
                status TEXT DEFAULT 'active',
                page TEXT NOT NULL,
                section TEXT NOT NULL,
                button_text TEXT NOT NULL,
                required_data TEXT,
                optional_data TEXT,
                prompt_template TEXT,
                format_type TEXT DEFAULT 'markdown',
                output_field TEXT DEFAULT 'ai_insights',
                response_template TEXT,
                timeout INTEGER DEFAULT 300,
                max_retries INTEGER DEFAULT 3,
                execution_mode TEXT DEFAULT 'sequential',
                cache_enabled BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        print("✅ Tabela 'ai_agents' criada com sucesso!")

        # Insert sample agent for testing
        sample_agent = {
            "id": "market_agent_v1",
            "name": "Agente de Mercado",
            "description": "Especialista em pesquisa de mercado externa",
            "version": "1.0",
            "status": "active",
            "page": "company",
            "section": "analyses",
            "button_text": "Gerar buscas e análises de IA",
            "required_data": '["trade_name", "cnpj", "cnaes", "coverage_physical", "coverage_online", "financial_data"]',
            "optional_data": '["market_info", "experience_segment", "mission", "vision", "values"]',
            "prompt_template": """Como Especialista em Pesquisa de Mercado, realize uma análise externa completa da empresa {trade_name}.

DADOS DA EMPRESA PARA PESQUISA:
- Nome: {trade_name}
- CNPJ: {cnpj}
- CNAEs: {cnaes}
- Cobertura Física: {coverage_physical}
- Cobertura Online: {coverage_online}
- Experiência no Segmento: {experience_segment}

DADOS FINANCEIROS:
{financial_data}

INFORMAÇÕES DE MERCADO EXISTENTES:
{market_info}

TAREFAS DE PESQUISA:

1. SEGMENTAÇÃO DE MERCADO:
   - Identifique o segmento específico de atuação
   - Classifique como B2B, B2C ou B2B2C
   - Mapeie subssegmentos e segmentos adjacentes

2. ANÁLISE DE MARGENS:
   - Compare as margens com benchmarks do setor
   - Identifique linhas com performance acima/média/abaixo
   - Analise tendências de margem no mercado

3. TAMANHO DO MERCADO:
   - Estime TAM (Total Addressable Market)
   - Calcule SAM (Serviceable Addressable Market)
   - Identifique SOM (Serviceable Obtainable Market)
   - Projete crescimento futuro

4. ANÁLISE COMPETITIVA:
   - Mapeie concorrentes diretos e indiretos
   - Avalie concentração do mercado
   - Analise atuação geográfica dos concorrentes
   - Identifique diferenciação competitiva

5. PRESENÇA DIGITAL:
   - Analise website (SEO, performance, UX)
   - Avalie presença em redes sociais
   - Verifique presença em marketplaces
   - Analise estratégia de marketing digital

6. REPUTAÇÃO ONLINE:
   - Pesquise avaliações no Google My Business
   - Analise reclamações no Reclame Aqui
   - Verifique sentiment nas redes sociais
   - Consulte processos judiciais

FORMATO DE RESPOSTA:
Use o formato estruturado definido e seja específico com dados e fontes quando possível.""",
            "format_type": "markdown",
            "output_field": "ai_insights",
            "response_template": """# PESQUISA DE MERCADO - {trade_name}
*Gerado em: {data_atual}*

## 📊 RESUMO EXECUTIVO
- **Segmento Identificado**: [Segmento específico]
- **Tamanho do Mercado**: [TAM/SAM/SOM estimados]
- **Posicionamento Competitivo**: [Resumo da concorrência]
- **Presença Digital**: [Status geral da presença online]
- **Reputação**: [Resumo da reputação online]

## 🎯 1. SEGMENTAÇÃO DE MERCADO
[Conteúdo da análise...]

## 💰 2. ANÁLISE DE MARGENS
[Conteúdo da análise...]

## 📈 3. TAMANHO DO MERCADO
[Conteúdo da análise...]

## 🏆 4. ANÁLISE COMPETITIVA
[Conteúdo da análise...]

## 💻 5. PRESENÇA DIGITAL
[Conteúdo da análise...]

## ⭐ 6. REPUTAÇÃO E AVALIAÇÕES
[Conteúdo da análise...]

## 🎯 7. OPORTUNIDADES IDENTIFICADAS
[Conteúdo da análise...]

## 📊 8. RECOMENDAÇÕES PRIORIZADAS
[Conteúdo da análise...]

---
*Pesquisa realizada pelo Agente de Mercado PEVAPP24*""",
            "timeout": 300,
            "max_retries": 3,
            "execution_mode": "sequential",
            "cache_enabled": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        cursor.execute(
            """
            INSERT OR IGNORE INTO ai_agents (
                id, name, description, version, status, page, section, button_text,
                required_data, optional_data, prompt_template, format_type,
                output_field, response_template, timeout, max_retries,
                execution_mode, cache_enabled, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                sample_agent["id"],
                sample_agent["name"],
                sample_agent["description"],
                sample_agent["version"],
                sample_agent["status"],
                sample_agent["page"],
                sample_agent["section"],
                sample_agent["button_text"],
                sample_agent["required_data"],
                sample_agent["optional_data"],
                sample_agent["prompt_template"],
                sample_agent["format_type"],
                sample_agent["output_field"],
                sample_agent["response_template"],
                sample_agent["timeout"],
                sample_agent["max_retries"],
                sample_agent["execution_mode"],
                sample_agent["cache_enabled"],
                sample_agent["created_at"],
                sample_agent["updated_at"],
            ),
        )

        conn.commit()
        conn.close()

        print("✅ Agente de exemplo 'market_agent_v1' inserido com sucesso!")
        print("🎯 Sistema de configuração de agentes de IA está pronto!")

        return True

    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PEVAPP24 - CRIAÇÃO DA TABELA DE AGENTES DE IA")
    print("=" * 60)

    success = create_ai_agents_table()

    if success:
        print("\n🚀 PRÓXIMOS PASSOS:")
        print(
            "1. Acesse o Dashboard Principal e vá para a seção 'Inteligência Artificial'"
        )
        print("2. Visualize o agente de exemplo criado")
        print("3. Crie novos agentes conforme necessário")
        print("4. Configure prompts e templates personalizados")
    else:
        print("\n❌ Falha na criação da tabela. Verifique os logs acima.")

    print("=" * 60)
