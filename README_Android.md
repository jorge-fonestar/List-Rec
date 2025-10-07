# Grabador de Audio - Compilación Android

Este proyecto contiene una aplicación de grabación de audio desarrollada con Kivy que puede ser compilada como APK para Android.

## Archivos del Proyecto

- `audio_recorder.py` - Versión original para Windows/Linux
- `main.py` - Versión adaptada para Android
- `buildozer.spec` - Configuración de compilación
- `compile_android.sh` - Script de compilación automatizado
- `config_android.ini` - Configuración de la app móvil

## Requisitos

- Windows 10/11 con WSL2 instalado
- Ubuntu en WSL
- Al menos 4GB de espacio libre
- Conexión a internet estable

## Pasos para Compilar el APK

### 1. Preparar WSL

Abre PowerShell como administrador y ejecuta:

```powershell
wsl --install Ubuntu
wsl --update
```

### 2. Acceder a WSL y navegar al proyecto

```bash
wsl
cd /mnt/c/Users/Yorch/Dropbox/Proyectos/Python/List\&Rec/
```

### 3. Dar permisos de ejecución al script

```bash
chmod +x compile_android.sh
```

### 4. Ejecutar la compilación

```bash
./compile_android.sh
```

Este script:
- Instala todas las dependencias necesarias
- Configura el entorno Java
- Compila el APK usando Buildozer

### 5. Compilación limpia (si es necesario)

Si tienes problemas, puedes limpiar y recompilar:

```bash
./compile_android.sh clean
```

## Ubicación del APK

Una vez completada la compilación, el APK se encontrará en:
```
bin/audiorecorder-1.0-arm64-v8a_armeabi-v7a-debug.apk
```

## Instalación en Android

1. Habilita "Fuentes desconocidas" en Configuración > Seguridad
2. Transfiere el APK a tu dispositivo Android
3. Abre el APK y confirma la instalación

## Permisos Requeridos

La aplicación solicita los siguientes permisos:
- **RECORD_AUDIO**: Para grabar audio del micrófono
- **WRITE_EXTERNAL_STORAGE**: Para guardar las grabaciones
- **READ_EXTERNAL_STORAGE**: Para acceder a grabaciones guardadas

## Funcionalidades de la App Móvil

- ✅ Monitor de volumen en tiempo real (simulado)
- ✅ Control de umbral de detección
- ✅ Estadísticas de grabaciones
- ✅ Interfaz optimizada para móvil
- ✅ Botones grandes para pantallas táctiles
- ⚠️ Grabación real (requiere implementación adicional)

## Notas Importantes

- La versión actual incluye grabación simulada para demostración
- Para grabación real, necesitas implementar el manejo de audio con `plyer`
- El primer build puede tomar 30-60 minutos
- Builds posteriores son más rápidos (5-10 minutos)

## Solución de Problemas Comunes

### Error de Java
```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
```

### Error de permisos
```bash
sudo chown -R $USER:$USER ~/.buildozer
```

### Error de espacio en disco
```bash
# Limpiar builds anteriores
buildozer android clean
```

### Error de NDK/SDK
Buildozer descargará automáticamente Android SDK y NDK. Si hay problemas:
```bash
rm -rf ~/.buildozer
./compile_android.sh
```

## Personalización

### Cambiar ícono de la aplicación
1. Crea un archivo PNG de 512x512 pixels
2. Guárdalo como `icon.png`
3. Descomenta la línea en `buildozer.spec`:
   ```
   icon.filename = icon.png
   ```

### Cambiar splash screen
1. Crea un archivo PNG de 1280x720 pixels
2. Guárdalo como `splash.png`
3. Descomenta la línea en `buildozer.spec`:
   ```
   presplash.filename = splash.png
   ```

### Modificar configuración
Edita el archivo `buildozer.spec` para cambiar:
- Nombre de la aplicación
- Versión
- Permisos
- Orientación de pantalla

## Para Desarrolladores

### Estructura del código móvil
- `main.py` contiene la lógica adaptada para Android
- Usa `plyer` para acceso a funciones del dispositivo
- Solicita permisos en tiempo de ejecución
- Interfaz optimizada para pantallas táctiles

### Agregar grabación real
Para implementar grabación real, necesitas:
1. Usar `plyer.audio` para grabación
2. Implementar conversión de formato de audio
3. Manejar permisos de Android correctamente

## Contacto

Si tienes problemas con la compilación, revisa:
1. Los logs de compilación
2. Que WSL tenga acceso a internet
3. Que tengas suficiente espacio en disco
4. Que Java esté correctamente instalado