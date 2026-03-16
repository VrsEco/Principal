from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
import logging
logger = logging.getLogger(__name__)
from models import db, IndicatorGroup, Indicator, IndicatorGoal, IndicatorData
from schemas.indicator import (
    indicator_schema, indicators_schema, 
    indicator_group_schema, indicator_groups_schema,
    indicator_goal_schema, indicator_goals_schema,
    indicator_data_schema, indicator_data_list_schema
)

from utils.permissions import permission_required

def get_request_company_id():
    from flask import session
    
    def clean(val):
        if val is None: return None
        s = str(val).strip().lower()
        if s in ('null', 'undefined', 'none', ''): return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    # 1. Try Query Arg
    cid = clean(request.args.get('company_id'))
    if cid is not None: return cid
    
    # 2. Try JSON Body
    try:
        if request.is_json:
            data = request.get_json(silent=True)
            if data:
                cid = clean(data.get('company_id'))
                if cid is not None: return cid
    except:
        pass

    # 3. Try Session
    cid = clean(session.get('active_company_id'))
    return cid

class IndicatorListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return [], 200
            
        process_id = request.args.get('process_id')
        project_id = request.args.get('project_id')
        
        query = Indicator.query.filter_by(company_id=company_id)
        if process_id:
            query = query.filter_by(process_id=process_id)
        if project_id:
            query = query.filter_by(project_id=project_id)
            
        indicators = query.all()
        return indicators_schema.dump(indicators), 200

    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
                
            # --- Automatic Code Generation ---
            if not data.get('code') or data.get('code') in ('Auto', 'Gerado automaticamente'):
                tree_id = data.get('tree_id')
                code = "PENDING"
                if tree_id:
                    from models import IndicatorTree, Indicator
                    parent_node = IndicatorTree.query.filter_by(id=tree_id, company_id=cid).first()
                    if parent_node:
                        # Check for existing children in Tree (subgroups)
                        tree_children = IndicatorTree.query.filter_by(company_id=cid, parent_id=tree_id).all()
                        # Check for existing children in Indicators (KPIs)
                        indicator_children = Indicator.query.filter_by(company_id=cid, tree_id=tree_id).all()
                        
                        indices = []
                        for c in tree_children:
                            last_part = c.code.split('.')[-1]
                            if last_part.isdigit(): indices.append(int(last_part))
                        for i in indicator_children:
                            if i.code:
                                last_part = i.code.split('.')[-1]
                                if last_part.isdigit(): indices.append(int(last_part))
                        
                        next_idx = max(indices) + 1 if indices else 1
                        code = f"{parent_node.code}.{next_idx}"
                else:
                    # Fallback to root-like
                    from models import Company, IndicatorTree
                    company = Company.query.get(cid)
                    prefix = company.client_code or "VS" if company else "VS"
                    roots = IndicatorTree.query.filter_by(company_id=cid, parent_id=None).all()
                    indices = []
                    for r in roots:
                        parts = r.code.split('.')
                        if len(parts) >= 3 and parts[2].isdigit(): indices.append(int(parts[2]))
                    next_idx = max(indices) + 1 if indices else 1
                    code = f"{prefix}.I.{next_idx}"
                data['code'] = code
                data['full_code'] = code

            indicator = indicator_schema.load(data)
            db.session.add(indicator)
            db.session.commit()
            return indicator_schema.dump(indicator), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, indicator_id):
        company_id = get_request_company_id()
        indicator = Indicator.query.filter_by(id=indicator_id, company_id=company_id).first_or_404()
        return indicator_schema.dump(indicator), 200

    @permission_required('indicators', 'edit')
    def put(self, indicator_id):
        company_id = get_request_company_id()
        indicator = Indicator.query.filter_by(id=indicator_id, company_id=company_id).first_or_404()
        try:
            data = request.get_json()
            data['company_id'] = company_id
            indicator = indicator_schema.load(data, instance=indicator, partial=True)
            db.session.commit()
            return indicator_schema.dump(indicator), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @permission_required('indicators', 'delete')
    def delete(self, indicator_id):
        company_id = get_request_company_id()
        indicator = Indicator.query.filter_by(id=indicator_id, company_id=company_id).first_or_404()
        try:
            db.session.delete(indicator)
            db.session.commit()
            return {"message": "Indicator deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorGroupListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return [], 200
            
        query = IndicatorGroup.query.filter_by(company_id=company_id)
        groups = query.all()
        return indicator_groups_schema.dump(groups), 200

    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
                
            group = indicator_group_schema.load(data)
            db.session.add(group)
            db.session.commit()
            return indicator_group_schema.dump(group), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorGoalListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        company_id = get_request_company_id()
        indicator_id = request.args.get('indicator_id')
        if not indicator_id or not company_id:
            return [], 200
             
        query = IndicatorGoal.query.filter_by(company_id=company_id, indicator_id=indicator_id)
        goals = query.all()
        return indicator_goals_schema.dump(goals), 200

    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            # --- Autocodificação (AB.M.1) ---
            from models.company import Company
            company = Company.query.get(cid)
            client_prefix = company.client_code if company and company.client_code else 'XX'
            
            # Contar metas existentes para sequencial
            total_goals = IndicatorGoal.query.filter_by(company_id=cid).count()
            data['code'] = f"{client_prefix}.M.{total_goals + 1}"
            # -------------------------------
                
            goal = indicator_goal_schema.load(data)
            db.session.add(goal)
            db.session.commit()
            return indicator_goal_schema.dump(goal), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorGoalResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, goal_id):
        goal = IndicatorGoal.query.get_or_404(goal_id)
        return indicator_goal_schema.dump(goal), 200

    @permission_required('indicators', 'edit')
    def put(self, goal_id):
        goal = IndicatorGoal.query.get_or_404(goal_id)
        try:
            data = request.get_json()
            goal = indicator_goal_schema.load(data, instance=goal, partial=True)
            db.session.commit()
            return indicator_goal_schema.dump(goal), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    def patch(self, goal_id):
        return self.put(goal_id)

    @permission_required('indicators', 'edit')
    def delete(self, goal_id):
        goal = IndicatorGoal.query.get_or_404(goal_id)
        try:
            db.session.delete(goal)
            db.session.commit()
            return {"message": "Goal deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorDataListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        goal_id = request.args.get('goal_id')
        indicator_id = request.args.get('indicator_id')
        
        if not goal_id and not indicator_id:
            return [], 200
            
        query = IndicatorData.query
        if goal_id:
            query = query.filter_by(goal_id=goal_id)
        elif indicator_id:
            query = query.filter_by(indicator_id=indicator_id)
            
        data_records = query.all()
        return indicator_data_list_schema.dump(data_records), 200


    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
                
            record = indicator_data_schema.load(data)
            db.session.add(record)
            db.session.commit()

            # --- Trigger Dependent Calculations (CMV, etc.) ---
            try:
                from services.indicator_service import IndicatorService
                IndicatorService.trigger_dependent_calculations(
                    company_id=record.company_id,
                    component_indicator_id=record.indicator_id,
                    reference_date=record.measured_date
                )
            except Exception as e:
                logger.error(f"Erro ao disparar cálculos dependentes: {e}")

            return indicator_data_schema.dump(record), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorDataResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, data_id):
        record = IndicatorData.query.get_or_404(data_id)
        return indicator_data_schema.dump(record), 200

    @permission_required('indicators', 'edit')
    def delete(self, data_id):
        record = IndicatorData.query.get_or_404(data_id)
        try:
            db.session.delete(record)
            db.session.commit()
            return {"message": "Data record deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class IndicatorAuditResource(Resource):
    """Resource para o Sapiens Wizard auditar indicadores sem rotina."""
    @permission_required('indicators', 'view')
    def get(self):
        company_id = get_request_company_id()
        if not company_id: return {"error": "Empresa não identificada"}, 400
        
        from services.indicator_service import IndicatorService
        orphans = IndicatorService.get_orphaned_indicators(company_id)
        return indicators_schema.dump(orphans), 200

class IndicatorWizardBatchResource(Resource):
    """Resource para o Sapiens Wizard aplicar vínculos em massa às metas."""
    @permission_required('indicators', 'edit')
    def post(self):
        from models import IndicatorGoal
        data = request.get_json()
        company_id = get_request_company_id()
        links = data.get('links', []) # List of {indicator_id: X, routine_id: Y}
        
        updated_count = 0
        for link in links:
            # Para cada indicador, buscamos a meta ativa para vincular a rotina
            active_goal = IndicatorGoal.query.filter_by(
                indicator_id=link['indicator_id'], 
                company_id=company_id,
                status='active'
            ).first()
            
            if active_goal:
                active_goal.routine_id = link.get('routine_id')
                updated_count += 1
        
        db.session.commit()
        return {"status": "success", "updated": updated_count}, 200
class IndicatorDataBatchResource(Resource):
    """Resource para salvar múltiplos registros de dados de uma vez (Planilha de Rotina)."""
    @permission_required('indicators', 'create')
    def post(self):
        try:
            payload = request.get_json()
            company_id = get_request_company_id()
            if not company_id:
                return {"error": "Empresa não identificada"}, 400
                
            entries = payload.get('entries', [])
            if not entries:
                return {"message": "Nenhum dado enviado"}, 400
            
            created_records = []
            for entry in entries:
                # Merge company_id if not present
                if 'company_id' not in entry:
                    entry['company_id'] = company_id
                
                # Check if it has a value (skip empty entries)
                if entry.get('measured_value') is None or entry.get('measured_value') == '':
                    continue
                    
                record = indicator_data_schema.load(entry)
                record.is_manual = True
                record.status = 'manual_override'
                db.session.add(record)
                created_records.append(record)
            
            db.session.commit()

            # Trigger calculations for each indicator uniquely
            from services.indicator_service import IndicatorService
            processed_indicators = set()
            for record in created_records:
                if record.indicator_id not in processed_indicators:
                    try:
                        IndicatorService.trigger_dependent_calculations(
                            company_id=record.company_id,
                            component_indicator_id=record.indicator_id,
                            reference_date=record.measured_date
                        )
                        processed_indicators.add(record.indicator_id)
                    except Exception as e:
                        logger.error(f"Batch calculation error for ind {record.indicator_id}: {e}")

            # Fechar instância de processo se foi informada no payload
            process_instance_id = payload.get('process_instance_id')
            if process_instance_id:
                try:
                    from models import ProcessInstance
                    from datetime import datetime
                    instance = ProcessInstance.query.filter_by(
                        id=int(process_instance_id),
                        company_id=company_id
                    ).first()
                    if instance and instance.status in ('pending', 'in_progress'):
                        instance.status = 'completed'
                        instance.completed_at = datetime.utcnow()
                        instance.actual_end_date = datetime.utcnow().date()
                        db.session.commit()
                        logger.info(f"ProcessInstance #{process_instance_id} concluída via batch de indicadores.")
                except Exception as e:
                    logger.error(f"Erro ao concluir instância {process_instance_id}: {e}")

            return {"status": "success", "saved": len(created_records)}, 201
            
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500
