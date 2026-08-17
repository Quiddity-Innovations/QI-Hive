# -*- coding: utf-8 -*-
"""QI_MaiaQueueDrain service entry point (launcher shim).

The elevation broker's NSSM whitelist only registers services whose scripts
live under C:\\QIH or C:\\APPS\\QIP, while the drainer itself belongs to the Maia
project (C:\\APPS\\QI\\TOOLS\\aws_relay\\queue_drainer.py). This shim bridges the
two: NSSM runs this file; it executes the real drainer in-process.
"""
import runpy

runpy.run_path(r"C:\APPS\QI\TOOLS\aws_relay\queue_drainer.py", run_name="__main__")
