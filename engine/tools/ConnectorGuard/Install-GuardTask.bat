@echo off
rem AI-GENERATED BEGIN (Claude Code, 2026-08-06)
rem Installs/updates the QI_McpConnectorGuard scheduled task: reconciles Claude
rem Desktop's mcpServers block against connectors.json every 5 minutes.
rem Hidden via conhost --headless per QI scheduled-task window policy.
schtasks /Create /F /SC MINUTE /MO 5 /TN "QI_McpConnectorGuard" /TR "conhost --headless C:\Program Files\Python311\python.exe C:\QIH\engine\tools\ConnectorGuard\connector_guard.py"
schtasks /Run /TN "QI_McpConnectorGuard"
schtasks /Query /TN "QI_McpConnectorGuard" /FO LIST
rem AI-GENERATED END
