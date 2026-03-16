from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy import text

from models import db, IndicatorGroup, Indicator, IndicatorGoal, IndicatorData
from schemas.indicator import (
    indicator_schema, indicators_schema,
    indicator_group_schema, indicator_groups_schema,
    indicator_goal_schema, indicator_goals_schema,
    indicator_data_schema, indicator_data_list_schema,
)
from utils.permissions import permission_required


def get_request_company_id():
    from flask import session

    def clean(val):
        if val is None:
            return None
        s = str(val).strip().lower()
        if s in ('null', 'undefined', 'none', ''):
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    cid = clean(request.args.get('company_id'))
    if cid is not None:
        return cid

    try:
        if request.is_json:
            data = request.get_json(silent=True)
            if data:
                cid = clean(data.get('company_id'))
                if cid is not None:
                    return cid
    except Exception:
        pass

    return clean(session.get('active_company_id'))


def _serialize_indicator_row(row):
    item = dict(row._mapping)
    last_value = item.get('last_value')
    goal_value = item.get('active_goal_value')
    polarity = item.get('polarity') or 'positive'
    performance = None
    if last_value is not None and goal_value not in (None, 0):
        try:
            last_num = float(last_value)
            goal_num = float(goal_value)
            if polarity == 'negative':
                performance = 100.0 if last_num == 0 else round((goal_num / last_num) * 100, 1)
            else:
                performance = round((last_num / goal_num) * 100, 1)
        except Exception:
            performance = None

    return {
        'id': item.get('id'),
        'company_id': item.get('company_id'),
        'group_id': item.get('group_id'),
        'tree_id': item.get('tree_id'),
        'full_code': item.get('full_code'),
        'code': item.get('code'),
        'name': item.get('name'),
        'description': item.get('description'),
        'indicator_type': item.get('indicator_type'),
        'source_module': item.get('source_module'),
        'source_id': item.get('source_id'),
        'collection_mode': item.get('collection_mode'),
        'aggregation_function': item.get('aggregation_function'),
        'unit': item.get('unit'),
        'polarity': item.get('polarity'),
        'formula': item.get('formula'),
        'process_id': item.get('process_id'),
        'project_id': item.get('project_id'),
        'collaborators': item.get('collaborators'),
        'data_source': item.get('data_source'),
        'notes': item.get('notes'),
        'okr_reference': item.get('okr_reference'),
        'okr_level': item.get('okr_level'),
        'is_active': item.get('is_active'),
        'created_at': item.get('created_at').isoformat() if item.get('created_at') else None,
        'updated_at': item.get('updated_at').isoformat() if item.get('updated_at') else None,
        'last_value': float(last_value) if last_value is not None else None,
        'performance': performance,
        'goals': [],
    }


def _serialize_goal_row(row):
    item = dict(row._mapping)
    return {
        'id': item.get('id'),
        'company_id': item.get('company_id'),
        'indicator_id': item.get('indicator_id'),
        'code': item.get('code'),
        'goal_value': float(item.get('goal_value')) if item.get('goal_value') is not None else None,
        'goal_date': item.get('goal_date').isoformat() if item.get('goal_date') else None,
        'period_start': item.get('period_start').isoformat() if item.get('period_start') else None,
        'period_end': item.get('period_end').isoformat() if item.get('period_end') else None,
        'responsible_id': item.get('responsible_id'),
        'status': item.get('status'),
        'notes': item.get('notes'),
        'goal_type': item.get('goal_type'),
        'evaluation_basis': item.get('evaluation_basis'),
        'created_at': item.get('created_at').isoformat() if item.get('created_at') else None,
        'updated_at': item.get('updated_at').isoformat() if item.get('updated_at') else None,
        'records': [],
    }


def _serialize_data_row(row):
    item = dict(row._mapping)
    value = item.get('value')
    record_date = item.get('record_date')
    return {
        'id': item.get('id'),
        'company_id': item.get('company_id'),
        'indicator_id': item.get('indicator_id'),
        'goal_id': item.get('goal_id'),
        'value': float(value) if value is not None else None,
        'record_date': record_date.isoformat() if record_date else None,
        'measured_value': float(value) if value is not None else None,
        'measured_date': record_date.isoformat() if record_date else None,
        'notes': item.get('notes'),
        'created_at': item.get('created_at').isoformat() if item.get('created_at') else None,
        'updated_at': item.get('updated_at').isoformat() if item.get('updated_at') else None,
    }


class IndicatorListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        company_id = get_request_company_id()
        if not company_id:
            return [], 200

        process_id = request.args.get('process_id')
        project_id = request.args.get('project_id')

        sql = """
            SELECT
                i.id,
                i.company_id,
                i.group_id,
                i.tree_id,
                i.full_code,
                i.code,
                i.name,
                i.description,
                i.indicator_type,
                i.source_module,
                i.source_id,
                i.collection_mode,
                i.aggregation_function,
                i.unit,
                i.polarity,
                i.formula,
                i.process_id,
                i.project_id,
                i.collaborators,
                i.data_source,
                i.notes,
                i.okr_reference,
                i.okr_level,
                i.is_active,
                i.created_at,
                i.updated_at,
                (
                    SELECT d.value
                    FROM indicator_data d
                    JOIN indicator_goals g ON g.id = d.goal_id
                    WHERE g.indicator_id = i.id
                      AND d.company_id = :company_id
                    ORDER BY d.record_date DESC NULLS LAST, d.id DESC
                    LIMIT 1
                ) AS last_value,
                (
                    SELECT g2.goal_value
                    FROM indicator_goals g2
                    WHERE g2.company_id = :company_id
                      AND g2.indicator_id = i.id
                      AND COALESCE(g2.status, 'active') = 'active'
                    ORDER BY g2.goal_date DESC NULLS LAST, g2.id DESC
                    LIMIT 1
                ) AS active_goal_value
            FROM indicators i
            WHERE i.company_id = :company_id
        """
        params = {'company_id': int(company_id)}
        if process_id:
            sql += " AND i.process_id = :process_id"
            params['process_id'] = int(process_id)
        if project_id:
            sql += " AND i.project_id = :project_id"
            params['project_id'] = int(project_id)
        sql += " ORDER BY i.name"

        rows = db.session.execute(text(sql), params)
        return [_serialize_indicator_row(row) for row in rows], 200

    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid

            indicator = indicator_schema.load(data)
            db.session.add(indicator)
            db.session.commit()
            return indicator_schema.dump(indicator), 201
        except ValidationError as err:
            db.session.rollback()
            return {'errors': err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


class IndicatorResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, indicator_id):
        company_id = get_request_company_id()
        sql = text(
            """
            SELECT
                i.id,
                i.company_id,
                i.group_id,
                i.tree_id,
                i.full_code,
                i.code,
                i.name,
                i.description,
                i.indicator_type,
                i.source_module,
                i.source_id,
                i.collection_mode,
                i.aggregation_function,
                i.unit,
                i.polarity,
                i.formula,
                i.process_id,
                i.project_id,
                i.collaborators,
                i.data_source,
                i.notes,
                i.okr_reference,
                i.okr_level,
                i.is_active,
                i.created_at,
                i.updated_at,
                (
                    SELECT d.value
                    FROM indicator_data d
                    JOIN indicator_goals g ON g.id = d.goal_id
                    WHERE g.indicator_id = i.id
                      AND d.company_id = i.company_id
                    ORDER BY d.record_date DESC NULLS LAST, d.id DESC
                    LIMIT 1
                ) AS last_value,
                (
                    SELECT g2.goal_value
                    FROM indicator_goals g2
                    WHERE g2.company_id = i.company_id
                      AND g2.indicator_id = i.id
                      AND COALESCE(g2.status, 'active') = 'active'
                    ORDER BY g2.goal_date DESC NULLS LAST, g2.id DESC
                    LIMIT 1
                ) AS active_goal_value
            FROM indicators i
            WHERE i.id = :indicator_id
            """
        )
        params = {'indicator_id': indicator_id}
        if company_id:
            sql = text(str(sql) + ' AND i.company_id = :company_id')
            params['company_id'] = int(company_id)
        row = db.session.execute(sql, params).first()
        if not row:
            return {'message': 'Indicator not found'}, 404
        return _serialize_indicator_row(row), 200

    @permission_required('indicators', 'edit')
    def put(self, indicator_id):
        indicator = Indicator.query.get_or_404(indicator_id)
        try:
            data = request.get_json()
            indicator = indicator_schema.load(data, instance=indicator, partial=True)
            db.session.commit()
            return indicator_schema.dump(indicator), 200
        except ValidationError as err:
            db.session.rollback()
            return {'errors': err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @permission_required('indicators', 'delete')
    def delete(self, indicator_id):
        indicator = Indicator.query.get_or_404(indicator_id)
        try:
            db.session.delete(indicator)
            db.session.commit()
            return {'message': 'Indicator deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


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
            db.session.rollback()
            return {'errors': err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


class IndicatorGoalListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        indicator_id = request.args.get('indicator_id')
        company_id = get_request_company_id()
        if not indicator_id:
            return [], 200

        rows = db.session.execute(
            text(
                """
                SELECT
                    g.id,
                    g.company_id,
                    g.indicator_id,
                    g.code,
                    g.goal_value,
                    g.goal_date,
                    g.period_start,
                    g.period_end,
                    g.responsible_id,
                    g.status,
                    g.notes,
                    g.goal_type,
                    g.evaluation_basis,
                    g.created_at,
                    g.updated_at
                FROM indicator_goals g
                WHERE g.indicator_id = :indicator_id
                  AND (:company_id IS NULL OR g.company_id = :company_id)
                ORDER BY g.goal_date DESC NULLS LAST, g.id DESC
                """
            ),
            {'indicator_id': int(indicator_id), 'company_id': int(company_id) if company_id else None}
        )
        return [_serialize_goal_row(row) for row in rows], 200

    @permission_required('indicators', 'create')
    def post(self):
        try:
            data = request.get_json()
            cid = get_request_company_id()
            if cid:
                data['company_id'] = cid

            goal = indicator_goal_schema.load(data)
            db.session.add(goal)
            db.session.commit()
            return indicator_goal_schema.dump(goal), 201
        except ValidationError as err:
            db.session.rollback()
            return {'errors': err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


class IndicatorGoalResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, goal_id):
        company_id = get_request_company_id()
        row = db.session.execute(
            text(
                """
                SELECT
                    g.id,
                    g.company_id,
                    g.indicator_id,
                    g.code,
                    g.goal_value,
                    g.goal_date,
                    g.period_start,
                    g.period_end,
                    g.responsible_id,
                    g.status,
                    g.notes,
                    g.goal_type,
                    g.evaluation_basis,
                    g.created_at,
                    g.updated_at
                FROM indicator_goals g
                WHERE g.id = :goal_id
                  AND (:company_id IS NULL OR g.company_id = :company_id)
                """
            ),
            {'goal_id': goal_id, 'company_id': int(company_id) if company_id else None}
        ).first()
        if not row:
            return {'message': 'Goal not found'}, 404
        return _serialize_goal_row(row), 200

    @permission_required('indicators', 'edit')
    def put(self, goal_id):
        goal = IndicatorGoal.query.get_or_404(goal_id)
        try:
            data = request.get_json()
            goal = indicator_goal_schema.load(data, instance=goal, partial=True)
            db.session.commit()
            return indicator_goal_schema.dump(goal), 200
        except ValidationError as err:
            db.session.rollback()
            return {'errors': err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500

    @permission_required('indicators', 'edit')
    def delete(self, goal_id):
        goal = IndicatorGoal.query.get_or_404(goal_id)
        try:
            db.session.delete(goal)
            db.session.commit()
            return {'message': 'Goal deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


class IndicatorDataListResource(Resource):
    @permission_required('indicators', 'view')
    def get(self):
        goal_id = request.args.get('goal_id')
        indicator_id = request.args.get('indicator_id')
        company_id = get_request_company_id()

        if not goal_id and not indicator_id:
            return [], 200

        sql = """
            SELECT
                d.id,
                d.company_id,
                g.indicator_id,
                d.goal_id,
                d.value,
                d.record_date,
                d.notes,
                d.created_at,
                d.updated_at
            FROM indicator_data d
            JOIN indicator_goals g ON g.id = d.goal_id
            WHERE (:company_id IS NULL OR d.company_id = :company_id)
        """
        params = {'company_id': int(company_id) if company_id else None}
        if goal_id:
            sql += ' AND d.goal_id = :goal_id'
            params['goal_id'] = int(goal_id)
        elif indicator_id:
            sql += ' AND g.indicator_id = :indicator_id'
            params['indicator_id'] = int(indicator_id)
        sql += ' ORDER BY d.record_date DESC NULLS LAST, d.id DESC'

        rows = db.session.execute(text(sql), params)
        return [_serialize_data_row(row) for row in rows], 200

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
            return indicator_data_schema.dump(record), 201
        except ValidationError as err:
            db.session.rollback()
            return {'errors': err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500


class IndicatorDataResource(Resource):
    @permission_required('indicators', 'view')
    def get(self, data_id):
        company_id = get_request_company_id()
        row = db.session.execute(
            text(
                """
                SELECT
                    d.id,
                    d.company_id,
                    g.indicator_id,
                    d.goal_id,
                    d.value,
                    d.record_date,
                    d.notes,
                    d.created_at,
                    d.updated_at
                FROM indicator_data d
                JOIN indicator_goals g ON g.id = d.goal_id
                WHERE d.id = :data_id
                  AND (:company_id IS NULL OR d.company_id = :company_id)
                """
            ),
            {'data_id': data_id, 'company_id': int(company_id) if company_id else None}
        ).first()
        if not row:
            return {'message': 'Data record not found'}, 404
        return _serialize_data_row(row), 200

    @permission_required('indicators', 'edit')
    def delete(self, data_id):
        record = IndicatorData.query.get_or_404(data_id)
        try:
            db.session.delete(record)
            db.session.commit()
            return {'message': 'Data record deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'error': str(e)}, 500
