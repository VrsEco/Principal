from pathlib import Path

path = Path(r"relatorios/generators/process_pop.py")
text = path.read_text(encoding="utf-8")
print(text[540:760])
