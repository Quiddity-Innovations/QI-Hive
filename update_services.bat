@echo off
:: QI Hive — NSSM service path config (CORRECTED 2026-06-18)
:: Run this as Administrator.
::
:: HISTORY: the original version of this script pointed QI_BrainAPI at the now-archived
:: legacy tree C:\QIH\brain (qi_brain_api.py). That tree was archived to
:: C:\QIH\_archive\brain_legacy_2026-06 on 2026-06-18. The live brain runs from
:: C:\QIH\engine\brain\api.py. These commands now reflect the live, running config —
:: re-running this is safe and idempotent.

set NSSM=C:\QIH\engine\bin\nssm.exe

echo ============================================
echo  QI Hive — NSSM Service Path Config
echo ============================================

echo.
echo [1/2] Configuring QI_BrainAPI -^> C:\QIH\engine\brain\api.py ...
%NSSM% stop QI_BrainAPI
%NSSM% set QI_BrainAPI AppDirectory "C:\QIH"
%NSSM% set QI_BrainAPI AppParameters "C:\QIH\engine\brain\api.py"
%NSSM% set QI_BrainAPI Description "QI Brain — hive nervous system (SQLite + ChromaDB + MCP)"
%NSSM% start QI_BrainAPI
echo    QI_BrainAPI -^> C:\QIH\engine\brain  [DONE]

echo.
echo [2/2] Configuring QI_Dashboard -^> C:\QIH\hive ...
%NSSM% stop QI_Dashboard
%NSSM% set QI_Dashboard AppDirectory "C:\QIH\hive"
%NSSM% set QI_Dashboard AppParameters "C:\QIH\hive\Dashboard\server.py"
%NSSM% set QI_Dashboard Description "QI Hive Dashboard — agent orchestration UI (port 8600)"
%NSSM% start QI_Dashboard
echo    QI_Dashboard -^> C:\QIH\hive  [DONE]

echo.
echo ============================================
echo  Verifying services...
echo ============================================
%NSSM% status QI_BrainAPI
%NSSM% status QI_Dashboard

echo.
echo Done. Open http://localhost:8600 to verify the Hive dashboard.
pause
