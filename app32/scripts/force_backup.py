import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('ip-69-164-205-75.cloudezapp.io', 22122, 'app2', '*Paraiso1978')
cmd = 'mkdir -p /home/app2/backups && pg_dump -U mff2000 bd_app_versus > /home/app2/backups/manual_test_backup.sql && gzip -f /home/app2/backups/manual_test_backup.sql'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
