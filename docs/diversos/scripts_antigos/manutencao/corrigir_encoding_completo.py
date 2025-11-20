#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para corrigir encoding de caracteres especiais no template
"""

import re

# Mapeamento de caracteres com encoding errado para correto
REPLACEMENTS = {
    # Letras com acento
    "Ã§": "ç",
    "Ã£": "ã",
    "Ã­": "í",
    "Ãµ": "õ",
    "Ã¡": "á",
    "Ã©": "é",
    "ÃŠ": "ê",
    "Ã³": "ó",
    "Ãº": "ú",
    "Ã": "à",
    "Ã¢": "â",
    # Palavras comuns com problema
    "ContribuiÃ§Ã£o": "Contribuição",
    "DestinaÃ§Ãµes": "Destinações",
    "PerÃ­odo": "Período",
    "AnÃ¡lise": "Análise",
    "VariÃ¡vel": "Variável",
    "MǸtricas": "Métricas",
    "DistribuiÃ§Ã£o": "Distribuição",
    "negÃ³cio": "negócio",
    "AutomÃ¡ticos": "Automáticos",
    "ExecuÃ§Ã£o": "Execução",
    "cÃ¡lculo": "cálculo",
    "mÃªs": "mês",
    # Símbolos
    "â†’": "→",
    "â„¹ï¸": "ℹ️",
    "ðŸ’°": "💰",
    "ðŸ“Š": "📊",
    "ðŸŽ¯": "🎯",
    "ðŸ“¦": "📦",
    "ðŸ—ï¸": "🏗️",
    "ðŸ’Ž": "💎",
}


def fix_encoding(file_path):
    """Corrige encoding no arquivo"""
    print(f"Corrigindo encoding em: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    replacements_made = 0

    # Aplicar todas as correções
    for wrong, correct in REPLACEMENTS.items():
        if wrong in content:
            count = content.count(wrong)
            content = content.replace(wrong, correct)
            replacements_made += count
            print(f"  Corrigido '{wrong}' -> '{correct}' ({count} vezes)")

    # Salvar se houve mudanças
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Arquivo salvo! Total de correções: {replacements_made}")
    else:
        print("✅ Nenhuma correção necessária!")

    return replacements_made


if __name__ == "__main__":
    file_path = "templates/implantacao/modelo_modelagem_financeira.html"
    total = fix_encoding(file_path)
    print(f"\n🎉 Concluído! Total de correções: {total}")
