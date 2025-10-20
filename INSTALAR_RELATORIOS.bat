@echo off
chcp 65001 >nul
echo ================================================================
echo 🚀 INSTALAÇÃO DE BIBLIOTECAS PARA RELATÓRIOS PROFISSIONAIS
echo Sistema: PEVAPP22
echo ================================================================
echo.

echo 📦 Instalando bibliotecas necessárias...
echo.
echo Este processo pode levar alguns minutos...
echo.

pip install weasyprint plotly kaleido pandas numpy openpyxl matplotlib seaborn xlsxwriter tabulate

echo.
echo ================================================================
echo.

if %ERRORLEVEL% EQU 0 (
    echo ✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!
    echo.
    echo 📊 Bibliotecas instaladas:
    echo    • WeasyPrint - Geração de PDF profissional
    echo    • Plotly - Gráficos corporativos de alta qualidade
    echo    • Kaleido - Exportação de gráficos como imagens
    echo    • Pandas - Manipulação e análise de dados
    echo    • NumPy - Cálculos numéricos
    echo    • OpenPyXL - Exportação para Excel
    echo    • Matplotlib - Gráficos estatísticos
    echo    • Seaborn - Visualizações avançadas
    echo    • XlsxWriter - Excel com formatação avançada
    echo    • Tabulate - Tabelas formatadas
    echo.
    echo 🎯 Próximo passo: Execute o teste de demonstração
    echo    python teste_relatorio_profissional.py
) else (
    echo ❌ ERRO: Falha na instalação!
    echo.
    echo Tente executar manualmente:
    echo    pip install -r requirements_relatorios.txt
)

echo.
echo ================================================================
pause


