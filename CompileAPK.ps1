# Script PowerShell para compilar APK usando WSL
# Ejecutar como administrador

Write-Host "=== Compilador de APK para Grabador de Audio ===" -ForegroundColor Green
Write-Host "Este script solucionará los problemas del SDK y compilará tu APK" -ForegroundColor Yellow
Write-Host ""

# Navegar al directorio del proyecto
$projectPath = "C:\Users\Yorch\Dropbox\Proyectos\Python\List&Rec"
if (!(Test-Path $projectPath)) {
    Write-Host "ERROR: No se encuentra el directorio del proyecto: $projectPath" -ForegroundColor Red
    pause
    exit
}

Set-Location $projectPath
Write-Host "Trabajando en: $(Get-Location)" -ForegroundColor Green

# Verificar archivos necesarios
$requiredFiles = @("main.py", "buildozer.spec", "fix_sdk.sh")
foreach ($file in $requiredFiles) {
    if (!(Test-Path $file)) {
        Write-Host "ERROR: Archivo requerido no encontrado: $file" -ForegroundColor Red
        pause
        exit
    }
}

Write-Host "Todos los archivos necesarios están presentes." -ForegroundColor Green

# Opciones de compilación
Write-Host ""
Write-Host "Opciones de compilación:" -ForegroundColor Yellow
Write-Host "1. Compilar APK (build normal)"
Write-Host "2. Compilar APK (con fix de SDK)"
Write-Host "3. Solo arreglar SDK"
Write-Host ""

do {
    $option = Read-Host "Selecciona una opción (1-3)"
} while ($option -notmatch '^[1-3]$')

# Preparar comandos WSL
$wslProjectPath = "/mnt/c/Users/Yorch/Dropbox/Proyectos/Python/List&Rec"

switch ($option) {
    1 {
        Write-Host "Iniciando compilación normal..." -ForegroundColor Green
        wsl bash -c "cd '$wslProjectPath' && buildozer android debug"
    }
    2 {
        Write-Host "Arreglando SDK y compilando..." -ForegroundColor Green
        wsl bash -c "cd '$wslProjectPath' && chmod +x fix_sdk.sh && ./fix_sdk.sh && buildozer android debug"
    }
    3 {
        Write-Host "Solo arreglando SDK..." -ForegroundColor Green
        wsl bash -c "cd '$wslProjectPath' && chmod +x fix_sdk.sh && ./fix_sdk.sh"
    }
}

# Verificar si la compilación fue exitosa
if ($LASTEXITCODE -eq 0 -and ($option -eq 1 -or $option -eq 2)) {
    Write-Host ""
    Write-Host "=== ¡COMPILACIÓN EXITOSA! ===" -ForegroundColor Green
    Write-Host "El APK se encuentra en: bin\audiorecorder-1.0-arm64-v8a_armeabi-v7a-debug.apk" -ForegroundColor Yellow
    
    # Verificar si el APK existe
    $apkPath = "bin\audiorecorder-1.0-arm64-v8a_armeabi-v7a-debug.apk"
    if (Test-Path $apkPath) {
        Write-Host "APK confirmado: $(Get-Item $apkPath | Select-Object Name, Length, LastWriteTime)" -ForegroundColor Green
        
        # Preguntar si desea abrir la carpeta
        $openFolder = Read-Host "¿Deseas abrir la carpeta con el APK? (s/n)"
        if ($openFolder -eq 's' -or $openFolder -eq 'S') {
            Start-Process explorer.exe -ArgumentList "bin"
        }
    } else {
        Write-Host "ADVERTENCIA: No se encontró el APK en la ubicación esperada." -ForegroundColor Red
        Write-Host "Revisa la carpeta bin\ manualmente." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Para instalar en tu dispositivo Android:" -ForegroundColor Cyan
    Write-Host "1. Habilita 'Fuentes desconocidas' en Configuración > Seguridad" -ForegroundColor White
    Write-Host "2. Transfiere el APK a tu dispositivo" -ForegroundColor White
    Write-Host "3. Abre el APK en tu dispositivo e instala" -ForegroundColor White
    
} elseif ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: La compilación falló" -ForegroundColor Red
    Write-Host "Revisa los mensajes de error anteriores" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Problemas comunes y soluciones:" -ForegroundColor Cyan
    Write-Host "- Falta de espacio en disco: Libera al menos 4GB" -ForegroundColor White
    Write-Host "- Problemas de permisos: Ejecuta como administrador" -ForegroundColor White
    Write-Host "- Error de Java: WSL configurará automáticamente" -ForegroundColor White
    Write-Host "- Falla de descarga: Verifica conexión a internet" -ForegroundColor White
} elseif ($option -eq 3) {
    Write-Host ""
    Write-Host "Entorno configurado exitosamente." -ForegroundColor Green
    Write-Host "Ahora puedes ejecutar este script nuevamente para compilar." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Presiona cualquier tecla para continuar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")