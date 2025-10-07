#!/bin/bash

# Comando rápido para compilar desde WSL
# Uso: ./quick_build.sh [clean|release]

cd /mnt/c/Users/Yorch/Dropbox/Proyectos/Python/List\&Rec

# Configurar JAVA_HOME si es necesario
if [ -z "$JAVA_HOME" ]; then
    export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
fi

# Agregar ~/.local/bin al PATH si no está
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

case "$1" in
    "clean")
        echo "=== Build limpio ==="
        buildozer android clean
        buildozer android debug
        ;;
    "release")
        echo "=== Build release ==="
        buildozer android release
        ;;
    *)
        echo "=== Build debug normal ==="
        buildozer android debug
        ;;
esac

# Mostrar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ¡Build exitoso!"
    ls -la bin/*.apk 2>/dev/null || echo "APK no encontrado en bin/"
else
    echo ""
    echo "❌ Build falló. Para más información ejecuta:"
    echo "buildozer -v android debug"
fi