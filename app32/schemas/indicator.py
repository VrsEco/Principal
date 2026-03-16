from marshmallow import fields
from . import ma
from models.indicator import IndicatorGroup, Indicator, IndicatorGoal, IndicatorData

class IndicatorDataSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = IndicatorData
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    # Mapeamentos para compatibilidade com o modelo real
    measured_value = fields.Float(required=True)
    measured_date = fields.Date(required=True)
    routine_id = fields.Integer(allow_none=True)
    
    # Campo legacy de visual/payload, mapeado para measured_value se necessário
    value = fields.Float(load_only=True)

class IndicatorGoalSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = IndicatorGoal
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    code = fields.String()
    
    goal_value = fields.Float()
    period_start = fields.Date()
    goal_date = fields.Date(allow_none=True)
    performance_ranges = fields.Dict(allow_none=True)
    routine_id = fields.Integer(allow_none=True)
    collection_method = fields.String(allow_none=True)
    
    records = fields.Nested(IndicatorDataSchema, many=True, dump_only=True)

class IndicatorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Indicator
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    routine_id = fields.Integer(allow_none=True)
    
    goals = fields.Nested(IndicatorGoalSchema, many=True, dump_only=True)
    
    last_value = fields.Method("get_last_value", dump_only=True)
    performance = fields.Method("get_performance", dump_only=True)

    def get_last_value(self, obj):
        # Get the most recent measured value for this indicator
        from sqlalchemy import desc
        last_data = IndicatorData.query.filter_by(
            indicator_id=obj.id
        ).order_by(desc('measured_date')).first()
        
        if not last_data:
            return None
        return float(last_data.measured_value)

    def get_performance(self, obj):
        # Comparison logic: last measured value vs active goal
        from sqlalchemy import desc
        active_goal = IndicatorGoal.query.filter_by(indicator_id=obj.id, status='active').order_by(desc('goal_date')).first()
        if not active_goal:
            return None
            
        last_val = self.get_last_value(obj)
        if last_val is None:
            return None
            
        goal_val = float(active_goal.goal_value)
        if goal_val == 0:
            return 0
            
        # Polarity check
        if hasattr(obj, 'polarity') and obj.polarity == 'negative':
             if last_val == 0: return 100.0
             return round((goal_val / last_val) * 100, 1) if last_val > 0 else 0.0
             
        return round((last_val / goal_val) * 100, 1)


class IndicatorGroupSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = IndicatorGroup
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    indicators = fields.Nested(IndicatorSchema, many=True, dump_only=True)

# Instances for easy import
indicator_schema = IndicatorSchema()
indicators_schema = IndicatorSchema(many=True)
indicator_group_schema = IndicatorGroupSchema()
indicator_groups_schema = IndicatorGroupSchema(many=True)
indicator_goal_schema = IndicatorGoalSchema()
indicator_goals_schema = IndicatorGoalSchema(many=True)
indicator_data_schema = IndicatorDataSchema()
indicator_data_list_schema = IndicatorDataSchema(many=True)
