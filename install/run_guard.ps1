$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $root)
py .\main.py
