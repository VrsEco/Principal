$path = 'C:\GestaoVersus\app32\templates\modules\pev\plan_company.html'
$lines = Get-Content -Path $path
# Line 370 is index 369
$lines[369] = '    let financialRowIndex = {{ company_data.financials|default([])|length }};'
# Line 371 is index 370
$lines[370] = '    // corrected'
$lines | Set-Content -Path $path
