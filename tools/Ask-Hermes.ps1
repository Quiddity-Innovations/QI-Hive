<#
.SYNOPSIS
  Ask-Hermes — one-shot local NL query through a Hermes MCP toolset.
  Quiddity Innovations, 2026-07-06.

  Routes an MCP-tool query to a TOOL-CAPABLE local model and scopes it to a
  single MCP server, so the query never loads the rich schemas that crash the
  gpt-oss-20b Ollama template. See C:\QIH\docs\QI_Hermes_Leverage_Playbook.md.

.WHY THE DEFAULTS
  -Model llama3.1:8b : 128K context (clears Hermes's 64K floor) AND a mature
                       Ollama tool template that renders rich MCP JSON schemas.
                       gpt-oss-20b does NOT (template bug `index $prop.Type 0`).
  -Server (toolset)  : loads ONLY that MCP server's tools — brain | maia-db |
                       domain. Anything else stays out of the tool list.

.EXAMPLES
  .\Ask-Hermes.ps1 -Server brain   -Prompt "Which QI projects have no session logged in 30 days?"
  .\Ask-Hermes.ps1 -Server maia-db -Prompt "How many messages per channel this week, as a table?"
  .\Ask-Hermes.ps1 -Server domain  -Prompt "Is quiddityinnovations.com registered?" -Model hf.co/unsloth/gpt-oss-20b-GGUF:latest
#>
param(
  [Parameter(Mandatory)][ValidateSet('brain','maia-db','domain')]
  [string]$Server,
  [Parameter(Mandatory)][string]$Prompt,
  [string]$Model = 'llama3.1:8b'
)
$hermes = Join-Path $env:LOCALAPPDATA 'hermes\hermes-agent\venv\Scripts\hermes.exe'
if (-not (Test-Path $hermes)) { $hermes = 'hermes' }
# Order matters: -z is greedy and must be LAST with its prompt.
& $hermes -m $Model -t $Server -z $Prompt
