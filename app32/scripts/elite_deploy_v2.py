
import paramiko
import time

HOST = "ip-69-164-205-75.cloudezapp.io"
PORT = 22122
USER = "app2"
PASS = "*Paraiso1978"

def deploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"📡 Conectando ao servidor {HOST}...")
        ssh.connect(HOST, port=PORT, username=USER, password=PASS)
        print("✅ Conectado ao servidor.")

        # Comando principal de deploy atômico (conforme Skill)
        # 1. Forçar sincronia do repositório
        # 2. Executar script oficial de deploy Configr
        cmd = "cd /home/app2/public_html/app32 && git fetch origin main && git reset --hard origin/main && bash scripts/deploy_configr.sh"
        
        print(f"🚀 Executando deploy atômico no servidor...")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Read output line by line to show progress
        for line in stdout:
            print(f"[SERVER]: {line.strip()}")
            
        for line in stderr:
            print(f"[SERVER ERR]: {line.strip()}")
            
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("\n✨ DEPLOY REALIZADO COM SUCESSO! Sistema atualizado na produção.")
        else:
            print(f"\n❌ ERRO NO DEPLOY: O comando encerrou com status {exit_status}.")
            
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO NA CONEXÃO SSH: {str(e)}")
    finally:
        ssh.close()

if __name__ == "__main__":
    deploy()
