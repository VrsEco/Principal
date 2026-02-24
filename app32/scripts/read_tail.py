import sys

with open("backups/uwsgi_app_latest.log", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
    with open("backups/tail_out.txt", "w", encoding="utf-8") as out:
        for line in lines[-150:]:
            out.write(line)
