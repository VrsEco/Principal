from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.deploy.configr_remote_helper import APP_DIR, DEPLOY_SCRIPT, HOST, PORT, USER, connect_ssh


def deploy() -> int:
    print(f"📡 Conectando ao servidor {HOST}:{PORT} como {USER}...")
    ssh = connect_ssh()
    try:
        print(f"🚀 Executando deploy atômico no path produtivo: {APP_DIR}")
        stdin, stdout, stderr = ssh.exec_command(
            f"cd {APP_DIR} && chmod +x scripts/deploy_configr.sh && bash {DEPLOY_SCRIPT}",
            get_pty=True,
        )

        for line in iter(lambda: stdout.readline(2048), ""):
            if not line:
                break
            print(f"[SERVER] {line.rstrip()}")

        err = stderr.read().decode("utf-8", "ignore").strip()
        exit_status = stdout.channel.recv_exit_status()
        if err:
            print("\n[SERVER ERR]")
            print(err)

        if exit_status == 0:
            print("\n✨ DEPLOY REALIZADO COM SUCESSO! Sistema atualizado na produção.")
        else:
            print(f"\n❌ ERRO NO DEPLOY: comando retornou status {exit_status}.")
        return exit_status
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(deploy())
