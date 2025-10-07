#!/bin/bash
# Script para solucionar el problema del SDK manager

echo "=== Solucionando problema del SDK Manager ==="

# Ruta del SDK
SDK_DIR="$HOME/.buildozer/android/platform/android-sdk"

if [ -d "$SDK_DIR" ]; then
    echo "SDK encontrado en: $SDK_DIR"
    
    # Crear la estructura correcta para cmdline-tools
    CMDTOOLS_DIR="$SDK_DIR/cmdline-tools"
    
    if [ ! -d "$CMDTOOLS_DIR/latest" ]; then
        echo "Creando estructura correcta para cmdline-tools..."
        
        # Si existe tools/, moverlo a cmdline-tools/latest/
        if [ -d "$SDK_DIR/tools" ]; then
            mkdir -p "$CMDTOOLS_DIR/latest"
            cp -r "$SDK_DIR/tools"/* "$CMDTOOLS_DIR/latest/"
            echo "Tools movido a cmdline-tools/latest/"
        else
            # Limpiar directorio cmdline-tools si existe
            rm -rf "$CMDTOOLS_DIR"
            
            # Descargar cmdline-tools actualizado
            echo "Descargando cmdline-tools..."
            cd "$SDK_DIR"
            wget -q https://dl.google.com/android/repository/commandlinetools-linux-8512546_latest.zip
            unzip -q commandlinetools-linux-8512546_latest.zip
            
            # Crear la estructura correcta
            mkdir -p "$CMDTOOLS_DIR"
            mv cmdline-tools "$CMDTOOLS_DIR/latest"
            rm commandlinetools-linux-8512546_latest.zip
            echo "cmdline-tools descargado e instalado"
        fi
    fi
    
    # Verificar que sdkmanager existe
    SDKMANAGER="$CMDTOOLS_DIR/latest/bin/sdkmanager"
    if [ -f "$SDKMANAGER" ]; then
        echo "✅ sdkmanager encontrado en: $SDKMANAGER"
        chmod +x "$SDKMANAGER"
        
        # Crear symlink en la ubicación que busca buildozer
        OLD_LOCATION="$SDK_DIR/tools/bin"
        mkdir -p "$OLD_LOCATION"
        ln -sf "$SDKMANAGER" "$OLD_LOCATION/sdkmanager"
        echo "✅ Symlink creado para compatibilidad"
        
        echo "=== SDK Manager configurado correctamente ==="
        
    else
        echo "❌ No se pudo configurar sdkmanager"
        exit 1
    fi
else
    echo "SDK no encontrado, será descargado durante el build"
fi

echo "=== Listo para compilar ==="