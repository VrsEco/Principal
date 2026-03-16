import sys
import os
from sqlalchemy import func

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from app import create_app
from models import db, Indicator, IndicatorGoal, IndicatorData

app = create_app()
with app.app_context():
    company_id = 1 # Usando empresa 1 para teste
    print(f"Testando query para company_id={company_id}")
    try:
        goals_count_sq = db.session.query(
            IndicatorGoal.indicator_id, 
            func.count(IndicatorGoal.id).label('count')
        ).filter_by(company_id=company_id).group_by(IndicatorGoal.indicator_id).subquery()

        data_count_sq = db.session.query(
            IndicatorData.indicator_id, 
            func.count(IndicatorData.id).label('count')
        ).filter_by(company_id=company_id).group_by(IndicatorData.indicator_id).subquery()

        indicators = db.session.query(
            Indicator,
            func.coalesce(goals_count_sq.c.count, 0).label('goals_count'),
            func.coalesce(data_count_sq.c.count, 0).label('data_count')
        ).outerjoin(goals_count_sq, Indicator.id == goals_count_sq.c.indicator_id)\
         .outerjoin(data_count_sq, Indicator.id == data_count_sq.c.indicator_id)\
         .filter(Indicator.company_id == company_id)\
         .order_by(Indicator.is_active.desc(), Indicator.source_module, Indicator.name)\
         .all()
         
        print(f"Sucesso! Encontrados {len(indicators)} indicadores.")
        for ind, gc, dc in indicators[:5]:
            print(f" - {ind.name}: Metas={gc}, Dados={dc}")
            
    except Exception as e:
        print(f"Erro na query: {e}")
