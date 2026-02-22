import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import app
from models import db, Plan, PlanImplantationData, PlanSectionStatus

def seed_implantation():
    with app.app_context():
        # Find or create a test implantation plan
        plan = Plan.query.get(10)
        if not plan:
            print("No implantation plan found. Creating one...")
            from models import Company
            company = Company.query.first()
            if not company: return
            plan = Plan(
                company_id=company.id,
                title="Novo Negócio: Versus Coffee & Tech",
                mode="implantation",
                status="draft"
            )
            db.session.add(plan)
        else:
            plan.title = "Novo Negócio: Versus Coffee & Tech (Migrated Structure)"
        
        db.session.flush()
        
        # Init sections
        for key in ['dashboard', 'alignment', 'model', 'execution', 'finance', 'final_report']:
            status = PlanSectionStatus.query.filter_by(plan_id=plan.id, section_key=key).first()
            if not status:
                db.session.add(PlanSectionStatus(plan_id=plan.id, section_key=key, status='pending'))

        # Structured Data following Pydantic Schemas
        data_map = {
            "alignment": {
                "shared_vision": "Ser o hub de inovação e café mais reconhecido do país em 3 anos, unindo tecnologia e hospitalidade.",
                "financial_goals": "Faturamento mensal de R$ 100k com margem líquida de 20%.",
                "decision_criteria": ["Impacto na marca", "Viabilidade de margem", "Escalabilidade"],
                "partners": [
                    {"name": "Arthur Dent", "role": "CEO", "motivation": "Inovação", "commitment": "Integral", "risk": "Baixo"},
                    {"name": "Tricia McMillan", "role": "CMO", "motivation": "Expansão", "commitment": "Parcial", "risk": "Médio"}
                ],
                "agenda": [
                    {"what": "Contratação de Barista Senior", "who": "Arthur", "when": "Semana 1", "how": "LinkedIn/Entrevista"},
                    {"what": "Setup do PDV", "who": "Tricia", "when": "Semana 2", "how": "Hardware + Software"}
                ]
            },
            "model": {
                "segments": [
                    {
                        "name": "Profissionais de Tecnologia",
                        "description": "Segmento focado em devs e nômades digitais.",
                        "audiences": ["Desenvolvedores", "Designers", "Nômades Digitais"],
                        "problems": ["Falta de foco em casa", "Internet instável em cafés comuns", "Barulho excessivo"],
                        "solution": "Ambiente produtivo com internet de 1Gbps, cabines acústicas e café especial ilimitado.",
                        "key_partners": ["Provedores de Internet", "Torrefações locais", "Comunidades Tech"],
                        "positioning": "O hub definitivo para quem leva produtividade a sério.",
                        "central_promise": "Triplique sua produtividade com o melhor café da cidade.",
                        "next_steps": ["Trial gratuito para influencers tech", "Meetup de Javascript"],
                        "differential_matrix": [
                            {"criterion": "Velocidade Internet", "our_company": "1Gbps / Fibra Dupla", "competitor_a": "100Mbps", "competitor_b": "4G/5G instável", "observation": "Único com redundância"},
                            {"criterion": "Conforto Acústico", "our_company": "Cabines Silent-Box", "competitor_a": "Mesas abertas", "competitor_b": "Fone de ouvido", "observation": "Alta privacidade"}
                        ],
                        "personas": [
                            {
                                "name": "Davi Tech",
                                "age": "28 anos",
                                "profile": "Desenvolvedor Fullstack que trabalha remoto.",
                                "goals": ["Entregar sprints no prazo", "Networking qualificado"],
                                "challenges": ["Distração doméstica", "Solidão"],
                                "journey": ["Acorda", "Tenta trabalhar", "Se distrai", "Vem para o Versus", "Rende muito"]
                            }
                        ]
                    }
                ],
                "products": [
                    {
                        "name": "Espresso Gourmet",
                        "sale_price": 12.00,
                        "variable_costs_percent": 20.0,
                        "variable_costs_value": 2.40,
                        "variable_expenses_percent": 10.0,
                        "variable_expenses_value": 1.20,
                        "market_share_goal_monthly_units": 500,
                        "ramp_up_entries": [
                            {"month_period": "2026.01", "percentage": 30.0},
                            {"month_period": "2026.02", "percentage": 70.0},
                            {"month_period": "2026.03", "percentage": 100.0}
                        ]
                    },
                    {
                        "name": "Diária Workstation",
                        "sale_price": 45.00,
                        "variable_costs_percent": 5.0,
                        "variable_costs_value": 2.25,
                        "variable_expenses_percent": 5.0,
                        "variable_expenses_value": 2.25,
                        "market_share_goal_monthly_units": 200,
                        "ramp_up_entries": [
                            {"month_period": "2026.01", "percentage": 50.0},
                            {"month_period": "2026.03", "percentage": 100.0}
                        ]
                    }
                ]
            },
            "execution": {
                "areas": {
                    "comercial": {
                        "items": [
                            {
                                "description": "Campanha Meta Ads Launch",
                                "item_type": "outros",
                                "classification": "contratação",
                                "value": 5000.0,
                                "acquisition_date": "2026-03-05",
                                "availability_date": "2026-03-15",
                                "operational_capacity_revenue": 150000.0,
                                "payments": [
                                    {"date": "2026-03-05", "amount": 2500.0},
                                    {"date": "2026-04-05", "amount": 2500.0}
                                ],
                                "repetition": "unica",
                                "supplier": "Agência Pixel",
                                "notes": "Foco em lançamento"
                            }
                        ]
                    },
                    "operacional": {
                        "items": [
                            {
                                "description": "Máquina de Espresso Nuova Simonelli",
                                "item_type": "maquinas",
                                "classification": "aquisição",
                                "value": 15000.0,
                                "acquisition_date": "2026-02-15",
                                "availability_date": "2026-04-01",
                                "operational_capacity_revenue": 80000.0,
                                "payments": [
                                    {"date": "2026-02-15", "amount": 5000.0},
                                    {"date": "2026-03-31", "amount": 5000.0},
                                    {"date": "2026-04-15", "amount": 5000.0}
                                ],
                                "repetition": "unica",
                                "supplier": "Nuova Simonelli",
                                "notes": "Máquina principal"
                            },
                            {
                                "description": "Barista Senior",
                                "item_type": "pessoas",
                                "classification": "contratação",
                                "value": 3500.0,
                                "acquisition_date": "2026-04-01",
                                "availability_date": "2026-04-01",
                                "operational_capacity_revenue": 0.0,
                                "payments": [
                                    {"date": "2026-04-30", "amount": 3500.0}
                                ],
                                "repetition": "mensal",
                                "notes": "Contratação via CLT"
                            }
                        ]
                    }
                }
            },

            "finance": {
                "target_revenue": 100000.0,
                "contribution_margin": 65.0,
                "investments": [
                    {"description": "Reforma e Mobiliário", "category": "capex", "amount": 80000.0},
                    {"description": "Capital de Giro Inicial", "category": "capital_giro", "amount": 40000.0}
                ],
                "sources": [
                    {"category": "socios", "description": "Capital Social Integralizado", "amount": 150000.0}
                ],
                "premises": [
                    {"description": "Ticket Médio", "value": "R$ 38,50"},
                    {"description": "Fluxo Diário", "value": "120 pessoas"}
                ]
            }
        }

        for key, content in data_map.items():
            record = PlanImplantationData.query.filter_by(plan_id=plan.id, section_key=key).first()
            if not record:
                db.session.add(PlanImplantationData(plan_id=plan.id, section_key=key, content=content))
            else:
                record.content = content
            
            status = PlanSectionStatus.query.filter_by(plan_id=plan.id, section_key=key).first()
            if status: status.status = 'completed'
        
        db.session.commit()
        print(f"✅ Implantation Seeded with Structured Data: Plan {plan.id}")

if __name__ == "__main__":
    seed_implantation()
