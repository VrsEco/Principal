from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.deploy.configr_remote_helper import APP_DIR, BASE_DIR as REMOTE_BASE_DIR, WWW_DIR, connect_ssh, run_command


def final_deploy() -> int:
    print("📡 Conectando ao servidor de produção com chave SSH...")
    ssh = connect_ssh()
    try:
        commands = [
            f"cd {APP_DIR} && git fetch origin main",
            f"cd {APP_DIR} && git reset --hard origin/main",
            f"cd {APP_DIR} && git clean -fd",
            f"cd {APP_DIR} && chmod +x scripts/deploy_configr.sh && bash scripts/deploy_configr.sh",
        ]

        final_status = 0
        for command in commands:
            print(f"\n[RUN] {command}")
            code, stdout, stderr = run_command(ssh, command, get_pty=True)
            if stdout.strip():
                print(stdout.strip())
            if stderr.strip():
                print("[STDERR]")
                print(stderr.strip())
            if code != 0:
                final_status = code
                break

        if final_status != 0:
            print(f"\n❌ Deploy interrompido com status {final_status}.")
            return final_status

        health_commands = [
            f"test -f {WWW_DIR}/restart.txt && echo restart-ok || echo restart-missing",
            f"cd {APP_DIR} && git log -n 1 --oneline",
        ]
        for command in health_commands:
            print(f"\n[CHECK] {command}")
            code, stdout, stderr = run_command(ssh, command)
            if stdout.strip():
                print(stdout.strip())
            if stderr.strip():
                print("[STDERR]")
                print(stderr.strip())
            if code != 0:
                return code

        print("\n✨ DEPLOY FINALIZADO COM SUCESSO.")
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(final_deploy())
