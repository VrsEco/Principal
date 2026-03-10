
import paramiko

def test_conn():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect("ip-69-164-205-75.cloudezapp.io", port=22122, username="app", password="*Paraiso1978")
        print("SUCCESS")
        ssh.close()
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_conn()
