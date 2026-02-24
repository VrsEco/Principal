import socket
import sys

def check_ports(host, ports):
    print(f"Checking ports on {host}...")
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("69.164.205.75", port))
            if result == 0:
                print(f"Port {port} is OPEN (IPv4)")
            sock.close()
        except:
            pass

if __name__ == "__main__":
    host = "ip-69-164-205-75.cloudezapp.io"
    ports = [22, 21, 22122, 2222, 1022, 2022, 2200, 2201, 2202, 10022, 22022, 30022, 222, 443, 80]
    check_ports(host, ports)
