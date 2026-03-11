import re
import os
import uuid
from datetime import datetime, date
from decimal import Decimal
from flask import request, current_app, session
from flask_restful import Resource
from flask_login import current_user
from marshmallow import ValidationError
from werkzeug.utils import secure_filename
from schemas.process import (
    process_area_schema, process_areas_schema,
    macro_process_schema, macro_processes_schema,
    process_schema, processes_schema,
    process_routine_schema, process_routines_schema,
    process_step_schema, process_steps_schema,
    process_instance_schema, process_instances_schema
)
from models import db, ProcessArea, MacroProcess, Process, ProcessRoutine, ProcessStep, ProcessInstance, Company, Indicator, ActivityWorkLog
from utils.permissions import get_default_company_id, has_company_full_access, has_permission, permission_required
from database import get_db
from sqlalchemy import or_

def _instance_visible_to_employee(instance, employee_id):
    if not instance or not employee_id:
        return False
    if instance.owner_employee_id == employee_id or instance.responsible_id == employee_id or instance.executor_id == employee_id:
        return True

    collaborators = instance.collaborators_json or []
    if isinstance(collaborators, list):
        for item in collaborators:
            if item == employee_id:
                return True
            if isinstance(item, dict):
                raw_id = item.get('employee_id') or item.get('id')
                try:
                    if raw_id is not None and int(raw_id) == int(employee_id):
                        return True
                except (TypeError, ValueError):
                    continue
    return False

def apply_instance_employee_filter(query, company_id):
    from flask_login import current_user

    if not current_user.is_authenticated:
        return query.filter(ProcessInstance.id == None)

    if has_company_full_access(company_id):
        return query

    # Para colaborador, a filtragem final é feita em Python para suportar collaborators_json no PostgreSQL.
    return query

def generate_area_code(company_id, sequence):
    company = Company.query.get(company_id)
    if not company or not company.client_code:
        return f"C.{sequence}"
    return f"{company.client_code}.C.{sequence}"

def generate_macro_code(area_id, sequence):
    area = ProcessArea.query.get(area_id)
    if not area or not area.code:
        return f"?.{sequence}"
    return f"{area.code}.{sequence}"

def generate_process_code(macro_id, sequence):
    macro = MacroProcess.query.get(macro_id)
    if not macro or not macro.code:
        return f"?.{sequence}"
    return f"{macro.code}.{sequence}"

def natural_sort_key(s):
    if s is None:
        s = ""
    # Returns a list of tuples (0, int) for numbers and (1, str) for text
    # This ensures types are always comparable in Python 3
    return [(0, int(text)) if text.isdigit() else (1, text.lower())
            for text in re.split('([0-9]+)', str(s)) if text]

def get_request_company_id():
    from flask import session
    from flask_login import current_user
    from models import Company, Employee
    
    def clean(val):
        if val is None: return None
        s = str(val).strip().lower()
        if s in ('null', 'undefined', 'none', ''): return None
        try:
            # Handle possible float strings like "1.0"
            return int(float(val))
        except (ValueError, TypeError):
            return None

    # 1. Try Query Arg
    cid = clean(request.args.get('company_id'))
    if cid is not None: return cid
    
    # 2. Try JSON Body (if it's a POST/PUT)
    try:
        if request.is_json:
            # use silent=True to avoid 400 if body is empty or not JSON
            # though usually Resource handles this
            data = request.get_json(silent=True)
            if data:
                cid = clean(data.get('company_id'))
                if cid is not None: return cid
    except:
        pass

    # 3. Try Session
    cid = clean(session.get('active_company_id'))
    if cid:
        return cid

    # 4. Fallback: pick a company the user can access
    if current_user.is_authenticated:
        default_company_id = get_default_company_id()
        if default_company_id:
            return default_company_id

    return None


