[app]

# (str) Título de tu aplicación
title = Grabador de Audio

# (str) Nombre del paquete
package.name = audiorecorder

# (str) Dominio del paquete (necesario para Google Play)
package.domain = com.yorch.audiorecorder

# (str) Código fuente de tu aplicación
source.dir = .

# (list) Extensiones de archivos fuente a incluir
source.include_exts = py,png,jpg,kv,atlas,txt,ini

# (str) Archivo principal de la aplicación
source.main = main.py

# (str) Versión de la aplicación
version = 1.0

# (list) Requerimientos de la aplicación
requirements = python3,kivy,plyer,audiostream

# (list) Permisos de Android
android.permissions = RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Versión mínima del API
android.minapi = 21

# (list) Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) Usar Android auto backup feature
android.allow_backup = True

# (str) Orientación soportada (landscape, portrait o all)
orientation = portrait

# (bool) Fullscreen
fullscreen = 0

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1