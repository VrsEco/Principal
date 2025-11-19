import sys
from pathlib import Path
paths = [Path(r"C:/GestaoVersus/Referencias/recuperacao_28out/dados_docker_28out/base/16384"),
         Path(r"C:/GestaoVersus/Referencias/recuperacao_28out/dados_docker_28out/base/16389")]
for base in paths:
    print(f"== Searching {base} ==")
    for file in sorted(base.iterdir()):
        if file.is_file():
            try:
                data = file.read_bytes()
            except Exception as exc:
                print(f"   [skip] {file.name} ({exc})")
                continue
            idx = data.find(b"EUA")
            if idx == -1:
                continue
            print(f"  File: {file.name}")
            count = 0
            while idx != -1 and count < 10:
                start = max(idx - 120, 0)
                end = min(idx + 120, len(data))
                snippet = data[start:end]
                text = snippet.decode('utf-8', 'ignore')
                print(f"    ...{text}...")
                count += 1
                idx = data.find(b"EUA", idx + 3)
            if idx != -1:
                print("    [more matches omitted]")
