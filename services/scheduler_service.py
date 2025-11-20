#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduler Service - Gerenciamento de tarefas agendadas
Utiliza APScheduler para executar rotinas automaticamente
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerService:
    """Serviço de agendamento de tarefas"""

    def __init__(self):
        """Inicializa o scheduler"""
        self.scheduler = BackgroundScheduler(
            {
                "apscheduler.timezone": "America/Sao_Paulo",
                "apscheduler.job_defaults.coalesce": True,
                "apscheduler.job_defaults.max_instances": 1,
            }
        )
        self.is_running = False
        logger.info("📅 Scheduler Service inicializado")

    def start(self):
        """Inicia o scheduler"""
        if not self.is_running:
            try:
                self.scheduler.start()
                self.is_running = True
                logger.info("✅ Scheduler iniciado com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao iniciar scheduler: {e}")
                raise

    def stop(self):
        """Para o scheduler"""
        if self.is_running:
            try:
                self.scheduler.shutdown(wait=False)
                self.is_running = False
                logger.info("⏹️ Scheduler parado")
            except Exception as e:
                logger.error(f"❌ Erro ao parar scheduler: {e}")

    def add_job(self, func, trigger, job_id, **trigger_args):
        """
        Adiciona um job ao scheduler

        Args:
            func: Função a ser executada
            trigger: Tipo de trigger ('cron', 'interval', 'date')
            job_id: ID único do job
            **trigger_args: Argumentos do trigger (hour, minute, day, etc.)
        """
        try:
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                **trigger_args,
            )
            logger.info(f"✅ Job '{job_id}' adicionado: {trigger} {trigger_args}")
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar job '{job_id}': {e}")
            raise

    def remove_job(self, job_id):
        """Remove um job do scheduler"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"🗑️ Job '{job_id}' removido")
        except Exception as e:
            logger.warning(f"⚠️ Job '{job_id}' não encontrado: {e}")

    def list_jobs(self):
        """Lista todos os jobs agendados"""
        jobs = self.scheduler.get_jobs()
        logger.info(f"📋 Jobs agendados: {len(jobs)}")
        for job in jobs:
            logger.info(f"  - {job.id}: próxima execução em {job.next_run_time}")
        return jobs


# Instância global do scheduler
scheduler_service = SchedulerService()


def process_daily_routines():
    """
    Processa todas as rotinas diárias
    Esta função é executada pelo scheduler
    """
    logger.info("=" * 80)
    logger.info(f"🔄 Iniciando processamento de rotinas - {datetime.now()}")
    logger.info("=" * 80)

    try:
        # Importar aqui para evitar circular import
        from routine_scheduler import process_routines

        # Executar o processamento de rotinas
        success = process_routines()

        if success:
            logger.info("✅ Processamento de rotinas concluído com sucesso!")
        else:
            logger.error("❌ Erro no processamento de rotinas")

    except Exception as e:
        logger.error(f"❌ Erro ao processar rotinas: {e}")
        import traceback

        traceback.print_exc()


def setup_routine_jobs():
    """
    Configura os jobs de rotina no scheduler
    """
    logger.info("🔧 Configurando jobs de rotina...")

    # Job 1: Processar rotinas diárias às 00:01
    scheduler_service.add_job(
        func=process_daily_routines,
        trigger="cron",
        job_id="process_daily_routines",
        hour=0,
        minute=1,
        name="Processamento Diário de Rotinas",
    )

    # Job 2: Verificar tarefas atrasadas a cada hora
    scheduler_service.add_job(
        func=check_overdue_tasks,
        trigger="cron",
        job_id="check_overdue_tasks",
        minute=0,  # A cada hora cheia
        name="Verificação de Tarefas Atrasadas",
    )

    logger.info("✅ Jobs de rotina configurados!")


def check_overdue_tasks():
    """
    Verifica e atualiza status de tarefas atrasadas
    Executado a cada hora
    """
    logger.info("⏰ Verificando tarefas atrasadas...")

    try:
        # Importar aqui para evitar circular import
        from routine_scheduler import update_overdue_tasks

        update_overdue_tasks()
        logger.info("✅ Verificação de tarefas concluída!")

    except Exception as e:
        logger.error(f"❌ Erro ao verificar tarefas: {e}")


def initialize_scheduler():
    """
    Inicializa o scheduler com todos os jobs configurados
    Deve ser chamado no startup da aplicação
    """
    logger.info("🚀 Inicializando Scheduler Service...")

    try:
        # Configurar jobs
        setup_routine_jobs()

        # Iniciar scheduler
        scheduler_service.start()

        # Listar jobs configurados
        scheduler_service.list_jobs()

        logger.info("=" * 80)
        logger.info("✅ SCHEDULER ATIVO E FUNCIONANDO!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Erro ao inicializar scheduler: {e}")
        raise


def shutdown_scheduler():
    """
    Para o scheduler de forma segura
    Deve ser chamado no shutdown da aplicação
    """
    logger.info("🛑 Desligando scheduler...")
    scheduler_service.stop()


# Para usar no Flask
def get_scheduler():
    """Retorna a instância do scheduler"""
    return scheduler_service
