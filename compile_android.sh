#!/bin/bash

# Script para compilar la aplicación Android
# Ejecutar en WSL Ubuntu

echo "=== Preparando entorno para compilar APK ==="

# Actualizar sistema
echo "Actualizando sistema..."
sudo apt update && sudo apt upgrade -y

# Verificar si ya tenemos las dependencias básicas
echo "Verificando dependencias del sistema..."

# Solo instalar lo que falta
PACKAGES_TO_INSTALL=""
command -v git >/dev/null 2>&1 || PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL git"
command -v zip >/dev/null 2>&1 || PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL zip unzip"
command -v gcc >/dev/null 2>&1 || PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL build-essential"

if [ ! -z "$PACKAGES_TO_INSTALL" ]; then
    echo "Instalando paquetes faltantes: $PACKAGES_TO_INSTALL"
    sudo apt install -y $PACKAGES_TO_INSTALL autoconf libtool pkg-config \
        zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 libffi-dev libssl-dev \
        ccache m4 libc6-dev-i386 cmake
else
    echo "Dependencias del sistema ya instaladas ✓"
fi

# Verificar e instalar dependencias de Python
echo "Verificando dependencias de Python..."
python3 -c "import buildozer" 2>/dev/null || pip3 install --user buildozer
python3 -c "import kivy" 2>/dev/null || pip3 install --user kivy
python3 -c "import cython" 2>/dev/null || pip3 install --user cython
python3 -c "import plyer" 2>/dev/null || pip3 install --user plyer

# Configurar JAVA_HOME con la versión instalada
CURRENT_JAVA=$(update-alternatives --query java | grep Best: | awk '{print $2}')
if [ ! -z "$CURRENT_JAVA" ]; then
    JAVA_HOME_PATH=$(dirname $(dirname $CURRENT_JAVA))
    if [ -z "$JAVA_HOME" ] || [ "$JAVA_HOME" != "$JAVA_HOME_PATH" ]; then
        echo "Configurando JAVA_HOME para Java 11..."
        export JAVA_HOME=$JAVA_HOME_PATH
        echo "export JAVA_HOME=$JAVA_HOME_PATH" >> ~/.bashrc
        echo "export PATH=\$JAVA_HOME/bin:\$PATH" >> ~/.bashrc
        echo "JAVA_HOME configurado: $JAVA_HOME"
    else
        echo "JAVA_HOME ya configurado: $JAVA_HOME ✓"
    fi
fi

# Crear directorio de trabajo si no existe
WORK_DIR="/mnt/c/Users/Yorch/Dropbox/Proyectos/Python/List&Rec"
if [ -d "$WORK_DIR" ]; then
    cd "$WORK_DIR"
    echo "Trabajando en: $(pwd)"
else
    echo "ERROR: No se encuentra el directorio del proyecto"
    echo "Asegúrate de que la ruta sea correcta: $WORK_DIR"
    exit 1
fi

echo "=== Iniciando compilación del APK ==="

# Limpiar builds anteriores si es necesario
if [ "$1" == "clean" ]; then
    echo "Limpiando builds anteriores..."
    buildozer android clean
fi

# Compilar APK debug
echo "Compilando APK debug..."
buildozer android debug

# Verificar si la compilación fue exitosa
if [ $? -eq 0 ]; then
    echo "=== ¡COMPILACIÓN EXITOSA! ==="
    echo "El APK se encuentra en: bin/audiorecorder-1.0-arm64-v8a_armeabi-v7a-debug.apk"
    echo ""
    echo "Para instalar en tu dispositivo Android:"
    echo "1. Habilita 'Fuentes desconocidas' en Configuración > Seguridad"
    echo "2. Transfiere el APK a tu dispositivo"
    echo "3. Instala el APK"
    echo ""
    echo "Para compilar una versión release (firmada):"
    echo "buildozer android release"
else
    echo "ERROR: La compilación falló"
    echo "Revisa los mensajes de error anteriores"
    exit 1
fi