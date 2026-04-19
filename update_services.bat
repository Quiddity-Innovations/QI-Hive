@echo off
:: QI Hive — Update NSSM services to new paths
:: Run this as Administrator

set NSSM=C:\UNIVERSAL\dashboard\nssm.exe

echo ============================================
echo  QI Hive — NSSM Service Migration
echo  Updating all services to C:\QIH paths
echo ============================================

echo.
echo [1/2] Updating QI_BrainAPI...
%NSSM% stop QI_BrainAPI
%NSSM% set QI_BrainAPI AppDirectory "C:\QIH\brain"
%NSSM% set QI_BrainAPI AppParameters "C:\QIH\brain\qi_brain_api.py"
%NSSM% set QI_BrainAPI Description "QI Brain — hive nervous system (SQLite + ChromaDB + MCP)"
%NSSM% start QI_BrainAPI
echo    QI_BrainAPI -> C:\QIH\brain  [DONE]

echo.
echo [2/2] Updating QI_Dashboard...
%NSSM% stop QI_Dashboard
%NSSM% set QI_Dashboard AppDirectory "C:\QIH\hive"
%NSSM% set QI_Dashboard AppParameters "C:\QIH\hive\Dashboard\server.py"
%NSSM% set QI_Dashboard Description "QI Hive Dashboard — agent orchestration UI (port 8600)"
%NSSM% start QI_Dashboard
echo    QI_Dashboard -> C:\QIH\hive  [DONE]

echo.
echo ============================================
echo  Verifying services...
echo ============================================
%NSSM% status QI_BrainAPI
%NSSM% status QI_Dashboard

echo.
echo Done. Open http://localhost:8600 to verify the Hive dashboard.
pause
