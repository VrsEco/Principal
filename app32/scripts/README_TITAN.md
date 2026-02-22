
# Titan Corp (Company 36) Reset Protocol

To fully reset the Titan Corp dataset (clean slate), run the following scripts in order:

## 1. Nuke Bulk Data
Removes Projects, Plans, Processes, and most dependencies.
```powershell
python scripts/nuke_titan_final.py
```

## 2. Nuke Employees (Deep Clean)
Removes blocked Employees and their deep linkages (Comments, Logs, Team Members).
```powershell
python scripts/nuke_employees_final.py
```
*Verify output: "--- NUKE EMPLOYEES V2 COMPLETE ---"*

## 3. Seed Data
Populates Company 36 with fresh data (Admin, Employees, Portfolio, RAG Project, 5W2H Tasks).
```powershell
python scripts/reset_titan_corp.py
```
*Verify output: "--- CADASTRO REFEITO COM SUCESSO! ---"*

## 4. Audit
Verify the data health.
```powershell
python scripts/audit_titan_360.py
```
**Expected Counts (approx):**
- Employees: 3
- Portfolios: 1
- Plans: 1
- Projects: 1
- Tasks: 2
