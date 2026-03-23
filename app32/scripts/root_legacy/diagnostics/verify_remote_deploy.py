from __future__ import annotations

from scripts.deploy.configr_remote_helper import APP_DIR, connect_ssh, run_command


def main() -> int:
    command = f"cd {APP_DIR} && git log -n 1 --oneline"
    print(f"📡 Validando deploy remoto em: {APP_DIR}")

    ssh = connect_ssh()
    try:
        exit_code, stdout, stderr = run_command(ssh, command)
    finally:
        ssh.close()

    print("--- STDOUT ---")
    print(stdout.strip())
    print("--- STDERR ---")
    print(stderr.strip())
    print(f"Exit Code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
