# Zweck: Startet den Cloud-Abbau oder Wiederaufbau in WSL; ohne Aktionsangabe wird nur der Status gelesen.
param(
    [ValidateSet('down', 'up', 'status', 'check')]
    [string]$Action = 'status',
    [string]$WslUser = 'cyberalex'
)
$ErrorActionPreference = 'Stop'
$taskPythonScript = Join-Path $PSScriptRoot 'lifecycle.py'
$taskLinuxScript = (& wsl.exe -u $WslUser --exec wslpath -u $taskPythonScript).Trim()
if ($LASTEXITCODE -ne 0) { throw 'WSL-Projektpfad konnte nicht ermittelt werden.' }
& wsl.exe -u $WslUser --exec python3 -u $taskLinuxScript $Action
if ($LASTEXITCODE -ne 0) { throw 'LearningSteps-Aktion wurde angehalten. Keine Fehlermeldungen mit Geheimniswerten weitergeben.' }
