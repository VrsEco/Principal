#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de Governança de Banco de Dados - Módulo PEV
Usa agente IA especializado em banco de dados para analisar a situação atual
e recomendar a melhor abordagem para migrations.
"""
import os
import sys
from pathlib import Path
from typing import Dict, List
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar path do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI


class DatabaseGovernanceAnalyzer:
    """Agente IA especializado em governança de banco de dados."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1  # Muito determinístico para análise técnica
        )
        
        self.migrations_path = ROOT_DIR / "migrations"
        self.output_path = ROOT_DIR / "docs" / "database_governance"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        self.system_prompt = """
        Você é um DBA Sênior e Especialista em Governança de Banco de Dados.
        
        Sua especialidade:
        - PostgreSQL (configuração, otimização, migrations)
        - Estratégias de migration (Alembic, Flyway, SQL puro)
        - Governança de dados e versionamento
        - Análise de estruturas existentes
        - Recomendações de melhores práticas
        
        Sua missão:
        Analisar a estrutura atual de migrations do projeto e recomendar a melhor
        abordagem para implementar as novas tabelas do módulo PEV, considerando:
        
        1. **Compatibilidade**: Com a estrutura existente
        2. **Governança**: Seguir padrões já estabelecidos
        3. **Segurança**: Evitar quebrar o que já funciona
        4. **Rastreabilidade**: Manter histórico claro
        5. **Reversibilidade**: Possibilidade de rollback
        
        Seja PRÁTICO, ESPECÍFICO e forneça EXEMPLOS CONCRETOS.
        """
    
    def read_file(self, file_path: Path) -> str:
        """Lê arquivo."""
        if not file_path.exists():
            return ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def analyze_current_structure(self) -> str:
        """Analisa a estrutura atual de migrations."""
        print("🔍 Analisando estrutura atual de migrations...")
        
        # Listar arquivos de migration
        sql_migrations = list(self.migrations_path.glob("*.sql"))
        py_migrations = list(self.migrations_path.glob("*.py"))
        
        # Ler alguns exemplos
        example_sql = ""
        if sql_migrations:
            example_sql = self.read_file(sql_migrations[0])[:2000]
        
        # Ler README se existir
        readme = self.read_file(self.migrations_path / "README")
        readme_sequences = self.read_file(self.migrations_path / "README_SEQUENCES_FIX.md")
        
        # Verificar se há env.py (Alembic)
        has_alembic = (self.migrations_path / "env.py").exists()
        has_alembic_ini = (self.migrations_path / "alembic.ini").exists()
        
        # Verificar versions/
        versions_path = self.migrations_path / "versions"
        alembic_versions = []
        if versions_path.exists():
            alembic_versions = list(versions_path.glob("*.py"))
        
        response = self.llm.invoke([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""
Analise a estrutura atual de migrations do projeto APP32 e forneça recomendações.

**Estrutura Encontrada:**

1. **Arquivos SQL diretos:** {len(sql_migrations)} arquivos
   - Exemplos: {[f.name for f in sql_migrations[:5]]}

2. **Scripts Python de migration:** {len(py_migrations)} arquivos
   - Exemplos: {[f.name for f in py_migrations[:3]]}

3. **Alembic configurado:** {'SIM' if has_alembic else 'NÃO'}
   - env.py: {'Existe' if has_alembic else 'Não existe'}
   - alembic.ini: {'Existe' if has_alembic_ini else 'Não existe'}
   - versions/: {len(alembic_versions)} arquivos Python

4. **README:**
```
{readme}
```

5. **README_SEQUENCES_FIX.md:**
```
{readme_sequences[:1000]}
```

6. **Exemplo de Migration SQL:**
```sql
{example_sql}
```

**Contexto:**
Precisamos adicionar novas tabelas para o módulo PEV (Planejamento Estratégico).
Já temos 3 migrations prontas em formato Alembic/Python, mas descobrimos que o
projeto pode estar usando SQL direto.

**Forneça análise seguindo este formato:**

# Análise de Governança de Banco de Dados - APP32

## 1. Estrutura Atual Identificada

### 1.1 Padrão de Migrations
[Descreva o padrão atual: SQL puro, Alembic, híbrido, etc.]

### 1.2 Convenções de Nomenclatura
[Padrão de nomes dos arquivos]

### 1.3 Processo de Execução
[Como as migrations são executadas atualmente]

### 1.4 Versionamento
[Como é controlada a versão do banco]

## 2. Avaliação da Estrutura

### 2.1 Pontos Fortes
1. [Ponto forte 1]
2. [Ponto forte 2]

### 2.2 Pontos Fracos
1. [Ponto fraco 1]
2. [Ponto fraco 2]

### 2.3 Riscos Identificados
1. [Risco 1]
2. [Risco 2]

## 3. Recomendações para Módulo PEV

### 3.1 Abordagem Recomendada
[SQL puro, Alembic, ou híbrido?]

**Justificativa:**
[Por que essa abordagem]

### 3.2 Estrutura de Arquivos Proposta

```
migrations/
├── YYYYMMDD_description.sql  (se SQL puro)
ou
├── versions/
│   └── XXXX_description.py   (se Alembic)
```

### 3.3 Exemplo de Migration PEV

**Opção A: SQL Puro**
```sql
-- Arquivo: 20260215_create_pev_base_tables.sql
-- Descrição: Cria tabelas base do módulo PEV

-- Tabela plans
CREATE TABLE IF NOT EXISTS plans (
    id SERIAL PRIMARY KEY,
    ...
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_plans_company ON plans(company_id);
```

**Opção B: Alembic**
```python
# Arquivo: versions/001_create_pev_base.py
def upgrade():
    op.create_table('plans', ...)

def downgrade():
    op.drop_table('plans')
```

### 3.4 Script de Execução

```python
# Como executar as migrations PEV
```

## 4. Plano de Implementação

### 4.1 Passo a Passo

1. [Passo 1]
2. [Passo 2]
3. [Passo 3]

### 4.2 Validação

```bash
# Comandos para validar
```

### 4.3 Rollback (se necessário)

```sql
-- Como reverter
```

## 5. Governança Futura

### 5.1 Padronização Recomendada
[Recomendações para unificar abordagem]

### 5.2 Documentação
[O que documentar em cada migration]

### 5.3 Processo de Revisão
[Como revisar migrations antes de aplicar]

## 6. Decisão Final

**Recomendação:** [SQL Puro | Alembic | Híbrido]

**Próximos Passos Imediatos:**
1. [Ação 1]
2. [Ação 2]
3. [Ação 3]

**Arquivos a Criar:**
- [ ] [Arquivo 1]
- [ ] [Arquivo 2]

**Comandos a Executar:**
```bash
# Comandos específicos
```
""")
        ])
        
        return response.content
    
    def analyze_pev_migrations(self) -> str:
        """Analisa as migrations PEV já criadas e adapta para o padrão do projeto."""
        print("📋 Analisando migrations PEV criadas...")
        
        # Ler as migrations Alembic criadas
        pev_migrations_path = ROOT_DIR / "migrations" / "versions"
        pev_001 = self.read_file(pev_migrations_path / "001_create_pev_base_tables.py")
        pev_002 = self.read_file(pev_migrations_path / "002_create_pev_growth_tables.py")
        pev_003 = self.read_file(pev_migrations_path / "003_create_pev_implantation_tables.py")
        
        response = self.llm.invoke([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""
Temos 3 migrations prontas em formato Alembic/Python para o módulo PEV.

**Migration 001 (Base):**
```python
{pev_001[:2000]}
```

**Migration 002 (Growth):**
```python
{pev_002[:2000]}
```

**Migration 003 (Implantation):**
```python
{pev_003[:2000]}
```

**Tarefa:**
Converta essas migrations para o formato adequado ao projeto APP32.

Se o projeto usa **SQL puro**, forneça:
1. Arquivo SQL completo para cada migration
2. Script Python para executar
3. Validações necessárias

Se o projeto usa **Alembic**, forneça:
1. Ajustes necessários nas migrations
2. Comandos para executar
3. Validações

Forneça resposta seguindo este formato:

# Conversão de Migrations PEV para Padrão APP32

## 1. Formato Recomendado
[SQL Puro ou Alembic]

## 2. Arquivos a Criar

### Arquivo 1: [Nome do arquivo]
```[sql ou python]
[Conteúdo completo]
```

### Arquivo 2: [Nome do arquivo]
```[sql ou python]
[Conteúdo completo]
```

### Arquivo 3: [Nome do arquivo]
```[sql ou python]
[Conteúdo completo]
```

## 3. Script de Execução

```python
# Script para executar as migrations
```

## 4. Validação

```sql
-- Queries para validar tabelas criadas
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'pev_%' OR table_name IN ('plans', 'participants', ...);
```

## 5. Rollback

```sql
-- Script de rollback se necessário
```
""")
        ])
        
        return response.content
    
    def generate_implementation_guide(self, analysis: str, conversion: str) -> str:
        """Gera guia de implementação consolidado."""
        print("📖 Gerando guia de implementação...")
        
        response = self.llm.invoke([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""
Com base na análise de governança e conversão de migrations, crie um guia
PRÁTICO e EXECUTÁVEL para implementar as tabelas PEV no APP32.

**Análise de Governança:**
{analysis[:3000]}

**Conversão de Migrations:**
{conversion[:3000]}

Forneça guia seguindo este formato:

# Guia de Implementação - Migrations PEV no APP32

## ✅ Checklist Pré-Implementação

- [ ] Backup do banco de dados criado
- [ ] Ambiente de testes validado
- [ ] Permissões de banco verificadas
- [ ] Documentação revisada

## 📋 Passo a Passo de Implementação

### Passo 1: Preparação
```bash
# Comandos de preparação
```

### Passo 2: Criação de Arquivos
[Lista de arquivos a criar com conteúdo]

### Passo 3: Execução de Migrations
```bash
# Comandos para executar
```

### Passo 4: Validação
```sql
-- Queries de validação
```

### Passo 5: Testes
```python
# Testes a executar
```

## 🔧 Troubleshooting

### Problema 1: [Possível erro]
**Solução:** [Como resolver]

### Problema 2: [Possível erro]
**Solução:** [Como resolver]

## 📊 Validação Final

```sql
-- Queries para confirmar sucesso
```

## 🎯 Próximos Passos

1. [Próximo passo 1]
2. [Próximo passo 2]
""")
        ])
        
        return response.content
    
    def run_full_analysis(self):
        """Executa análise completa."""
        print("🚀 Iniciando análise de governança de banco de dados\n")
        print("="*60)
        
        # 1. Analisar estrutura atual
        print("\n📊 FASE 1: Análise da Estrutura Atual")
        print("="*60)
        
        try:
            analysis = self.analyze_current_structure()
            
            output_file = self.output_path / "governance_analysis.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(analysis)
            
            print(f"   ✅ Análise salva: {output_file.name}\n")
        except Exception as e:
            print(f"   ❌ Erro na análise: {e}\n")
            return
        
        # 2. Analisar e converter migrations PEV
        print("\n📋 FASE 2: Conversão de Migrations PEV")
        print("="*60)
        
        try:
            conversion = self.analyze_pev_migrations()
            
            output_file = self.output_path / "pev_migrations_conversion.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(conversion)
            
            print(f"   ✅ Conversão salva: {output_file.name}\n")
        except Exception as e:
            print(f"   ❌ Erro na conversão: {e}\n")
            return
        
        # 3. Gerar guia de implementação
        print("\n📖 FASE 3: Guia de Implementação")
        print("="*60)
        
        try:
            guide = self.generate_implementation_guide(analysis, conversion)
            
            output_file = self.output_path / "implementation_guide.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(guide)
            
            print(f"   ✅ Guia salvo: {output_file.name}\n")
        except Exception as e:
            print(f"   ❌ Erro ao gerar guia: {e}\n")
            return
        
        # Resumo final
        print("\n" + "="*60)
        print("✅ ANÁLISE DE GOVERNANÇA COMPLETA!")
        print("="*60)
        print(f"\n📁 Documentos gerados em: {self.output_path}")
        print(f"\nArquivos criados:")
        for file in self.output_path.glob("*.md"):
            print(f"  - {file.name}")
        
        print("\n🎯 LEIA OS DOCUMENTOS GERADOS:")
        print(f"   1. governance_analysis.md - Análise da estrutura atual")
        print(f"   2. pev_migrations_conversion.md - Migrations convertidas")
        print(f"   3. implementation_guide.md - Guia passo a passo")
        print("\n" + "="*60)


def main():
    """Função principal."""
    analyzer = DatabaseGovernanceAnalyzer()
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
