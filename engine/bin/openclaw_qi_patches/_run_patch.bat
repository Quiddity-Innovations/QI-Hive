@echo off
wsl -d Ubuntu-24.04 -- bash -lc "cd ~ && python3 /mnt/c/QIH/engine/bin/openclaw_qi_patches/apply_filter_patch.py"
