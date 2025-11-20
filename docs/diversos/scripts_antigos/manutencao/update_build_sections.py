from pathlib import Path

path = Path(r"relatorios/generators/process_pop.py")
text = path.read_text(encoding="utf-8")
old = "        # 1. Seção de Informações Gerais\n        self._add_info_section()\n        \n        # 2. Seção de Fluxo (se incluído)\n        if self.include_flow:\n            self._add_flow_section()\n        \n        # 3. Seção de Atividades (se incluído)\n        if self.include_activities:\n            self._add_activities_section()\n        \n        # 4. Seção de Rotinas (se incluído)\n        if self.include_routines:\n            self._add_routines_section()\n        \n        # 5. Seção de Indicadores (se incluído)"
if old not in text:
    old = old.replace("\n", "\r\n")
new = "        # 1. Seção de Fluxo (se incluído)\n        if self.include_flow:\n            self._add_flow_section()\n        \n        # 2. Seção de Atividades (se incluído)\n        if self.include_activities:\n            self._add_activities_section()\n        \n        # 3. Seção de Rotinas (se incluído)\n        if self.include_routines:\n            self._add_routines_section()\n        \n        # 4. Seção de Indicadores (se incluído)"
if old not in text:
    raise SystemExit("build_sections block not found")
path.write_text(text.replace(old, new), encoding="utf-8")
