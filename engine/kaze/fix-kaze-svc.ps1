$nssm    = "C:\QIH\engine\bin\nssm.exe"
$svc     = "QI_KazeConfigAPI"
$python  = "C:\Program Files\Python311\python.exe"
$script  = "C:\APPS\OC\repo\scripts\kaze\kaze-config-api.py"
$logfile = "C:\APPS\OC\runtime\logs\agents\kaze\kaze-config-api.log"

New-Item -ItemType Directory -Force "C:\APPS\OC\runtime\logs\agents\kaze" | Out-Null

& $nssm stop   $svc 2>$null
& $nssm set    $svc Application    $python
& $nssm set    $svc AppParameters  $script
& $nssm set    $svc AppDirectory   "C:\APPS\OC\repo\scripts\kaze"
& $nssm set    $svc AppThrottle    0
& $nssm set    $svc AppStdout      $logfile
& $nssm set    $svc AppStderr      $logfile
& $nssm set    $svc AppRotateFiles 1
& $nssm set    $svc AppRotateBytes 5000000
& $nssm set    $svc Start          SERVICE_AUTO_START
& $nssm start  $svc

Start-Sleep 5
Write-Output "=== Status ==="
& $nssm status $svc
