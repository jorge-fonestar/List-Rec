#!/bin/bash
# Script de compilación que evita el problema del SDK

echo "=== Compilador APK con solución de SDK ==="

# NO usar sudo - buildozer debe ejecutarse como usuario normal
if [ "$EUID" -eq 0 ]; then
    echo "❌ ERROR: No ejecutes este script con sudo"
    echo "Buildozer debe ejecutarse como usuario normal"
    exit 1
fi

# Configurar variables de entorno
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH="$HOME/.local/bin:$PATH"

# Verificar que buildozer esté disponible
if ! command -v buildozer &> /dev/null; then
    echo "Buildozer no encontrado, instalando..."
    pip3 install --user buildozer
    export PATH="$HOME/.local/bin:$PATH"
fi

# Navegar al directorio correcto
cd /mnt/c/Users/Yorch/Dropbox/Proyectos/Python/List\&Rec

echo "Directorio actual: $(pwd)"
echo "Java: $(java -version 2>&1 | head -1)"
echo "Python: $(python3 --version)"
echo "Buildozer: $(buildozer --version 2>/dev/null || echo 'Error verificando versión')"

# Limpiar cache de buildozer con permisos correctos
echo "Limpiando cache de buildozer..."
chmod -R 755 .buildozer 2>/dev/null || true
rm -rf ~/.buildozer
rm -rf .buildozer

# Crear un buildozer.spec minimalista que funcione
echo "Creando buildozer.spec optimizado..."
cat > buildozer_simple.spec << 'EOF'
[app]
title = Audio Recorder
package.name = audiorecorder  
package.domain = com.yorch.audiorecorder
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy,plyer
android.permissions = RECORD_AUDIO,WRITE_EXTERNAL_STORAGE
android.minapi = 21
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
EOF

echo "Iniciando compilación con configuración simple..."
buildozer --profile simple android debug

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 ¡APK compilado exitosamente!"
    ls -la bin/*.apk 2>/dev/null
else
    echo ""
    echo "❌ Compilación falló"
    echo "Intentando compilación verbose para más información..."
    buildozer --profile simple -v android debug
fi