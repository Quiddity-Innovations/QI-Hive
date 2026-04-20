# install_gsudo.ps1 — one-shot installer for gsudo + credential cache
# Run this ONCE as Administrator. After that, Claude can elevate silently.

$ErrorActionPreference = "Stop"

Write-Host "[1/4] Installing gsudo via winget..." -ForegroundColor Cyan
winget install --id gerardog.gsudo --accept-source-agreements --accept-package-agreements --silent

# Refresh PATH so gsudo is visible in this session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "[2/4] Verifying install..." -ForegroundColor Cyan
$v = & gsudo --version 2>&1 | Select-Object -First 1
Write-Host "  gsudo: $v"

Write-Host "[3/4] Enabling credential cache (no repeat UAC prompts)..." -ForegroundColor Cyan
# CacheMode auto: cache a credential the first time you elevate, reuse it automatically
& gsudo config CacheMode auto          | Out-Null
# Cache lifetime: extend to 8 hours so a normal work session only prompts once
& gsudo config CacheDuration 00:08:00  | Out-Null
& gsudo cache on                       | Out-Null

Write-Host "[4/4] Done." -ForegroundColor Green
Write-Host ""
Write-Host "Verify with: gsudo status" -ForegroundColor Yellow
Write-Host "Test with:   gsudo C:\QIH\engine\bin\nssm.exe status QI_Elevate" -ForegroundColor Yellow
Write-Host ""
Write-Host "The first time Claude (or you) runs a gsudo command, Windows will show ONE UAC prompt." -ForegroundColor Yellow
Write-Host "After that, elevated commands run silently for 8 hours." -ForegroundColor Yellow
