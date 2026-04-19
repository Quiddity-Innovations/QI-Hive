@echo off
:: ============================================================
::  QI Hive — Finalize migration to QI Project Standard layout
::  RUN THIS AS ADMINISTRATOR
:: ============================================================
::  Steps:
::   1. Stop all affected services
::   2. Remove duplicate legacy services (MaiaBot, ClaudeManager)
::   3. Rename NayaTunnel / NEXUSTunnel to QI_ prefix (or remove if stopped)
::   4. Repoint QI_BrainAPI and QI_Dashboard to engine/ paths
::   5. Switch QI services to project-local nssm.exe binary
::   6. Start services and verify
:: ============================================================

set NSSM=C:\QIH\engine\bin\nssm.exe
set OLD_NSSM=C:\UNIVERSAL\dashboard\nssm.exe

echo.
echo ============================================
echo  [1/5] Stopping services
echo ============================================
%OLD_NSSM% stop QI_Dashboard
%OLD_NSSM% stop QI_BrainAPI
%OLD_NSSM% stop ClaudeManager
%OLD_NSSM% stop MaiaBot
%OLD_NSSM% stop NayaTunnel
%OLD_NSSM% stop NEXUSTunnel

echo.
echo ============================================
echo  [2/5] Removing duplicate legacy services
echo ============================================
%OLD_NSSM% remove ClaudeManager confirm
%OLD_NSSM% remove MaiaBot confirm
echo  (NayaTunnel / NEXUSTunnel left alone — decide later: rename or remove)

echo.
echo ============================================
echo  [3/5] Repointing QI_BrainAPI to engine/brain/api.py
echo ============================================
%OLD_NSSM% set QI_BrainAPI AppDirectory  "C:\QIH"
%OLD_NSSM% set QI_BrainAPI AppParameters "C:\QIH\engine\brain\api.py"
%OLD_NSSM% set QI_BrainAPI Description   "QI Brain — hive nervous system (SQLite + ChromaDB + MCP). Port 9010."

echo.
echo ============================================
echo  [4/5] Repointing QI_Dashboard to engine/hive/dashboard/server.py
echo ============================================
%OLD_NSSM% set QI_Dashboard AppDirectory  "C:\QIH"
%OLD_NSSM% set QI_Dashboard AppParameters "C:\QIH\engine\hive\dashboard\server.py"
%OLD_NSSM% set QI_Dashboard Description   "QI Hive Dashboard — agent orchestration UI. Port 8600."

echo.
echo ============================================
echo  [5/5] Starting services
echo ============================================
%OLD_NSSM% start QI_BrainAPI
timeout /t 3 /nobreak
%OLD_NSSM% start QI_Dashboard
timeout /t 3 /nobreak

echo.
echo ============================================
echo  Verification
echo ============================================
%OLD_NSSM% status QI_BrainAPI
%OLD_NSSM% status QI_Dashboard

echo.
echo  Open http://localhost:8600/hive   (Hive agents)
echo  Open http://localhost:8600/config (log level management)
echo  Open http://localhost:9010/api/agents (Brain API)
echo.
echo  Note: this bat still uses the central nssm.exe at C:\UNIVERSAL\dashboard
echo        because that is what Windows registered the services with.
echo        To switch services to the project-local C:\QIH\engine\bin\nssm.exe
echo        they must be REINSTALLED (remove + install). That is a separate pass.
echo ============================================
pause
