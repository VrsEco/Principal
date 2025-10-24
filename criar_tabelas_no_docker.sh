#!/bin/bash

echo "============================================"
echo "  CRIANDO TABELAS NO POSTGRESQL DO DOCKER"
echo "============================================"
echo ""

# Executar SQL dentro do container do PostgreSQL
docker exec -i gestaoversos_db_prod psql -U postgres -d bd_app_versus << 'EOF'

-- Remover tabelas antigas se existirem
DROP TABLE IF EXISTS plan_alignment_agenda CASCADE;
DROP TABLE IF EXISTS plan_alignment_members CASCADE;
DROP TABLE IF EXISTS plan_alignment_principles CASCADE;
DROP TABLE IF EXISTS plan_alignment_project CASCADE;
DROP TABLE IF EXISTS plan_alignment_overview CASCADE;

-- Criar tabela plan_alignment_members
CREATE TABLE plan_alignment_members (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans (id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255),
    motivation TEXT,
    commitment TEXT,
    risk TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela plan_alignment_overview
CREATE TABLE plan_alignment_overview (
    plan_id INTEGER PRIMARY KEY REFERENCES plans (id) ON DELETE CASCADE,
    shared_vision TEXT,
    financial_goals TEXT,
    decision_criteria JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela plan_alignment_agenda
CREATE TABLE plan_alignment_agenda (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans (id) ON DELETE CASCADE,
    action_title TEXT,
    owner_name TEXT,
    schedule_info TEXT,
    execution_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela plan_alignment_principles
CREATE TABLE plan_alignment_principles (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans (id) ON DELETE CASCADE,
    principle TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela plan_alignment_project
CREATE TABLE plan_alignment_project (
    plan_id INTEGER PRIMARY KEY REFERENCES plans (id) ON DELETE CASCADE,
    project_name TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar índices
CREATE INDEX idx_alignment_members_plan_id ON plan_alignment_members(plan_id);
CREATE INDEX idx_alignment_agenda_plan_id ON plan_alignment_agenda(plan_id);
CREATE INDEX idx_alignment_principles_plan_id ON plan_alignment_principles(plan_id);

-- Verificar criação
\dt plan_alignment*

EOF

echo ""
echo "============================================"
echo "✅ TABELAS CRIADAS NO POSTGRESQL DO DOCKER!"
echo "============================================"
echo ""
echo "Agora reinicie o container do Flask:"
echo "  docker-compose restart app"
echo ""
echo "E teste novamente!"
echo ""

