# Grabador de Audio con Detección de Volumen

Este script de Python graba secuencias de audio de 30 segundos en bucle continuo y guarda automáticamente las grabaciones que superen un umbral de volumen configurable.

## Características

- **Grabación continua**: Graba en bucles de duración configurable (10-60 segundos)
- **Duración configurable**: Slider para ajustar el tiempo de grabación de cada tramo
- **Detección de volumen**: Analiza el nivel de audio en tiempo real
- **Umbral configurable**: Slider para ajustar el umbral de volumen (-60 a 0 dB)
- **Indicador visual del tramo actual**: Muestra si la grabación en curso será guardada o eliminada
- **Guardado automático**: Solo guarda grabaciones que superen el umbral
- **Interfaz gráfica**: Interfaz intuitiva con Tkinter
- **Monitor visual**: Barra de progreso que muestra el volumen actual
- **Estadísticas**: Contador de grabaciones guardadas y eliminadas

## Instalación

### Opción 1: Usar entorno virtual (Recomendado)

1. **Activar el entorno virtual** (ya está configurado):
   - **Windows Command Prompt**: `activate_env.bat`
   - **PowerShell**: `.\activate_env.ps1`

2. **Las dependencias ya están instaladas** en el entorno virtual `.venv`

### Opción 2: Instalación manual

1. Crea un entorno virtual:
```bash
python -m venv .venv
```

2. Activa el entorno virtual:
   - **Windows**: `.venv\Scripts\activate`
   - **Linux/Mac**: `source .venv/bin/activate`

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

**Nota para Windows**: Si tienes problemas instalando PyAudio, puedes usar:
```bash
pip install pipwin
pipwin install pyaudio
```

## Uso

1. Ejecuta el script:
```bash
python audio_recorder.py
```

2. **Configurar parámetros**: 
   - Usa el slider superior para establecer el umbral de volumen en decibelios
   - Usa el slider inferior para configurar la duración de cada grabación (10-60 segundos)
   - Las grabaciones que no superen el umbral se eliminarán automáticamente

3. **Iniciar grabación**: Haz clic en "Iniciar Grabación" para comenzar el bucle de grabación.

4. **Monitorear**: 
   - Observa el monitor de volumen en tiempo real
   - El "Tramo actual" te indicará si la grabación en curso será guardada (✅) o eliminada (❌)
   - Revisa las estadísticas de grabaciones guardadas y eliminadas

5. **Detener**: Haz clic en "Detener Grabación" cuando desees parar.

## Configuración

- **Duración de grabación**: 10-60 segundos por ciclo (configurable con slider)
- **Umbral de volumen**: -60 a 0 dB (configurable con slider)
- **Formato de audio**: WAV, 16-bit, mono, 44.1 kHz
- **Directorio de salida**: `grabaciones/` (se crea automáticamente)
- **Formato de nombre**: `grabacion_YYYYMMDD_HHMMSS.wav`

## Estructura de archivos

```
grabaciones/
├── grabacion_20250927_143025.wav
├── grabacion_20250927_143055.wav
└── ...
```

## Parámetros técnicos

- **Canales**: 1 (mono)
- **Frecuencia de muestreo**: 44,100 Hz
- **Formato**: 16-bit PCM
- **Tamaño de chunk**: 1024 frames
- **Rango de umbral**: -60 dB a 0 dB

## Notas importantes

- El micrófono debe estar conectado y funcionando
- Se requieren permisos de acceso al micrófono
- Las grabaciones se guardan automáticamente con timestamp
- El cálculo de decibelios usa RMS (Root Mean Square)
- La aplicación funciona en segundo plano mientras graba

## Solución de problemas

### Error de PyAudio
Si recibes errores relacionados con PyAudio, especialmente en Windows:
1. Instala Microsoft Visual C++ Build Tools
2. O usa `pipwin install pyaudio` como alternativa

### Problemas de micrófono
- Verifica que el micrófono esté conectado
- Asegúrate de que no esté siendo usado por otra aplicación
- Revisa los permisos de acceso al micrófono del sistema