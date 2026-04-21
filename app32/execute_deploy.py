from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scripts.deploy.configr_remote_helper import APP_DIR, DEPLOY_SCRIPT, HOST, PORT, USER, connect_ssh


def main() -> int:
    print(f"📡 Conectando ao servidor {HOST}:{PORT} como {USER}...")
    ssh = connect_ssh()
    try:
        print(f"🚀 Executando deploy oficial: {DEPLOY_SCRIPT}")
        stdin, stdout, stderr = ssh.exec_command(
            f"cd {APP_DIR} && chmod +x scripts/deploy_configr.sh && bash {DEPLOY_SCRIPT}",
            get_pty=True,
        )
        for line in iter(lambda: stdout.readline(2048), ""):
            if not line:
                break
            print(line.rstrip())

        err = stderr.read().decode("utf-8", "ignore").strip()
        exit_code = stdout.channel.recv_exit_status()
        if err:
            print("\n[STDERR]")
            print(err)
        print(f"\n[EXIT_CODE]={exit_code}")
        return exit_code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
