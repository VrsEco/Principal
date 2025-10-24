#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar migração do My Work
Adiciona campos e tabelas necessárias
"""

import os
import sys
from database.postgres_helper import connect as pg_connect

def apply_migration():
    """Aplica migração do My Work no PostgreSQL"""
    
    print("=" * 80)
    print("MIGRAÇÃO: MY WORK - Sistema de Gestão de Atividades")
    print("=" * 80)
    print()
    
    try:
        conn = pg_connect()
        cursor = conn.cursor()
        
        print("✅ Conectado ao PostgreSQL")
        print()
        
        # ==================================================
        # 1. Adicionar campos em company_projects
        # ==================================================
        print("📋 1. Adicionando campos em company_projects...")
        
        cursor.execute("""
            ALTER TABLE company_projects 
            ADD COLUMN IF NOT EXISTS estimated_hours DECIMAL(5,2) DEFAULT 0
        """)
        print("   ✓ estimated_hours")
        
        cursor.execute("""
            ALTER TABLE company_projects 
            ADD COLUMN IF NOT EXISTS worked_hours DECIMAL(5,2) DEFAULT 0
        """)
        print("   ✓ worked_hours")
        
        cursor.execute("""
            ALTER TABLE company_projects 
            ADD COLUMN IF NOT EXISTS executor_id INTEGER
        """)
        print("   ✓ executor_id")
        
        conn.commit()
        print()
        
        # ==================================================
        # 2. Criar tabela teams
        # ==================================================
        print("📋 2. Criando tabela teams...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id SERIAL PRIMARY KEY,
                company_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                leader_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (leader_id) REFERENCES employees(id) ON DELETE SET NULL
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_teams_company ON teams(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_teams_leader ON teams(leader_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_teams_active ON teams(is_active)")
        
        conn.commit()
        print("   ✓ Tabela teams criada")
        print()
        
        # ==================================================
        # 3. Criar tabela team_members
        # ==================================================
        print("📋 3. Criando tabela team_members...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id SERIAL PRIMARY KEY,
                team_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                role VARCHAR(50) DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                left_at TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                UNIQUE(team_id, employee_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_employee ON team_members(employee_id)")
        
        conn.commit()
        print("   ✓ Tabela team_members criada")
        print()
        
        # ==================================================
        # 4. Criar tabela activity_work_logs
        # ==================================================
        print("📋 4. Criando tabela activity_work_logs...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_work_logs (
                id SERIAL PRIMARY KEY,
                activity_type VARCHAR(20) NOT NULL,
                activity_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                employee_name VARCHAR(200),
                work_date DATE NOT NULL,
                hours_worked DECIMAL(5,2) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                CHECK (activity_type IN ('project', 'process')),
                CHECK (hours_worked > 0 AND hours_worked <= 24)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_logs_activity ON activity_work_logs(activity_type, activity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_logs_employee ON activity_work_logs(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_work_logs_date ON activity_work_logs(work_date)")
        
        conn.commit()
        print("   ✓ Tabela activity_work_logs criada")
        print()
        
        # ==================================================
        # 5. Criar tabela activity_comments
        # ==================================================
        print("📋 5. Criando tabela activity_comments...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_comments (
                id SERIAL PRIMARY KEY,
                activity_type VARCHAR(20) NOT NULL,
                activity_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                employee_name VARCHAR(200),
                comment_type VARCHAR(20),
                comment_text TEXT NOT NULL,
                is_private BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
                CHECK (activity_type IN ('project', 'process'))
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_activity ON activity_comments(activity_type, activity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_employee ON activity_comments(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_created ON activity_comments(created_at)")
        
        conn.commit()
        print("   ✓ Tabela activity_comments criada")
        print()
        
        # ==================================================
        # 6. Criar função e trigger para worked_hours
        # ==================================================
        print("📋 6. Criando trigger para atualização automática de worked_hours...")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_activity_worked_hours()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.activity_type = 'project' THEN
                    UPDATE company_projects 
                    SET worked_hours = (
                        SELECT COALESCE(SUM(hours_worked), 0) 
                        FROM activity_work_logs 
                        WHERE activity_type = 'project' AND activity_id = NEW.activity_id
                    )
                    WHERE id = NEW.activity_id;
                
                ELSIF NEW.activity_type = 'process' THEN
                    UPDATE process_instances 
                    SET actual_hours = (
                        SELECT COALESCE(SUM(hours_worked), 0) 
                        FROM activity_work_logs 
                        WHERE activity_type = 'process' AND activity_id = NEW.activity_id
                    )
                    WHERE id = NEW.activity_id;
                END IF;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        cursor.execute("DROP TRIGGER IF EXISTS trigger_update_worked_hours ON activity_work_logs")
        cursor.execute("""
            CREATE TRIGGER trigger_update_worked_hours
            AFTER INSERT ON activity_work_logs
            FOR EACH ROW
            EXECUTE FUNCTION update_activity_worked_hours()
        """)
        
        conn.commit()
        print("   ✓ Trigger criado")
        print()
        
        # ==================================================
        # 7. Criar índices adicionais
        # ==================================================
        print("📋 7. Criando índices para performance...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_company_projects_responsible ON company_projects(responsible_id)",
            "CREATE INDEX IF NOT EXISTS idx_company_projects_executor ON company_projects(executor_id)",
            "CREATE INDEX IF NOT EXISTS idx_company_projects_status ON company_projects(status)",
            "CREATE INDEX IF NOT EXISTS idx_company_projects_priority ON company_projects(priority)",
            "CREATE INDEX IF NOT EXISTS idx_company_projects_end_date ON company_projects(end_date)"
        ]
        
        for idx in indexes:
            cursor.execute(idx)
        
        conn.commit()
        print("   ✓ Índices criados")
        print()
        
        # ==================================================
        # Verificação final
        # ==================================================
        print("=" * 80)
        print("VERIFICAÇÃO FINAL")
        print("=" * 80)
        print()
        
        # Verificar tabelas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('teams', 'team_members', 'activity_work_logs', 'activity_comments')
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print("📋 Tabelas criadas:")
        for table in tables:
            print(f"   ✓ {table[0]}")
        print()
        
        # Verificar campos
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'company_projects' 
            AND column_name IN ('estimated_hours', 'worked_hours', 'executor_id')
        """)
        columns = cursor.fetchall()
        
        print("📋 Campos adicionados em company_projects:")
        for col in columns:
            print(f"   ✓ {col[0]}")
        print()
        
        cursor.close()
        conn.close()
        
        print("=" * 80)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 80)
        print()
        print("Próximos passos:")
        print("1. Criar models Python (models/team.py, etc)")
        print("2. Criar services (services/my_work_service.py)")
        print("3. Criar rotas (modules/my_work/)")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO na migração: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)

