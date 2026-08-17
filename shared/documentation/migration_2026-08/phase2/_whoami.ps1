$ErrorActionPreference = 'Stop'
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$p  = New-Object Security.Principal.WindowsPrincipal($id)
Write-Output ("WhoAmI  : " + $id.Name)
Write-Output ("IsAdmin : " + $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
Write-Output ("PSVer   : " + $PSVersionTable.PSVersion.ToString())
