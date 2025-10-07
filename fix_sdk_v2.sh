#!/bin/bash
# Script mejorado para solucionar el problema del SDK manager

echo "=== Solucionando problema del SDK Manager (v2) ==="

# Ruta del SDK
SDK_DIR="$HOME/.buildozer/android/platform/android-sdk"

if [ -d "$SDK_DIR" ]; then
    echo "SDK encontrado en: $SDK_DIR"
    
    # Limpiar completamente y empezar de nuevo
    echo "Limpiando SDK existente..."
    rm -rf "$SDK_DIR"
    mkdir -p "$SDK_DIR"
    
    # Descargar cmdline-tools directamente
    echo "Descargando cmdline-tools..."
    cd "$SDK_DIR"
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-8512546_latest.zip
    
    if [ $? -eq 0 ]; then
        echo "Extrayendo cmdline-tools..."
        unzip -q commandlinetools-linux-8512546_latest.zip
        
        # Crear la estructura correcta
        mkdir -p cmdline-tools/latest
        mv cmdline-tools/* cmdline-tools/latest/ 2>/dev/null || true
        
        # Verificar que se movió correctamente
        if [ -f "cmdline-tools/latest/bin/sdkmanager" ]; then
            echo "✅ cmdline-tools configurado correctamente"
            
            # Crear symlinks para compatibilidad
            mkdir -p tools/bin
            ln -sf "../../cmdline-tools/latest/bin/sdkmanager" "tools/bin/sdkmanager"
            ln -sf "../../cmdline-tools/latest/bin/avdmanager" "tools/bin/avdmanager"
            
            chmod +x cmdline-tools/latest/bin/*
            chmod +x tools/bin/*
            
            echo "✅ Symlinks creados para compatibilidad"
            echo "✅ SDK Manager configurado exitosamente"
            
        else
            echo "❌ Error: sdkmanager no encontrado después de la instalación"
        fi
        
        # Limpiar archivo zip
        rm -f commandlinetools-linux-8512546_latest.zip
        
    else
        echo "❌ Error descargando cmdline-tools"
        exit 1
    fi
    
else
    echo "SDK no encontrado, será descargado durante el build"
fi

echo "=== Listo para compilar ==="