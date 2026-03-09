"""Script de deploy remoto usando Paramiko no ambiente produtivo Configr."""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.deploy.configr_remote_helper import APP_DIR, DEPLOY_SCRIPT, HOST, PORT, USER, connect_ssh


def main() -> int:
    print("=" * 60)
    print("  DEPLOY REMOTO - Gestão Versus (Configr)")
    print("=" * 60)
    print(f"\n🔌 Conectando a {HOST}:{PORT} como {USER}...")

    ssh = connect_ssh()
    try:
        print("  ✅ Conectado!")
        cmd = f"cd {APP_DIR} && chmod +x scripts/deploy_configr.sh && bash {DEPLOY_SCRIPT}"
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)

        for line in iter(lambda: stdout.readline(2048), ""):
            if not line:
                break
            print(line.rstrip())

        err = stderr.read().decode("utf-8", "ignore").strip()
        code = stdout.channel.recv_exit_status()
        if err:
            print("[STDERR]")
            print(err)

        if code == 0:
            print("\n" + "=" * 60)
            print("  ✨ DEPLOY CONCLUÍDO COM SUCESSO!")
            print("  🌐 Acesse: https://app.gestaoversus.com.br")
            print("=" * 60)
        else:
            print(f"\n❌ Deploy falhou com status {code}.")
        return code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
