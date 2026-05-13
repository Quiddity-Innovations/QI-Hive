@echo off
net stop QI_BrainAPI
timeout /t 3 /nobreak >nul
net start QI_BrainAPI
