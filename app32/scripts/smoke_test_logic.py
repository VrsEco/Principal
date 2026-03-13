import os
import unittest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import date, timedelta
from decimal import Decimal

# Mocking the minimal environment for Logic Test without full DB dependency
class MinimalIncentiveService:
    @staticmethod
    def calculate(base_salary, realized, target, weight, impact_type):
        achievement = (realized / target) if target > 0 else Decimal('0.00')
        accumulated = base_salary
        
        if impact_type == 'individual':
            accumulated *= (weight * achievement)
        elif impact_type == 'multiplier':
            accumulated *= achievement
        elif impact_type == 'reducer':
            factor = Decimal('1.00') - (achievement * weight)
            accumulated *= max(Decimal('0.00'), factor)
            
        return max(Decimal('0.00'), accumulated - base_salary)

class IncentiveLogicSmokeTest(unittest.TestCase):
    def test_calculation_mathematics(self):
        """Validar se a lógica matemática de bônus está correta (Individual)"""
        base = Decimal('1000.00')
        # Meta 100, Realizado 120 -> 120% achievement. Peso 1.0.
        # 1000 * 1.2 = 1200. Bônus = 200.
        bonus = MinimalIncentiveService.calculate(base, Decimal('120'), Decimal('100'), Decimal('1.0'), 'individual')
        self.assertEqual(bonus, Decimal('200.00'))

    def test_reducer_mathematics(self):
        """Validar lógica de redutor de risco"""
        base = Decimal('1000.00')
        # Meta de erros = 1. Realizado 2 erros -> 200% achievement no erro.
        # Peso do redutor 0.1 (10% por 'unidade' de meta atingida negativa)
        # Fator = 1.0 - (2.0 * 0.1) = 0.8
        # 1000 * 0.8 = 800. Bônus = 0 (pois ficou abaixo do base)
        bonus = MinimalIncentiveService.calculate(base, Decimal('2'), Decimal('1'), Decimal('0.1'), 'reducer')
        self.assertEqual(bonus, Decimal('0.00'))
        
    def test_multiplier_mathematics(self):
        """Validar multiplicador global"""
        base = Decimal('1000.00')
        # Meta batida em 150%
        bonus = MinimalIncentiveService.calculate(base, Decimal('150'), Decimal('100'), Decimal('1.0'), 'multiplier')
        self.assertEqual(bonus, Decimal('500.00'))

if __name__ == '__main__':
    print("Iniciando Smoke Test Logístico (Arquitetura Matemática)...")
    unittest.main()
