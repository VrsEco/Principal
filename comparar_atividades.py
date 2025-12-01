"""
Script de Comparação: Busca Direta no Banco vs Lógica do Código
Compara os resultados para identificar possíveis inconsistências
"""
import sys
import os
import json
import argparse
import contextlib
import io

sys.path.append(os.getcwd())

from app_pev import app
from models import db
from models.user import User
from models.employee import Employee
from models.company import Company
from services.my_work_service import (
    get_employee_from_user,
    get_user_activities,
    get_user_employees,
)


def _row_to_dict(row):
    """Converte um resultado do SQLAlchemy Row para dict padrão."""
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    try:
        return dict(row)
    except Exception:
        return {}


def _parse_collaborators(raw_value):
    """Converte o campo assigned_collaborators em lista de dicts."""
    if not raw_value:
        return []
    if isinstance(raw_value, list):
        return raw_value
    if isinstance(raw_value, str):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            return []
    return []


def _table_exists(table_name: str) -> bool:
    """Verifica se a tabela existe no schema público."""
    result = db.session.execute(
        db.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = :table_name
            )
            """
        ),
        {"table_name": table_name},
    )
    return bool(result.scalar())


def _build_in_clause(values, prefix):
    """Gera placeholders nomeados para cláusulas IN."""
    values = list(values)
    if not values:
        return "", {}
    placeholders = ",".join(f":{prefix}{i}" for i in range(len(values)))
    params = {f"{prefix}{i}": value for i, value in enumerate(values)}
    return placeholders, params


def coletar_resultados(email: str, silent: bool = False):
    """Executa as duas consultas e retorna dados mais logs opcionais."""
    buffer = io.StringIO()
    context = (
        contextlib.redirect_stdout(buffer)
        if silent
        else contextlib.nullcontext()
    )

    with context:
        resultado_banco = buscar_direto_banco(email)
        resultado_codigo = buscar_via_codigo(email)

    logs = buffer.getvalue() if silent else ""
    return resultado_banco, resultado_codigo, logs

def buscar_direto_banco(email="mff2000@gmail.com"):
    """
    Busca atividades diretamente no banco de dados usando SQL
    """
    print("\n" + "="*80)
    print("🔍 MÉTODO 1: BUSCA DIRETA NO BANCO DE DADOS (SQL)")
    print("="*80)
    
    with app.app_context():
        # 1. Buscar usuário
        print(f"\n1️⃣  Buscando usuário: {email}")
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"   ❌ Usuário não encontrado")
            return None
        
        print(f"   ✅ Usuário encontrado: {user.name} (ID: {user.id})")
        
        # 2. Buscar colaboradores vinculados
        print(f"\n2️⃣  Buscando colaboradores vinculados...")
        
        # Busca por user_id
        result = db.session.execute(
            db.text("""
                SELECT e.id, e.name, e.email, e.company_id, c.name as company_name
                FROM employees e
                LEFT JOIN companies c ON c.id = e.company_id
                WHERE e.user_id = :user_id
                ORDER BY e.id
            """),
            {"user_id": user.id}
        )
        
        employees_by_user_id = result.fetchall()
        print(f"   📊 Por user_id: {len(employees_by_user_id)} colaborador(es)")
        
        # Busca por email (fallback)
        result = db.session.execute(
            db.text("""
                SELECT e.id, e.name, e.email, e.company_id, c.name as company_name
                FROM employees e
                LEFT JOIN companies c ON c.id = e.company_id
                WHERE LOWER(TRIM(e.email)) = LOWER(TRIM(:email))
                ORDER BY e.id
            """),
            {"email": email}
        )
        
        employees_by_email = result.fetchall()
        print(f"   📊 Por email: {len(employees_by_email)} colaborador(es)")
        
        # Consolidar IDs únicos
        employee_ids = set()
        employee_details = {}
        
        for emp in employees_by_user_id + employees_by_email:
            emp_id, emp_name, emp_email, company_id, company_name = emp
            employee_ids.add(emp_id)
            employee_details[emp_id] = {
                'id': emp_id,
                'name': emp_name,
                'email': emp_email,
                'company_id': company_id,
                'company_name': company_name
            }
        
        print(f"\n   ✅ Total de colaboradores únicos: {len(employee_ids)}")
        for emp_id in sorted(employee_ids):
            emp = employee_details[emp_id]
            print(f"      - ID {emp['id']}: {emp['name']} ({emp['company_name']})")
        
        if not employee_ids:
            print(f"   ⚠️  Nenhum colaborador encontrado!")
            return None
        
        # 3. Buscar atividades de PROJETOS
        print(f"\n3️⃣  Buscando atividades de PROJETOS...")
        
        employee_ids_list = sorted(employee_ids)
        project_count = 0
        project_samples = []
        
        if not employee_ids_list:
            print("   ⚠️  Nenhum colaborador para buscar projetos")
        elif not _table_exists("company_projects"):
            print("   ⚠️  Tabela 'company_projects' não existe")
        else:
            placeholders, params = _build_in_clause(employee_ids_list, "emp")
            project_count = db.session.execute(
                db.text(f"""
                    SELECT COUNT(*)
                    FROM company_projects cp
                    WHERE cp.responsible_id IN ({placeholders})
                       OR cp.executor_id IN ({placeholders})
                """),
                params,
            ).scalar() or 0
            
            if project_count:
                result = db.session.execute(
                    db.text(f"""
                        SELECT 
                            cp.id,
                            cp.title,
                            cp.description,
                            cp.end_date AS prazo,
                            cp.status,
                            c.name AS empresa,
                            cp.responsible_id,
                            cp.executor_id
                        FROM company_projects cp
                        LEFT JOIN companies c ON c.id = cp.company_id
                        WHERE cp.responsible_id IN ({placeholders})
                           OR cp.executor_id IN ({placeholders})
                        ORDER BY cp.end_date DESC, cp.updated_at DESC
                        LIMIT 20
                    """),
                    params,
                )
                project_samples = result.fetchall()
            
            print(f"   ✅ Encontradas {project_count} atividade(s) de projeto")
            
            for i, act in enumerate(project_samples[:5], 1):
                (
                    act_id,
                    titulo,
                    descricao,
                    prazo,
                    status,
                    empresa,
                    resp_id,
                    executor_id,
                ) = act
                print(f"\n      {i}. Projeto #{act_id}")
                print(f"         Título: {titulo}")
                if descricao:
                    preview = descricao[:60] + ("..." if len(descricao) > 60 else "")
                    print(f"         Descrição: {preview}")
                print(f"         Empresa: {empresa}")
                print(f"         Prazo: {prazo}")
                print(f"         Status: {status}")
                print(f"         Responsável ID: {resp_id}, Executor ID: {executor_id}")
            
            if project_count > len(project_samples):
                restante = project_count - len(project_samples)
                print(f"\n      ... e mais {restante} atividade(s) não listadas")
        
        # 4. Buscar instâncias de PROCESSOS
        print(f"\n4️⃣  Buscando instâncias de PROCESSOS...")
        
        process_entries = []
        process_count = 0
        
        if not employee_ids_list:
            print("   ⚠️  Nenhum colaborador para buscar processos")
        elif not _table_exists("process_instances"):
            print("   ⚠️  Tabela 'process_instances' não existe")
        else:
            company_ids = sorted(
                {
                    details["company_id"]
                    for details in employee_details.values()
                    if details.get("company_id") is not None
                }
            )
            
            if not company_ids:
                print("   ⚠️  Colaboradores sem empresa vinculada")
            else:
                comp_placeholders, comp_params = _build_in_clause(company_ids, "comp")
                
                result = db.session.execute(
                    db.text(f"""
                        SELECT 
                            pi.id,
                            pi.title,
                            pi.description,
                            pi.status,
                            pi.due_date AS prazo,
                            c.name AS empresa,
                            pi.assigned_collaborators,
                            pi.company_id,
                            pi.created_at
                        FROM process_instances pi
                        LEFT JOIN companies c ON c.id = pi.company_id
                        WHERE pi.company_id IN ({comp_placeholders})
                        ORDER BY pi.created_at DESC
                    """),
                    comp_params,
                )
                
                target_ids = set(employee_ids_list)
                for row in result.fetchall():
                    data = _row_to_dict(row)
                    collaborators = _parse_collaborators(data.get("assigned_collaborators"))
                    collaborator_ids = {
                        collab.get("id")
                        for collab in collaborators
                        if collab.get("id") is not None
                    }
                    if collaborator_ids & target_ids:
                        data["collaborators"] = collaborators
                        process_entries.append(data)
                
                process_count = len(process_entries)
                print(f"   ✅ Encontradas {process_count} instância(s) de processo")
                
                for i, inst in enumerate(process_entries[:5], 1):
                    collab_labels = [
                        f"{collab.get('id')} ({collab.get('name', 'sem nome')})"
                        for collab in inst.get("collaborators", [])
                        if collab.get("id") in target_ids
                    ]
                    print(f"\n      {i}. Instância #{inst.get('id')}")
                    print(f"         Título: {inst.get('title')}")
                    print(f"         Empresa: {inst.get('empresa')}")
                    print(f"         Status: {inst.get('status')}")
                    print(f"         Prazo: {inst.get('prazo')}")
                    collab_output = ", ".join(collab_labels) if collab_labels else "N/A"
                    print(f"         Colaboradores alvo: {collab_output}")
                
                if process_count > 5:
                    print(f"\n      ... e mais {process_count - 5} instância(s) não listadas")
        
        return {
            'user_id': user.id,
            'employee_ids': employee_ids,
            'employee_details': employee_details,
            'project_activities': project_count,
            'process_instances': process_count,
            'total': project_count + process_count
        }


def buscar_via_codigo(email="mff2000@gmail.com"):
    """
    Busca atividades usando a lógica do código (my_work_service)
    """
    print("\n" + "="*80)
    print("🔍 MÉTODO 2: BUSCA VIA LÓGICA DO CÓDIGO (my_work_service)")
    print("="*80)
    
    with app.app_context():
        # 1. Buscar usuário
        print(f"\n1️⃣  Buscando usuário: {email}")
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"   ❌ Usuário não encontrado")
            return None
        
        print(f"   ✅ Usuário encontrado: {user.name} (ID: {user.id})")
        
        # 2. Usar get_employee_from_user (lógica do código)
        print(f"\n2️⃣  Usando get_employee_from_user()...")
        employee_id = get_employee_from_user(user.id)
        
        if employee_id:
            print(f"   ✅ Employee ID retornado: {employee_id}")
            emp = db.session.get(Employee, employee_id)
            if emp:
                company = db.session.get(Company, emp.company_id) if emp.company_id else None
                print(f"      Nome: {emp.name}")
                print(f"      Email: {emp.email}")
                print(f"      Empresa: {company.name if company else 'N/A'}")
        else:
            print(f"   ❌ Nenhum employee_id retornado")
        
        # 3. Usar get_user_employees (lógica do código)
        print(f"\n3️⃣  Usando get_user_employees()...")
        companies = get_user_employees(user.id)
        
        print(f"   ✅ Retornadas {len(companies)} empresa(s)/colaborador(es):")
        employee_ids_from_service = []
        for comp in companies:
            print(f"      - Employee ID {comp['employee_id']}: {comp['employee_name']} ({comp['company_name']})")
            employee_ids_from_service.append(comp['employee_id'])
        
        # 4. Usar get_user_activities (lógica do código)
        print(f"\n4️⃣  Usando get_user_activities()...")
        
        if employee_id:
            try:
                # Testar com escopo 'me'
                activities_me = get_user_activities(
                    employee_id,
                    scope='me',
                    filters={'filter': 'all'},
                    company_ids=[],
                    employee_ids=employee_ids_from_service
                )
                print(f"   ✅ Escopo 'me': {len(activities_me)} atividade(s)")
                
                # Mostrar primeiras 5
                for i, act in enumerate(activities_me[:5], 1):
                    print(f"\n      {i}. {act.get('type', 'N/A')} - {act.get('description', 'N/A')[:60]}")
                    print(f"         Empresa: {act.get('company_name', 'N/A')}")
                    print(f"         Prazo: {act.get('deadline', 'N/A')}")
                    print(f"         Status: {act.get('status', 'N/A')}")
                
                if len(activities_me) > 5:
                    print(f"\n      ... e mais {len(activities_me) - 5} atividade(s)")
                
                return {
                    'user_id': user.id,
                    'employee_id': employee_id,
                    'employee_ids_from_service': employee_ids_from_service,
                    'activities_count': len(activities_me),
                    'activities': activities_me
                }
                
            except Exception as e:
                print(f"   ❌ Erro ao buscar atividades: {e}")
                import traceback
                traceback.print_exc()
                return None
        else:
            print(f"   ⚠️  Não foi possível buscar atividades (employee_id é None)")
            return None


def comparar_resultados(email: str = "mff2000@gmail.com"):
    """
    Compara os resultados dos dois métodos
    """
    print("\n" + "="*80)
    print("📊 COMPARAÇÃO DE RESULTADOS")
    print("="*80)
    
    # Executar ambas as buscas
    resultado_banco = buscar_direto_banco(email)
    resultado_codigo = buscar_via_codigo(email)
    
    # Comparação
    print("\n" + "="*80)
    print("🔬 ANÁLISE COMPARATIVA")
    print("="*80)
    
    if resultado_banco and resultado_codigo:
        print(f"\n✅ Ambos os métodos retornaram resultados\n")
        
        # Comparar employee_ids
        print("📋 COLABORADORES:")
        emp_ids_banco = resultado_banco['employee_ids']
        emp_ids_codigo = set(resultado_codigo['employee_ids_from_service'])
        
        print(f"   Banco (SQL direto): {len(emp_ids_banco)} colaborador(es)")
        print(f"   Código (service):   {len(emp_ids_codigo)} colaborador(es)")
        
        if emp_ids_banco == emp_ids_codigo:
            print(f"   ✅ MATCH! Os mesmos colaboradores foram encontrados")
        else:
            print(f"   ⚠️  DIFERENÇA detectada!")
            apenas_banco = emp_ids_banco - emp_ids_codigo
            apenas_codigo = emp_ids_codigo - emp_ids_banco
            
            if apenas_banco:
                print(f"      Apenas no banco: {apenas_banco}")
            if apenas_codigo:
                print(f"      Apenas no código: {apenas_codigo}")
        
        # Comparar atividades
        print(f"\n📋 ATIVIDADES:")
        print(f"   Banco (SQL direto):")
        print(f"      - Projetos: {resultado_banco['project_activities']}")
        print(f"      - Processos: {resultado_banco['process_instances']}")
        print(f"      - Total: {resultado_banco['total']}")
        
        print(f"\n   Código (service):")
        print(f"      - Total: {resultado_codigo['activities_count']}")
        
        diff = abs(resultado_banco['total'] - resultado_codigo['activities_count'])
        if diff == 0:
            print(f"\n   ✅ MATCH! Mesma quantidade de atividades")
        else:
            print(f"\n   ⚠️  DIFERENÇA: {diff} atividade(s) de diferença")
            
            if resultado_banco['total'] > resultado_codigo['activities_count']:
                print(f"      O banco tem MAIS atividades que o código retorna")
                print(f"      Possível causa: Filtros ou lógica de negócio no service")
            else:
                print(f"      O código retorna MAIS atividades que o banco")
                print(f"      Possível causa: Agregação de múltiplas fontes")
    
    elif resultado_banco and not resultado_codigo:
        print(f"\n⚠️  Apenas o método do BANCO retornou resultados")
        print(f"   O código (service) não conseguiu buscar atividades")
        print(f"   Possível causa: Problema na lógica do my_work_service")
    
    elif not resultado_banco and resultado_codigo:
        print(f"\n⚠️  Apenas o método do CÓDIGO retornou resultados")
        print(f"   O banco direto não encontrou atividades")
        print(f"   Possível causa: Tabelas com nomes diferentes ou estrutura diferente")
    
    else:
        print(f"\n❌ Nenhum dos métodos retornou resultados")
        print(f"   Não há atividades cadastradas para este usuário")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compara atividades de um usuário no banco e via serviços"
    )
    parser.add_argument(
        "--email",
        default="mff2000@gmail.com",
        help="Email do usuário alvo (default: %(default)s)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Formato de saída (text/json)",
    )
    args = parser.parse_args()

    if args.format == "json":
        banco, codigo, logs = coletar_resultados(args.email, silent=True)
        if banco and isinstance(banco.get("employee_ids"), set):
            banco["employee_ids"] = sorted(banco["employee_ids"])
        resultado = {
            "email": args.email,
            "database": banco,
            "service": codigo,
        }
        if logs.strip():
            resultado["logs"] = logs.strip().splitlines()
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        print("\n🚀 Comparação: Banco vs Código - Atividades do Usuário")
        try:
            comparar_resultados(email=args.email)
        except Exception as e:
            print(f"\n❌ Erro durante a comparação: {e}")
            import traceback

            traceback.print_exc()
        print("\n✅ Comparação concluída!")
