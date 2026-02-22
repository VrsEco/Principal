from marshmallow import fields
from . import ma
from models.indicator import Indicator, IndicatorGroup, IndicatorGoal, IndicatorData

class IndicatorDataSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = IndicatorData
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    value = fields.Float()

class IndicatorGoalSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = IndicatorGoal
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    goal_value = fields.Float()
    
    records = fields.Nested(IndicatorDataSchema, many=True, dump_only=True)

class IndicatorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Indicator
        load_instance = True
        include_fk = True
    
    created_at = fields.String(dump_only=True)
    updated_at = fields.String(dump_only=True)
    
    goals = fields.Nested(IndicatorGoalSchema, many=True, dump_only=True)
    
    last_value = fields.Method("get_last_value", dump_only=True)
    performance = fields.Method("get_performance", dump_only=True)

    def get_last_value(self, obj):
        # Get the most recent record across all goals
        all_records = []
        for goal in obj.goals:
            all_records.extend(goal.records.all())
        
        if not all_records:
            return None
            
        # Sort by date descending
        all_records.sort(key=lambda r: r.record_date, reverse=True)
        return float(all_records[0].value)

    def get_performance(self, obj):
        # Get last record and active goal
        active_goal = obj.goals.filter_by(status='active').first()
        if not active_goal:
            return None
            
        last_val = self.get_last_value(obj)
        if last_val is None:
            return None
            
        goal_val = float(active_goal.goal_value)
        if goal_val == 0:
            return 0
            
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
