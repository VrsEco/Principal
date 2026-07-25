from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scheduler_runner_disables_web_bootstrap_and_publishes_heartbeat():
    runner = (ROOT / "scripts" / "run_scheduler.py").read_text(encoding="utf-8")

    assert 'os.environ["APP_BOOTSTRAP_RUNTIME_SERVICES"] = "0"' in runner
    assert 'Flask("app32_scheduler")' in runner
    assert "from app import create_app" not in runner
    assert "initialize_scheduler(app)" in runner
    assert "scheduler_heartbeat.json" in runner
    assert "fcntl.LOCK_EX | fcntl.LOCK_NB" in runner


def test_scheduler_manager_has_pid_lock_and_health_contract():
    manager = (ROOT / "scripts" / "manage_scheduler.sh").read_text(encoding="utf-8")

    assert 'PID_FILE="$TMP_DIR/scheduler_runtime.pid"' in manager
    assert 'MANAGER_LOCK_DIR="$TMP_DIR/scheduler_manager.lock"' in manager
    assert 'HEARTBEAT_FILE="$TMP_DIR/scheduler_heartbeat.json"' in manager
    assert "run_scheduler.py" in manager
    assert "start|stop|restart|status|health" in manager


def test_deploy_restarts_and_validates_dedicated_scheduler():
    deploy = (ROOT / "scripts" / "deploy_configr.sh").read_text(encoding="utf-8")

    assert 'bash "$APP/scripts/manage_scheduler.sh" restart' in deploy
    assert 'bash "$APP/scripts/manage_scheduler.sh" health' in deploy
    assert "APP_BOOTSTRAP_RUNTIME_SERVICES=0" in deploy


def test_morning_summary_runs_only_on_weekdays_at_eight():
    scheduler = (ROOT / "services" / "scheduler_service.py").read_text(encoding="utf-8")
    job_block = scheduler.split('job_id="proactive_morning_summary"', 1)[1].split(
        'logger.info("✅ Jobs proativos configurados!")',
        1,
    )[0]

    assert 'day_of_week="mon-fri"' in job_block
    assert "hour=8" in job_block
    assert "minute=0" in job_block


def test_proactive_service_does_not_load_ai_telegram_webhook_at_bootstrap():
    proactive = (ROOT / "services" / "proactive_service.py").read_text(encoding="utf-8")
    eager_imports = proactive.split("logger = logging.getLogger", 1)[0]

    assert "api.webhooks.telegram_webhook" not in eager_imports
    assert "from api.webhooks.telegram_webhook import bot" in proactive
