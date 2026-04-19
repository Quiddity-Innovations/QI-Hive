# grant_claude_service_rights.ps1
# Run ONCE as Administrator.
# Grants your Windows user start/stop/restart rights on all QI services.
# After this runs, Claude can control services without UAC prompts.
# Covers: Maia, Naya, NEXUS, OpenClaw, Cloudflare tunnels, Ollama

$QI_SERVICES = @(
    # MAIA
    @{ Name = "MaiaBot";              Project = "Maia"      },
    @{ Name = "MaiaTunnel";           Project = "Maia"      },
    @{ Name = "MaiaDemoTunnel";       Project = "Maia"      },
    # NAYA
    @{ Name = "NayaBot";              Project = "Naya"      },
    @{ Name = "NayaGradio";           Project = "Naya"      },
    @{ Name = "NayaTunnel";           Project = "Naya"      },
    # NEXUS
    @{ Name = "NEXUSService";         Project = "NEXUS"     },
    @{ Name = "NEXUSTunnel";          Project = "NEXUS"     },
    # OPENCLAW
    @{ Name = "OC-Keepalive-Service"; Project = "OpenClaw"  },
    # SHARED
    @{ Name = "Cloudflared";          Project = "Shared"    },
    @{ Name = "tunnel";               Project = "Shared"    },
    @{ Name = "ollama";               Project = "Shared"    }
)

# Resolve current user SID
$username = "$env:USERDOMAIN\$env:USERNAME"
try {
    $objUser = New-Object System.Security.Principal.NTAccount($username)
    $sid     = $objUser.Translate([System.Security.Principal.SecurityIdentifier]).Value
} catch {
    Write-Host ""
    Write-Host "[ERROR] Could not resolve SID for '$username'" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# SDDL rights granted to current user:
#   CC = SERVICE_QUERY_CONFIG    LC = SERVICE_QUERY_STATUS
#   SW = SERVICE_ENUMERATE_DEPS  RP = SERVICE_START
#   WP = SERVICE_STOP            DT = SERVICE_PAUSE_CONTINUE
#   LO = SERVICE_INTERROGATE     CR = READ_CONTROL
$sddl = "D:(A;;CCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCLCSWRPWPDTLOCRRC;;;$sid)"

Write-Host ""
Write-Host "QI Ecosystem - Claude Service Rights Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  User : $username" -ForegroundColor Gray
Write-Host "  SID  : $sid"      -ForegroundColor Gray
Write-Host ""

$ok_count   = 0
$skip_count = 0
$fail_count = 0
$last_project = ""

foreach ($svc in $QI_SERVICES) {

    if ($svc.Project -ne $last_project) {
        Write-Host "  -- $($svc.Project) --" -ForegroundColor DarkCyan
        $last_project = $svc.Project
    }

    $exists = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if (-not $exists) {
        Write-Host "    [SKIP] $($svc.Name) - not installed" -ForegroundColor Yellow
        $skip_count++
        continue
    }

    $result = & sc.exe sdset $svc.Name $sddl 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK]   $($svc.Name)" -ForegroundColor Green
        $ok_count++
    } else {
        Write-Host "    [FAIL] $($svc.Name) - $result" -ForegroundColor Red
        $fail_count++
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Granted: $ok_count  |  Skipped: $skip_count  |  Failed: $fail_count" -ForegroundColor White
Write-Host ""

if ($fail_count -eq 0) {
    Write-Host "  Claude can now start/stop/restart all QI services" -ForegroundColor Green
    Write-Host "  without admin rights or UAC prompts." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Quick test (no admin needed after this):" -ForegroundColor Gray
    Write-Host "    sc.exe query MaiaBot" -ForegroundColor White
} else {
    Write-Host "  WARNING: Some services failed. Check output above." -ForegroundColor Yellow
    Write-Host "  Failed services will still require manual restart." -ForegroundColor Yellow
}

Write-Host ""
