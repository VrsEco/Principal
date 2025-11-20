from pathlib import Path

app_path = Path(r"c:\GestaoVersus\pev_app_2_0\app.py")
text = app_path.read_text(encoding="utf-8")
block = '        "company_data": {\n            "trade_name": "Alimentos Tia Sonia",\n            "legal_name": "Alimentos Tia Sonia LTDA",\n            "cnpj": "12.345.678/0001-90",\n            "coverage": "regional",\n            "experience_total": "12 anos",\n            "experience_segment": "8 anos",\n            "cnaes": ["1091-1/01 Fabricacao de produtos de panificacao", "4721-1/02 Comercio varejista de produtos alimenticios"],\n'
new = '        "company_data": {\n            "trade_name": "Alimentos Tia Sonia",\n            "legal_name": "Alimentos Tia Sonia LTDA",\n            "cnpj": "12.345.678/0001-90",\n            "coverage": {\n                "physical": "regional",\n                "online": "internet-nacional"\n            },\n            "experience_total": "12 anos",\n            "experience_segment": "8 anos",\n            "cnaes": ["1091-1/01 Fabricacao de produtos de panificacao", "4721-1/02 Comercio varejista de produtos alimenticios"],\n'
if block in text:
    text = text.replace(block, new)
app_path.write_text(text, encoding="utf-8")
