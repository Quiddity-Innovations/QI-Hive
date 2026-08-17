# -*- coding: utf-8 -*-
"""
QI_ClaudeVoiceControl launcher.

NSSM entry point for the Claude Voice brain control API + config UI (:8720,
loopback only). Lives under C:\\QIH so the QI_Elevate broker whitelist can
install it; the real app lives at C:\\APPS\\CLAUDE\\Claude Voice\\server.py.
"""
import os
import runpy
import sys

APP = r"C:\APPS\CLAUDE\Claude Voice"

os.chdir(APP)
sys.path.insert(0, APP)
runpy.run_path(os.path.join(APP, "server.py"), run_name="__main__")
