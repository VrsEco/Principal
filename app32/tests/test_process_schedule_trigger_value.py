import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.resources import process as process_resource


def test_format_schedule_trigger_value_for_monthly_uses_day_of_month_label():
    assert process_resource._format_schedule_trigger_value('monthly', '20', '00:01') == 'Dia 20'


def test_format_schedule_trigger_value_for_quarterly_uses_month_and_day():
    assert process_resource._format_schedule_trigger_value('quarterly', '2-15', '00:01') == 'Mês 2 do tri · Dia 15'


def test_format_schedule_trigger_value_for_yearly_formats_dd_mm():
    assert process_resource._format_schedule_trigger_value('yearly', '5/12', '00:01') == '05/12'


def test_format_schedule_trigger_value_for_daily_prefers_start_time():
    assert process_resource._format_schedule_trigger_value('daily', '', '08:30') == '08:30'
