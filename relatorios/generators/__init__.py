#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Geradores de Relatórios
Sistema PEVAPP22

Importações facilitadas para uso nos relatórios
"""

from .base import BaseReportGenerator
from .process_pop import ProcessPOPReport, generate_process_pop_report
from .my_work_report import MyWorkReport

__all__ = [
    "BaseReportGenerator",
    "ProcessPOPReport",
    "generate_process_pop_report",
    "MyWorkReport",
]
