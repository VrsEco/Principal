from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.deploy.configr_remote_helper import APP_DIR, HOST, PORT, USER, connect_ssh, run_command


def run_ssh_commands(commands: list[str]) -> int:
    print(f"📡 Conectando ao servidor {HOST}:{PORT} como {USER}...")
    ssh = connect_ssh()
    try:
        for cmd in commands:
            full_cmd = f"cd {APP_DIR} && {cmd}"
            print(f"\n>>> {full_cmd}")
            code, out, err = run_command(ssh, full_cmd)
            if out:
                print(out.strip())
            if err:
                print(err.strip())
            print(f"[EXIT_CODE]={code}")
            if code != 0:
                return code
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(
        run_ssh_commands(
            [
                "whoami",
                "pwd",
                "git rev-parse --short HEAD",
                "git status --short",
            ]
        )
    )
