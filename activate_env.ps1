# Script para activar el entorno virtual en PowerShell
Write-Host "Activando entorno virtual para el Grabador de Audio..." -ForegroundColor Green
.\.venv\Scripts\Activate.ps1
Write-Host ""
Write-Host "Entorno virtual activado. Para ejecutar el programa:" -ForegroundColor Yellow
Write-Host "python audio_recorder.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para desactivar el entorno virtual:" -ForegroundColor Yellow
Write-Host "deactivate" -ForegroundColor Cyan
Write-Host ""