def fetch_pop_routines(process_id: int, include_schedules: bool = False):
    """
    Retorna atividades de POP (process_routines).
    Se include_schedules for True, também inclui dados da tabela routines (legado ou agendamentos).
    """
    if not process_id:
        return []

    conn = None
    try:
        pg = get_db()
        conn = pg._get_connection()
        cursor = conn.cursor()

        if include_schedules:
            cursor.execute(
                """
                SELECT id, process_id, code, name, description,
                       COALESCE(order_index, 0) AS order_index,
                       CAST(created_at AS TIMESTAMP) AS created_at,
                       CAST(is_active AS BOOLEAN) AS is_active,
                       'process_routines' AS source,
                       NULL as schedule_type, NULL as schedule_value, 0 as deadline_days, 0 as deadline_hours, NULL as deadline_date
                FROM process_routines
                WHERE process_id = %s AND (is_active = TRUE OR is_active IS NULL)
                UNION ALL
                SELECT id, process_id, NULL as code, name, description,
                       0 AS order_index,
                       CAST(created_at AS TIMESTAMP) AS created_at,
                       CAST(is_active AS BOOLEAN) AS is_active,
                       'routines' AS source,
                       schedule_type, schedule_value, deadline_days, deadline_hours, deadline_date
                FROM routines
                WHERE process_id = %s AND (is_active = TRUE OR is_active IS NULL)
                ORDER BY order_index, id
                """,
                (process_id, process_id),
            )
        else:
            cursor.execute(
                """
                SELECT id, process_id, code, name, description,
                       COALESCE(order_index, 0) AS order_index,
                       CAST(created_at AS TIMESTAMP) AS created_at,
                       CAST(is_active AS BOOLEAN) AS is_active,
                       'process_routines' AS source,
                       NULL as schedule_type, NULL as schedule_value, 0 as deadline_days, 0 as deadline_hours, NULL as deadline_date
                FROM process_routines
                WHERE process_id = %s AND (is_active = TRUE OR is_active IS NULL)
                ORDER BY order_index, id
                """,
                (process_id,),
            )

        routines = [dict(row) for row in cursor.fetchall()]

        # Ensure JSON serializable dates
        for r in routines:
            for k, v in r.items():
                if isinstance(v, (datetime, date)):
                    r[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    r[k] = float(v)

        routine_ids = [r["id"] for r in routines]

        if routine_ids:
            placeholders = ",".join(["%s"] * len(routine_ids))
            cursor.execute(
                f"""
                SELECT id, routine_id, name, description, expected_result,
                       COALESCE(order_index, 0) AS order_index,
                       image_path, image_width, layout
                FROM process_steps
                WHERE routine_id IN ({placeholders})
                ORDER BY COALESCE(order_index,0), id
                """,
                tuple(routine_ids),
            )
            steps = [
                {
                    "id": row[0],
                    "routine_id": row[1],
                    "name": row[2],
                    "description": row[3],
                    "expected_result": row[4],
                    "order_index": row[5],
                    "image_path": row[6],
                    "image_width": row[7],
                    "layout": row[8],
                }
                for row in cursor.fetchall()
            ]
            steps_map = {}
            for step in steps:
                steps_map.setdefault(step["routine_id"], []).append(step)
            for routine in routines:
                routine["steps"] = steps_map.get(routine["id"], [])
        else:
            for routine in routines:
                routine["steps"] = []

        return routines
    except Exception as e:
        current_app.logger.error(f"Error fetching routines for process {process_id}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _get_process_with_access(process_id: int, action: str = 'view', sync_session: bool = False):
    process = Process.query.get_or_404(process_id)

    if not current_user.is_authenticated:
        return None

    if not has_permission(process.company_id, 'processes', action):
        return None

    if sync_session:
        session['active_company_id'] = process.company_id

    return process


def fetch_pop_routine_by_id(routine_id: int):
    """Busca uma rotina específica (POP) em ambas as tabelas e anexa passos."""
    if not routine_id:
        return None
    pg = get_db()
    conn = pg._get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, process_id, code, name, description,
               COALESCE(order_index, 0) AS order_index,
               CAST(created_at AS TIMESTAMP) AS created_at,
               CAST(is_active AS BOOLEAN) AS is_active,
               'process_routines' AS source
        FROM process_routines
        WHERE id = %s
        UNION ALL
        SELECT id, process_id, code, name, description,
               COALESCE(order_index, 0) AS order_index,
               CAST(created_at AS TIMESTAMP) AS created_at,
               CAST(is_active AS BOOLEAN) AS is_active,
               'routines' AS source
        FROM routines
        WHERE id = %s
        """,
        (routine_id, routine_id),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    routine = dict(row)

    # Ensure JSON serializable dates
    for k, v in routine.items():
        if isinstance(v, (datetime, date)):
            routine[k] = v.isoformat()
        elif isinstance(v, Decimal):
            routine[k] = float(v)

    cursor.execute(
        """
        SELECT id, routine_id, name, description, expected_result,
               COALESCE(order_index, 0) AS order_index,
               image_path, image_width
        FROM process_steps
        WHERE routine_id = %s
        ORDER BY COALESCE(order_index,0), id
        """,
        (routine_id,),
    )
    routine["steps"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return routine


class ProcessInstanceListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, company_id=None):
        if not company_id:
            company_id = get_request_company_id()
        
        if not company_id:
            return [], 200
            
        query = ProcessInstance.query.filter_by(company_id=company_id)
        query = apply_instance_employee_filter(query, company_id)
        
        process_id = request.args.get('process_id')
        if process_id:
            query = query.filter_by(process_id=process_id)
            
        instances = query.all()
        if not has_company_full_access(company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
            if employee:
                instances = [inst for inst in instances if _instance_visible_to_employee(inst, employee.id)]
            else:
                instances = []
        
        # Enrich with normalized collaborators (Owner, Responsible, Executors)
        from models.employee import Employee
        employees = {e.id: e.name for e in Employee.query.filter_by(company_id=company_id).all()}
        
        results = []
        for inst in instances:
            data = process_instance_schema.dump(inst)
            collabs = []
            
            # Owner
            if inst.owner_employee_id and inst.owner_employee_id in employees:
                collabs.append({
                    'role': 'owner',
                    'name': employees[inst.owner_employee_id],
                    'id': inst.owner_employee_id
                })
            
            # Responsible
            if inst.responsible_id and inst.responsible_id in employees:
                collabs.append({
                    'role': 'responsible',
                    'name': employees[inst.responsible_id],
                    'id': inst.responsible_id
                })
            
            # Executors
            if inst.executor_id and inst.executor_id in employees:
                collabs.append({
                    'role': 'executor',
                    'name': employees[inst.executor_id],
                    'id': inst.executor_id
                })
            
            # Check collaborators_json
            if inst.collaborators_json and isinstance(inst.collaborators_json, list):
                for c in inst.collaborators_json:
                    if isinstance(c, dict):
                        e_id = c.get('employee_id') or c.get('id')
                        if e_id and e_id in employees:
                            # Avoid duplicates
                            if not any(x['id'] == e_id and x['role'] == c.get('role', 'executor') for x in collabs):
                                collabs.append({
                                    'role': c.get('role', 'executor'),
                                    'name': employees[e_id],
                                    'id': e_id
                                })
                    elif isinstance(c, int):
                         if c in employees:
                             collabs.append({
                                'role': 'executor',
                                'name': employees[c],
                                'id': c
                             })
            
            data['normalized_collaborators'] = collabs
            results.append(data)

        return results, 200

    @permission_required('processes', 'create')
    def post(self, company_id=None):
        try:
            data = request.get_json()
            if not data:
                data = {}
            
            # Determine company_id: URL > Body > Session
            cid = company_id
            if not cid:
                cid = data.get('company_id')
            if not cid:
                cid = get_request_company_id()
            
            if cid:
                data['company_id'] = cid
            
            # Auto-generate instance_code if missing
            if not data.get('instance_code'):
                from models import Company, Process
                
                comp = Company.query.get(cid)
                proc = Process.query.get(data.get('process_id'))
                
                c_code = comp.client_code if comp and comp.client_code else str(cid)
                p_code = proc.code if proc and proc.code else (proc.name[:3].upper() if proc else 'PRC')
                
                # Count existing instances for this company/process
                count = ProcessInstance.query.filter_by(company_id=cid, process_id=data.get('process_id')).count()
                data['instance_code'] = f"{p_code}-{count + 1}"

            # Auto-populate collaborators from Process definition if not provided
            if not data.get('collaborators_json'):
                from models import Employee
                collaborators = []
                
                # Fetch Process Owner
                if proc and proc.owner_employee_id:
                    owner = Employee.query.get(proc.owner_employee_id)
                    if owner:
                        collaborators.append({
                            "id": owner.id,
                            "name": owner.name,
                            "role": "owner",
                            "hours": 0,
                            "actual_hours": 0
                        })
                
                # Fetch Process Responsible
                if proc and proc.responsible_id:
                     resp = Employee.query.get(proc.responsible_id)
                     if resp:
                        # Avoid duplicate if owner is same as responsible
                        if not any(c['id'] == resp.id for c in collaborators):
                            collaborators.append({
                                "id": resp.id,
                                "name": resp.name,
                                "role": "responsible", 
                                "hours": 0,
                                "actual_hours": 0
                            })
                
                # If there is a routine, check for routine specific roles
                if data.get('routine_id'):
                    routine_id = data.get('routine_id')
                    try:
                        pg = get_db()
                        conn = pg._get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT rc.employee_id, e.name 
                            FROM routine_collaborators rc
                            JOIN employees e ON rc.employee_id = e.id
                            WHERE rc.routine_id = %s
                        """, (routine_id,))
                        
                        rows = cursor.fetchall()
                        cursor.close()
                        
                        for row in rows:
                            # Row can be dict or tuple depending on driver/factory
                            # Based on other files, it seems to support dict-like access or valid access
                            if hasattr(row, 'get'): 
                                emp_id = row['employee_id']
                                emp_name = row['name']
                            else:
                                emp_id = row[0]
                                emp_name = row[1]
                                
                            # Avoid duplicates
                            if not any(c['id'] == emp_id for c in collaborators):
                                collaborators.append({
                                    "id": emp_id,
                                    "name": emp_name,
                                    "role": "executor",
                                    "hours": 0,
                                    "actual_hours": 0
                                })
                    except Exception as e:
                        print(f"Error fetching routine collaborators: {e}")

                if collaborators:
                    data['collaborators_json'] = collaborators
                    # Also set the legacy ID columns for compatibility
                    if proc.owner_employee_id:
                        data['owner_employee_id'] = proc.owner_employee_id
                    if proc.responsible_id:
                        data['responsible_id'] = proc.responsible_id

            instance = process_instance_schema.load(data)
            db.session.add(instance)
            db.session.commit()
            
            # Populate normalized collaborators table
            if data.get('collaborators_json'):
                from models import ProcessInstanceCollaborator
                for c in data['collaborators_json']:
                    try:
                        collab_obj = ProcessInstanceCollaborator(
                            process_instance_id=instance.id,
                            employee_id=c.get('id') or c.get('employee_id'),
                            role=c.get('role', 'executor'),
                            estimated_hours=c.get('hours', 0),
                            notes=c.get('notes')
                        )
                        db.session.add(collab_obj)
                    except:
                        continue
                db.session.commit()

            return process_instance_schema.dump(instance), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return {"error": str(e)}, 500

class ProcessInstanceResource(Resource):
    @permission_required('processes', 'view')
    def get(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        if not has_company_full_access(instance.company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee or not _instance_visible_to_employee(instance, employee.id):
                return {"error": "Acesso negado à instância."}, 403
        return process_instance_schema.dump(instance), 200

    @permission_required('processes', 'edit')
    def put(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)

        # Colaboradores restritos só podem editar se participarem diretamente
        if not has_company_full_access(instance.company_id):
            from models.employee import Employee
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=instance.company_id).first()
            if not employee:
                return {"error": "Viewer only: You can only view this process instance."}, 403
            if instance.owner_employee_id != employee.id and \
               instance.responsible_id != employee.id and \
               instance.executor_id != employee.id:
                return {"error": "Viewer only: You can only view this process instance."}, 403

        try:
            data = request.get_json()
            
            # Map frontend 'end_date' is now handled by Schema alias
                
            instance = process_instance_schema.load(data, instance=instance, partial=True)
            db.session.commit()
            return process_instance_schema.dump(instance), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    @permission_required('processes', 'delete')
    def delete(self, instance_id):
        instance = ProcessInstance.query.get_or_404(instance_id)
        
        if not has_company_full_access(instance.company_id):
            return {"error": "Viewer only: You cannot delete process instances."}, 403

        try:
            db.session.delete(instance)
            db.session.commit()
            return {"message": "Process instance deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProcessInstanceWorkLogResource(Resource):
    @permission_required('processes', 'view')
    def get(self, instance_id):
        logs = ActivityWorkLog.query.filter_by(
            activity_type='process_instance',
            activity_id=instance_id
        ).order_by(ActivityWorkLog.created_at.desc()).all()
        
        return [log.to_dict() for log in logs], 200

    @permission_required('processes', 'edit')
    def post(self, instance_id):
        try:
            data = request.get_json()
            instance = ProcessInstance.query.get_or_404(instance_id)
            
            # Create Log
            log = ActivityWorkLog(
                activity_type='process_instance',
                activity_id=instance_id,
                employee_id=data.get('employee_id'),
                employee_name=data.get('employee_name'),
                hours_worked=data.get('hours_worked'),
                description=data.get('description'),
                work_date=datetime.strptime(data.get('work_date'), '%Y-%m-%d').date() if data.get('work_date') else date.today()
            )
            
            db.session.add(log)
            
            # Update Instance Total
            current_total = float(instance.actual_hours or 0)
            added = float(log.hours_worked or 0)
            instance.actual_hours = current_total + added
            # Also update worked_hours to keep in sync if they are duplicates
            instance.worked_hours = instance.actual_hours
            
            db.session.commit()
            
            return log.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ActivityWorkLogItemResource(Resource):
    @permission_required('processes', 'edit')
    def put(self, log_id):
        try:
            log = ActivityWorkLog.query.get_or_404(log_id)
            data = request.get_json()
            
            # Helper to update instance total if hours changed
            if 'hours_worked' in data:
                old_hours = float(log.hours_worked or 0)
                new_hours = float(data['hours_worked'])
                diff = new_hours - old_hours
                
                if log.activity_type == 'process_instance' and diff != 0:
                    instance = ProcessInstance.query.get(log.activity_id)
                    if instance:
                         current_total = float(instance.actual_hours or 0)
                         instance.actual_hours = current_total + diff
                         instance.worked_hours = instance.actual_hours
            
            if 'employee_id' in data: log.employee_id = data['employee_id']
            if 'employee_name' in data: log.employee_name = data['employee_name']
            if 'hours_worked' in data: log.hours_worked = data['hours_worked']
            if 'description' in data: log.description = data['description']
            if 'work_date' in data: 
                log.work_date = datetime.strptime(data['work_date'], '%Y-%m-%d').date()

            db.session.commit()
            return log.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @permission_required('processes', 'edit')
    def delete(self, log_id):
        try:
            log = ActivityWorkLog.query.get_or_404(log_id)
            
            # Update instance total before deleting
            if log.activity_type == 'process_instance':
                instance = ProcessInstance.query.get(log.activity_id)
                if instance:
                    current_total = float(instance.actual_hours or 0)
                    removed = float(log.hours_worked or 0)
                    instance.actual_hours = max(0, current_total - removed)
                    instance.worked_hours = instance.actual_hours
            
            db.session.delete(log)
            db.session.commit()
            return {"message": "Log deleted"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProcessAreaListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, company_id=None):
        try:
            if not company_id:
                company_id = get_request_company_id()
                
            if not company_id:
                return [], 200
                
            query = ProcessArea.query.filter_by(company_id=company_id)
            areas = query.all()
            # Natural sort by code, then order_index, then name
            areas.sort(key=lambda x: (natural_sort_key(x.code), x.order_index or 0, x.name or ""))
            return process_areas_schema.dump(areas), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in ProcessAreaListResource.get: {e}")
            return {"error": str(e)}, 500

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {"error": "No data provided"}, 400
                
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            if not data.get('company_id'):
                return {"error": "company_id is required"}, 400
                
            area = process_area_schema.load(data)
            
            # Generate code automatically
            if area.company_id and area.code:
                area.code = generate_area_code(area.company_id, area.code)
            
            db.session.add(area)
            db.session.commit()
            return process_area_schema.dump(area), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in ProcessAreaListResource.post: {e}")
            return {"error": str(e)}, 500

class ProcessAreaResource(Resource):
    @permission_required('processes', 'view')
    def get(self, area_id):
        area = ProcessArea.query.get_or_404(area_id)
        return process_area_schema.dump(area), 200

    @permission_required('processes', 'edit')
    def put(self, area_id):
        area = ProcessArea.query.get_or_404(area_id)
        try:
            data = request.get_json()
            area = process_area_schema.load(data, instance=area, partial=True)
            
            # Recalculate code if sequence changed
            if 'code' in data and area.company_id:
                # Need to check if user passed only the sequence part
                # If it contains dots, it might already be the full code
                if '.' not in str(data['code']):
                    area.code = generate_area_code(area.company_id, data['code'])
            
            db.session.commit()
            return process_area_schema.dump(area), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    @permission_required('processes', 'delete')
    def delete(self, area_id):
        area = ProcessArea.query.get_or_404(area_id)
        try:
            db.session.delete(area)
            db.session.commit()
            return {"message": "Process area deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class MacroProcessListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, company_id=None):
        try:
            if not company_id:
                company_id = get_request_company_id()
                
            if not company_id:
                return [], 200
                
            area_id = request.args.get('area_id')
            query = MacroProcess.query.filter_by(company_id=company_id)
            if area_id:
                query = query.filter_by(area_id=area_id)
            macros = query.all()
            # Natural sort by code, fallback to order_index
            macros.sort(key=lambda x: (natural_sort_key(x.code), x.order_index or 0, x.name or ""))
            return macro_processes_schema.dump(macros), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in MacroProcessListResource.get: {e}")
            return {"error": str(e)}, 500

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {"error": "No data provided"}, 400
                
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            if not data.get('company_id'):
                return {"error": "company_id is required"}, 400
                
            macro = macro_process_schema.load(data)
            
            # Generate code automatically
            if macro.area_id and macro.order_index:
                macro.code = generate_macro_code(macro.area_id, macro.order_index)
            
            db.session.add(macro)
            db.session.commit()
            return macro_process_schema.dump(macro), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in MacroProcessListResource.post: {e}")
            return {"error": str(e)}, 500

class MacroProcessResource(Resource):
    @permission_required('processes', 'view')
    def get(self, macro_id):
        macro = MacroProcess.query.get_or_404(macro_id)
        return macro_process_schema.dump(macro), 200

    @permission_required('processes', 'edit')
    def put(self, macro_id):
        macro = MacroProcess.query.get_or_404(macro_id)
        try:
            data = request.get_json()
            macro = macro_process_schema.load(data, instance=macro, partial=True)
            
            # Recalculate code if sequence or area changed
            if 'order_index' in data or 'area_id' in data:
                macro.code = generate_macro_code(macro.area_id, macro.order_index)
                
            db.session.commit()
            return macro_process_schema.dump(macro), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400

    @permission_required('processes', 'delete')
    def delete(self, macro_id):
        macro = MacroProcess.query.get_or_404(macro_id)
        try:
            db.session.delete(macro)
            db.session.commit()
            return {"message": "Macro process deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProcessListResource(Resource):
    @permission_required('processes', 'view')
    def get(self, company_id=None):
        try:
            if not company_id:
                company_id = get_request_company_id()
                
            if not company_id:
                return [], 200
                
            macro_id = request.args.get('macro_id')
            query = Process.query.filter_by(company_id=company_id)
            if macro_id:
                query = query.filter_by(macro_id=macro_id)
            processes = query.all()
            # Natural sort by code, fallback to order_index
            processes.sort(key=lambda x: (natural_sort_key(x.code), x.order_index or 0, x.name or ""))
            
            # Dump basic data
            result = processes_schema.dump(processes)
            
            # Enrich with Routines (RTN/POP) and Indicators (IND) for badges
            for p_data in result:
                pid = p_data.get('id')
                if pid:
                    # Fetch Routines (unifying `routines` and `process_routines`)
                    p_data['routines'] = fetch_pop_routines(pid)
                    
                    # Fetch Indicators
                    try:
                        inds = Indicator.query.filter_by(process_id=pid).with_entities(Indicator.id, Indicator.name).all()
                        p_data['indicators'] = [{"id": i.id, "name": i.name} for i in inds]
                    except:
                        p_data['indicators'] = []
            
            return result, 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in ProcessListResource.get: {e}")
            return {"error": str(e)}, 500

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            if not data:
                return {"error": "No data provided"}, 400
                
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid
            
            if not data.get('company_id'):
                return {"error": "company_id is required"}, 400
                
            process = process_schema.load(data)
            
            # Generate code automatically
            if process.macro_id and process.order_index:
                process.code = generate_process_code(process.macro_id, process.order_index)
                
            db.session.add(process)
            db.session.commit()
            return process_schema.dump(process), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in ProcessListResource.post: {e}")
            return {"error": str(e)}, 500

from utils.storage import save_file, delete_file

class ProcessResource(Resource):
    @permission_required('processes', 'view')
    def get(self, process_id):
        current_app.logger.info(
            'ProcessResource.get start process_id=%s path=%s user_id=%s active_company_id=%s args=%s',
            process_id,
            request.path,
            getattr(current_user, 'id', None),
            session.get('active_company_id'),
            dict(request.args),
        )

        try:
            process = _get_process_with_access(process_id, action='view', sync_session=True)
            if not process:
                current_app.logger.warning(
                    'ProcessResource.get denied process_id=%s user_id=%s active_company_id=%s',
                    process_id,
                    getattr(current_user, 'id', None),
                    session.get('active_company_id'),
                )
                return {"error": "Permission denied: view on processes"}, 403

            payload = process_schema.dump(process)
            current_app.logger.info(
                'ProcessResource.get success process_id=%s company_id=%s macro_id=%s user_id=%s',
                process_id,
                getattr(process, 'company_id', None),
                getattr(process, 'macro_id', None),
                getattr(current_user, 'id', None),
            )
            return payload, 200
        except Exception:
            current_app.logger.exception(
                'ProcessResource.get failure process_id=%s user_id=%s active_company_id=%s',
                process_id,
                getattr(current_user, 'id', None),
                session.get('active_company_id'),
            )
            raise

    @permission_required('processes', 'edit')
    def put(self, process_id):
        process = _get_process_with_access(process_id, action='edit', sync_session=True)
        if not process:
            return {"error": "Permission denied: edit on processes"}, 403
        try:
            if request.mimetype == 'multipart/form-data':
                # Handle flow document upload
                file = request.files.get('flow_document')
                if file and file.filename:
                    # Delete old file
                    if process.flow_document:
                        delete_file(process.flow_document)
                    
                    # Save new file
                    process.flow_document = save_file(file, subfolder='flows')
                
                # Update other fields from form data
                if 'name' in request.form: process.name = request.form.get('name')
                if 'description' in request.form: process.description = request.form.get('description')
                # ... other fields if needed
                
                db.session.commit()
                return process_schema.dump(process), 200
            else:
                # Handle standard JSON
                data = request.get_json()
                process = process_schema.load(data, instance=process, partial=True)
                
                # Recalculate code if sequence or macro changed
                if 'order_index' in data or 'macro_id' in data:
                    process.code = generate_process_code(process.macro_id, process.order_index)
                    
                db.session.commit()
                return process_schema.dump(process), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @permission_required('processes', 'delete')
    def delete(self, process_id):
        process = _get_process_with_access(process_id, action='delete', sync_session=True)
        if not process:
            return {"error": "Permission denied: delete on processes"}, 403
        try:
            db.session.delete(process)
            db.session.commit()
            return {"message": "Process deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProcessRoutineListResource(Resource):
    @permission_required('processes', 'view')
    def get(self):
        process_id = request.args.get('process_id', type=int)
        if not process_id:
            return [], 200
        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403
        try:
            routines = fetch_pop_routines(process.id)
            return routines, 200
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}, 500

    @permission_required('processes', 'create')
    def post(self):
        try:
            data = request.get_json()
            process_id = data.get('process_id') if data else None
            if process_id:
                proc = _get_process_with_access(process_id, action='create', sync_session=True)
                if not proc:
                    return {"error": "Permission denied: create on processes"}, 403
                if not data.get('company_id'):
                    data['company_id'] = proc.company_id

            routine = process_routine_schema.load(data)
            
            # Ensure company_id is set on object (in case schema ignored it)
            if not getattr(routine, 'company_id', None) and data.get('company_id'):
                 routine.company_id = data.get('company_id')

            # Persistir sempre em process_routines (POP)
            db.session.add(routine)
            db.session.commit()
            resp = process_routine_schema.dump(routine)
            resp["source"] = "process_routines"
            return resp, 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProcessRoutineResource(Resource):
    @permission_required('processes', 'view')
    def get(self, routine_id):
        routine = fetch_pop_routine_by_id(routine_id)
        if routine:
            return routine, 200
        return {"error": "Routine not found"}, 404

    @permission_required('processes', 'edit')
    def put(self, routine_id):
        try:
            data = request.get_json()
            # Tenta atualizar primeiro em process_routines (POP)
            updated = False
            pg = get_db()
            conn = pg._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM process_routines WHERE id = %s", (routine_id,))
            if cursor.fetchone():
                cursor.execute(
                    """
                    UPDATE process_routines
                    SET name = COALESCE(%s, name), 
                        description = COALESCE(%s, description), 
                        code = COALESCE(%s, code), 
                        order_index = COALESCE(%s, order_index), 
                        process_id = COALESCE(%s, process_id),
                        is_active = COALESCE(%s, is_active)
                    WHERE id = %s
                    """,
                    (
                        data.get("name"),
                        data.get("description"),
                        data.get("code"),
                        data.get("order_index"),
                        data.get("process_id"),
                        data.get("is_active"),
                        routine_id,
                    ),
                )
                conn.commit()
                updated = True
            else:
                cursor.execute("SELECT id FROM routines WHERE id = %s", (routine_id,))
                if cursor.fetchone():
                    cursor.execute(
                        """
                        UPDATE routines
                        SET name = COALESCE(%s, name), 
                            description = COALESCE(%s, description), 
                            code = COALESCE(%s, code), 
                            order_index = COALESCE(%s, order_index), 
                            process_id = COALESCE(%s, process_id), 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (
                            data.get("name"),
                            data.get("description"),
                            data.get("code"),
                            data.get("order_index"),
                            data.get("process_id"),
                            routine_id,
                        ),
                    )
                    conn.commit()
                    updated = True
            conn.close()
            if not updated:
                return {"error": "Routine not found"}, 404
            # Retornar registro atualizado
            routine = fetch_pop_routine_by_id(routine_id)
            if routine:
                return routine, 200
            return {"message": "Rotina atualizada"}, 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}, 500

    @permission_required('processes', 'delete')
    def delete(self, routine_id):
        try:
            pg = get_db()
            conn = pg._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM process_routines WHERE id = %s", (routine_id,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE process_routines SET is_active = FALSE WHERE id = %s",
                    (routine_id,),
                )
                conn.commit()
                conn.close()
                return {"message": "Routine deleted successfully"}, 200

            cursor.execute("SELECT id FROM routines WHERE id = %s", (routine_id,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE routines SET is_active = FALSE WHERE id = %s",
                    (routine_id,),
                )
                conn.commit()
                conn.close()
                return {"message": "Routine deleted successfully"}, 200

            conn.close()
            return {"error": "Routine not found"}, 404
        except Exception as e:
            return {"error": str(e)}, 500

class ProcessStepListResource(Resource):
    @permission_required('processes', 'view')
    def get(self):
        routine_id = request.args.get('routine_id')
        if not routine_id:
            return [], 200
            
        query = ProcessStep.query.filter_by(routine_id=routine_id)
        steps = query.order_by(ProcessStep.order_index).all()
        return process_steps_schema.dump(steps), 200

    @permission_required('processes', 'create')
    def post(self):
        try:
            if request.mimetype == 'multipart/form-data':
                # Handle form data (with optional file)
                routine_id = request.form.get('routine_id')
                name = request.form.get('name')
                description = request.form.get('description')
                expected_result = request.form.get('expected_result')
                layout = request.form.get('layout', 'single')
                image_width = request.form.get('image_width', 280)
                order_index = request.form.get('order_index', 0)
                
                step = ProcessStep(
                    routine_id=routine_id,
                    name=name,
                    description=description,
                    expected_result=expected_result,
                    layout=layout,
                    image_width=int(image_width),
                    order_index=int(order_index)
                )

                file = request.files.get('image')
                if file and file.filename:
                    step.image_path = save_file(file, subfolder='pop')
                
                db.session.add(step)
                db.session.commit()
                return process_step_schema.dump(step), 201
            else:
                # Handle standard JSON
                data = request.get_json()
                step = process_step_schema.load(data)
                db.session.add(step)
                db.session.commit()
                return process_step_schema.dump(step), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProcessStepResource(Resource):
    @permission_required('processes', 'view')
    def get(self, step_id):
        step = ProcessStep.query.get_or_404(step_id)
        return process_step_schema.dump(step), 200

    @permission_required('processes', 'edit')
    def put(self, step_id):
        step = ProcessStep.query.get_or_404(step_id)
        try:
            if request.mimetype == 'multipart/form-data':
                # Handle form data (with optional file)
                if 'name' in request.form: step.name = request.form.get('name')
                if 'description' in request.form: step.description = request.form.get('description')
                if 'expected_result' in request.form: step.expected_result = request.form.get('expected_result')
                if 'layout' in request.form: step.layout = request.form.get('layout')
                if 'image_width' in request.form: step.image_width = int(request.form.get('image_width'))
                if 'order_index' in request.form: step.order_index = int(request.form.get('order_index'))
                
                remove_image = request.form.get('remove_image') == '1'
                if remove_image and step.image_path:
                    delete_file(step.image_path)
                    step.image_path = None

                file = request.files.get('image')
                if file and file.filename:
                    # Delete old file
                    if step.image_path:
                        delete_file(step.image_path)
                    
                    step.image_path = save_file(file, subfolder='pop')
                
                db.session.commit()
                return process_step_schema.dump(step), 200
            else:
                # Handle standard JSON
                data = request.get_json()
                step = process_step_schema.load(data, instance=step, partial=True)
                db.session.commit()
                return process_step_schema.dump(step), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @permission_required('processes', 'delete')
    def delete(self, step_id):
        step = ProcessStep.query.get_or_404(step_id)
        try:
            if step.image_path:
                delete_file(step.image_path)
            db.session.delete(step)
            db.session.commit()
            return {"message": "Step deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProcessScheduleListResource(Resource):
    @permission_required('processes', 'view')
    def get(self):
        process_id = request.args.get('process_id', type=int)
        if not process_id:
            return [], 400

        process = _get_process_with_access(process_id, action='view', sync_session=True)
        if not process:
            return {"error": "Permission denied: view on processes"}, 403

        try:
            # Busca APENAS na tabela routines (agendamentos) associados ao processo
            pg = get_db()
            conn = pg._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, process_id, code, name, description,
                       schedule_type, schedule_value, deadline_days, deadline_hours, deadline_date,
                       score_weight, created_at, updated_at
                FROM routines
                WHERE process_id = %s AND (is_active = TRUE OR is_active IS NULL)
                ORDER BY created_at DESC
                """,
                (process.id,)
            )
            
            routines = [dict(row) for row in cursor.fetchall()]

            # Enrich with collaborators and ensure JSON serialization
            if routines:
                for r in routines:
                    # Convert dates and decimals
                    for k, v in r.items():
                        if isinstance(v, (datetime, date)):
                            r[k] = v.isoformat()
                        elif isinstance(v, Decimal):
                            r[k] = float(v)

                    # Fetch collaborators for each routine
                    cursor.execute("""
                        SELECT e.name
                        FROM routine_collaborators rc
                        JOIN employees e ON e.id = rc.employee_id
                        WHERE rc.routine_id = %s
                    """, (r['id'],))
                    collabs = cursor.fetchall()
                    r['team'] = [c['name'] for c in collabs]
                conn.close()

            return routines, 200
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}, 500
