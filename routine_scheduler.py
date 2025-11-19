#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Routine Scheduler - Processamento diário de rotinas
Este script deve ser executado diariamente às 00:01 para criar as tarefas baseadas nos gatilhos configurados
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import calendar

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_database import get_db

db = get_db()


def get_weekday_name(date: datetime) -> str:
    """Get the weekday name in lowercase"""
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return weekdays[date.weekday()]


def should_trigger_daily(trigger_value: str, current_time: datetime) -> bool:
    """Check if a daily trigger should fire"""
    # trigger_value format: "HH:MM"
    try:
        hour, minute = map(int, trigger_value.split(':'))
        return current_time.hour == hour and current_time.minute <= 1
    except:
        return False


def should_trigger_weekly(trigger_value: str, current_date: datetime) -> bool:
    """Check if a weekly trigger should fire"""
    # trigger_value format: "monday", "tuesday", etc.
    return get_weekday_name(current_date) == trigger_value.lower()


def should_trigger_monthly(trigger_value: str, current_date: datetime) -> bool:
    """Check if a monthly trigger should fire"""
    # trigger_value format: "01", "02", "15", etc.
    try:
        day = int(trigger_value)
        return current_date.day == day
    except:
        return False


def should_trigger_yearly(trigger_value: str, current_date: datetime) -> bool:
    """Check if a yearly trigger should fire"""
    # trigger_value format: "DD/MM"
    try:
        day, month = map(int, trigger_value.split('/'))
        return current_date.day == day and current_date.month == month
    except:
        return False


def calculate_deadline(deadline_value: int, deadline_unit: str, scheduled_date: datetime) -> datetime:
    """Calculate the deadline date based on the trigger time"""
    if deadline_unit == 'hours':
        return scheduled_date + timedelta(hours=deadline_value)
    elif deadline_unit == 'days':
        return scheduled_date + timedelta(days=deadline_value)
    else:
        return scheduled_date + timedelta(days=1)


def process_trigger(routine: Dict[str, Any], trigger: Dict[str, Any], current_time: datetime) -> bool:
    """
    Process a single trigger and create a task if it should fire
    Returns True if a task was created
    """
    trigger_type = trigger['trigger_type']
    trigger_value = trigger['trigger_value']
    
    should_fire = False
    
    if trigger_type == 'daily':
        should_fire = should_trigger_daily(trigger_value, current_time)
    elif trigger_type == 'weekly':
        should_fire = should_trigger_weekly(trigger_value, current_time)
    elif trigger_type == 'monthly':
        should_fire = should_trigger_monthly(trigger_value, current_time)
    elif trigger_type == 'yearly':
        should_fire = should_trigger_yearly(trigger_value, current_time)
    
    if should_fire:
        # Create the task
        scheduled_date = current_time.strftime('%Y-%m-%d %H:%M:%S')
        deadline_date = calculate_deadline(
            trigger['deadline_value'],
            trigger['deadline_unit'],
            current_time
        ).strftime('%Y-%m-%d %H:%M:%S')
        
        title = f"{routine['name']}"
        description = routine.get('description', '')
        
        task_id = db.create_routine_task(
            routine['id'],
            trigger['id'],
            title,
            description,
            scheduled_date,
            deadline_date
        )
        
        if task_id:
            print(f"✓ Tarefa criada: {title} (ID: {task_id}) - Prazo: {deadline_date}")
            return True
        else:
            print(f"✗ Erro ao criar tarefa: {title}")
            return False
    
    return False


def update_overdue_tasks():
    """Update status of overdue tasks"""
    try:
        # Get all companies
        companies = db.get_companies()
        
        for company in companies:
            company_id = company['id']
            
            # Get all pending/in_progress tasks
            pending_tasks = db.get_routine_tasks(company_id, 'pending')
            in_progress_tasks = db.get_routine_tasks(company_id, 'in_progress')
            
            all_tasks = pending_tasks + in_progress_tasks
            current_time = datetime.now()
            
            for task in all_tasks:
                deadline = datetime.strptime(task['deadline_date'], '%Y-%m-%d %H:%M:%S')
                
                if current_time > deadline:
                    # Mark as overdue
                    db.update_routine_task_status(task['id'], 'overdue')
                    print(f"⚠ Tarefa atrasada: {task['title']} (ID: {task['id']})")
        
        print(f"✓ Verificação de tarefas atrasadas concluída")
    
    except Exception as e:
        print(f"✗ Erro ao verificar tarefas atrasadas: {e}")


def process_routines():
    """Main function to process all routines"""
    print("=" * 80)
    print(f"Iniciando processamento de rotinas - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Get all companies
        companies = db.get_companies()
        
        total_tasks_created = 0
        total_routines_processed = 0
        
        for company in companies:
            company_id = company['id']
            company_name = company.get('name') or company.get('legal_name') or f"Empresa {company_id}"
            
            print(f"\n📊 Processando empresa: {company_name} (ID: {company_id})")
            
            # Get all active routines for this company
            routines = db.get_routines(company_id)
            
            if not routines:
                print(f"   Nenhuma rotina ativa encontrada")
                continue
            
            for routine in routines:
                total_routines_processed += 1
                print(f"\n   📋 Rotina: {routine['name']} (ID: {routine['id']})")
                
                # Get all active triggers for this routine
                triggers = db.get_routine_triggers(routine['id'])
                
                if not triggers:
                    print(f"      Nenhum gatilho configurado")
                    continue
                
                # Process each trigger
                current_time = datetime.now()
                
                for trigger in triggers:
                    if process_trigger(routine, trigger, current_time):
                        total_tasks_created += 1
        
        print("\n" + "=" * 80)
        print(f"✓ Processamento concluído!")
        print(f"  - Empresas processadas: {len(companies)}")
        print(f"  - Rotinas processadas: {total_routines_processed}")
        print(f"  - Tarefas criadas: {total_tasks_created}")
        print("=" * 80)
        
        # Update overdue tasks
        print("\n📅 Verificando tarefas atrasadas...")
        update_overdue_tasks()
        
        return True
        
    except Exception as e:
        print(f"\n✗ Erro durante o processamento: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # Initialize the database (create tables if they don't exist)
    db.initialize_database()
    
    # Run the routine processor
    success = process_routines()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)



