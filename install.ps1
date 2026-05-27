# Author: kamekingdom (2026-05-27)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir\scripts\install_kamex.py" @args
