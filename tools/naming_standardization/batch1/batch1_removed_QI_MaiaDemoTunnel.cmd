C:\QIH\engine\bin\nssm.exe install QI_MaiaDemoTunnel "C:\Program Files (x86)\cloudflared\cloudflared.exe"
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel AppParameters "tunnel --protocol http2 --url http://localhost:7860"
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel AppDirectory "C:\Program Files (x86)\cloudflared"
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel AppExit Default Restart
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel AppStdout C:\APPS\QI\LOGS\Maia_Gradio_Tunnel_Log.txt
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel AppStderr C:\APPS\QI\LOGS\Maia_Gradio_Tunnel_Log.txt
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel AppRotateFiles 1
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel Description "Cloudflare quick tunnel exposing Maia Gradio demo UI (port 7860) for demonstrations and testing. Start manually when needed."
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel DisplayName "QI - Maia Demo Tunnel (Gradio)"
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel ObjectName LocalSystem
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel Start SERVICE_DISABLED
C:\QIH\engine\bin\nssm.exe set QI_MaiaDemoTunnel Type SERVICE_WIN32_OWN_PROCESS
