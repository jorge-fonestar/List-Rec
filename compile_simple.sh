#!/bin/bash

# Script simplificado de compilación para tu entorno ya configurado
# yorch@YORCH-VICTUS

echo "=== Compilador APK - Grabador de Audio ==="
echo "Configuración detectada:"
echo "- Python: $(python3 --version)"
echo "- Java: $(java -version 2>&1 | head -1)"
echo "- Buildozer: $(buildozer --version 2>/dev/null || echo 'No encontrado')"
echo ""

# Obtener la ruta correcta del proyecto desde WSL
PROJECT_DIR="/mnt/c/Users/Yorch/Dropbox/Proyectos/Python/List&Rec"

# Verificar si estamos en el directorio correcto
if [ ! -f "main.py" ] || [ ! -f "buildozer.spec" ]; then
    echo "Navegando al directorio del proyecto..."
    cd "$PROJECT_DIR" || {
        echo "ERROR: No se puede acceder al directorio del proyecto"
        echo "Ruta esperada: $PROJECT_DIR"
        exit 1
    }
fi

echo "Directorio actual: $(pwd)"

# Verificar archivos necesarios
echo "Verificando archivos del proyecto..."
MISSING_FILES=""
for file in "main.py" "buildozer.spec"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES="$MISSING_FILES $file"
    fi
done

if [ ! -z "$MISSING_FILES" ]; then
    echo "ERROR: Archivos faltantes:$MISSING_FILES"
    exit 1
fi

echo "✓ Archivos del proyecto encontrados"

# Verificar buildozer
if ! command -v buildozer &> /dev/null; then
    echo "Instalando buildozer..."
    pip3 install --user buildozer
    # Agregar al PATH si no está
    export PATH="$HOME/.local/bin:$PATH"
fi

# Verificar y configurar JAVA_HOME
if [ -z "$JAVA_HOME" ]; then
    # Buscar Java automáticamente
    JAVA_PATH=$(which java)
    if [ ! -z "$JAVA_PATH" ]; then
        # Resolver symlinks
        JAVA_REAL=$(readlink -f "$JAVA_PATH")
        # Obtener directorio de instalación de Java
        JAVA_HOME_CANDIDATE=$(dirname $(dirname "$JAVA_REAL"))
        
        # Verificar si es un directorio válido de Java
        if [ -f "$JAVA_HOME_CANDIDATE/bin/java" ]; then
            export JAVA_HOME="$JAVA_HOME_CANDIDATE"
            echo "JAVA_HOME configurado automáticamente: $JAVA_HOME"
        fi
    fi
fi

# Mostrar configuración
echo ""
echo "=== Configuración Final ==="
echo "JAVA_HOME: ${JAVA_HOME:-'No configurado'}"
echo "PATH includes ~/.local/bin: $(echo $PATH | grep -q '.local/bin' && echo 'Sí' || echo 'No')"
echo ""

# Preguntar tipo de build
echo "Opciones de compilación:"
echo "1. Build debug (rápido)"
echo "2. Build debug limpio (recomendado si es la primera vez)"
echo "3. Build release (para distribución)"
echo ""

read -p "Selecciona una opción (1-3): " BUILD_OPTION

case $BUILD_OPTION in
    1)
        echo "=== Iniciando build debug ==="
        buildozer android debug
        ;;
    2)
        echo "=== Iniciando build debug limpio ==="
        echo "Limpiando builds anteriores..."
        buildozer android clean
        buildozer android debug
        ;;
    3)
        echo "=== Iniciando build release ==="
        echo "NOTA: Necesitarás configurar las claves de firma para distribución"
        buildozer android release
        ;;
    *)
        echo "Opción inválida. Ejecutando build debug por defecto."
        buildozer android debug
        ;;
esac

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "=== ¡COMPILACIÓN EXITOSA! ==="
    echo ""
    
    # Buscar el APK generado
    APK_FILE=$(find ./bin -name "*.apk" -type f 2>/dev/null | head -1)
    
    if [ ! -z "$APK_FILE" ]; then
        APK_SIZE=$(du -h "$APK_FILE" | cut -f1)
        echo "APK generado: $APK_FILE"
        echo "Tamaño: $APK_SIZE"
        echo ""
        echo "Para instalar en tu dispositivo Android:"
        echo "1. Habilita 'Fuentes desconocidas' en Configuración > Seguridad"
        echo "2. Transfiere el APK a tu dispositivo"
        echo "3. Instala tocando el archivo APK"
        echo ""
        echo "El APK se encuentra en Windows en:"
        echo "C:\\Users\\Yorch\\Dropbox\\Proyectos\\Python\\List&Rec\\bin\\"
    else
        echo "APK generado pero no encontrado en ./bin/"
        echo "Revisa la carpeta bin/ manualmente"
    fi
    
else
    echo ""
    echo "=== ERROR EN LA COMPILACIÓN ==="
    echo ""
    echo "Posibles soluciones:"
    echo "- Ejecuta: buildozer android clean"
    echo "- Verifica conexión a internet"
    echo "- Revisa que tengas al menos 4GB libres"
    echo "- Verifica los logs anteriores para errores específicos"
    echo ""
    echo "Si el error persiste, ejecuta:"
    echo "buildozer -v android debug"
    echo "Para obtener información detallada del error"
fi