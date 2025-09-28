import tkinter as tk
from tkinter import ttk, messagebox
import pyaudio
import wave
import numpy as np
import threading
import os
from datetime import datetime
import time
import configparser

class AudioRecorder:
    def __init__(self):
        # Archivo de configuración
        self.config_file = "config.ini"
        
        # Cargar configuración desde archivo
        self.load_config()
        
        self.root = tk.Tk()
        self.root.title("Grabador de Audio con Detección de Volumen")
        self.root.geometry("500x500")
        self.root.resizable(True, True)
        self.root.minsize(400, 500)  # Tamaño mínimo para la interfaz principal más simple
        
        # Configuración de audio - Cargada desde config.ini
        self.CHUNK = self.config_chunk_size
        self.FORMAT = self.config_format
        self.CHANNELS = self.config_channels
        self.RATE = self.config_sample_rate
        # RECORD_SECONDS será definido dinámicamente desde self.record_duration
        
        # Variables de estado - Inicializadas desde config.ini
        self.is_recording = False
        self.audio = None
        self.threshold_db = tk.DoubleVar(value=self.config_threshold_db)
        self.record_duration = tk.DoubleVar(value=self.config_record_seconds)
        self.current_volume = tk.StringVar(value="0.0 dB")
        self.status = tk.StringVar(value="Detenido")
        self.recordings_saved = tk.IntVar(value=0)
        self.recordings_deleted = tk.IntVar(value=0)
        self.will_save_current = tk.StringVar(value="Esperando...")  # Estado del tramo actual
        self.current_max_volume = -60.0  # Volumen máximo del tramo actual
        
        # Variables para tracking de tiempo
        self.recording_start_time = 0  # Tiempo de inicio de la grabación actual
        self.current_recording_time = tk.StringVar(value="0/30 seg")  # Tiempo transcurrido/total
        
        # Variables para calidad de audio - Inicializadas desde config.ini
        self.sample_rate = tk.StringVar(value=str(self.config_sample_rate))
        self.bit_depth = tk.StringVar(value=str(self.config_bit_depth))
        self.channels_mode = tk.StringVar(value="Estéreo" if self.config_channels == 2 else "Mono")
        self.selected_device = tk.StringVar()  # Dispositivo de audio seleccionado
        self.audio_devices = []  # Lista de dispositivos disponibles
        
        # Directorio para guardar grabaciones - Desde config.ini
        self.output_dir = self.config_output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        self.setup_ui()
        self.refresh_audio_devices()  # Cargar dispositivos al inicializar
        
    def load_config(self):
        """Carga la configuración desde el archivo config.ini"""
        # Crear parser que no procese interpolación para evitar problemas con %
        config = configparser.ConfigParser(interpolation=None)
        config.optionxform = str  # Mantener case sensitivity
        
        # Valores por defecto si no existe el archivo o faltan secciones
        defaults = {
            'AUDIO': {
                'RECORD_SECONDS': '30',
                'SAMPLE_RATE': '44100',
                'CHANNELS': '1',
                'FORMAT': '16',
                'CHUNK_SIZE': '1024'
            },
            'INTERFACE': {
                'DEFAULT_THRESHOLD_DB': '-40.0',
                'MIN_THRESHOLD_DB': '-60.0',
                'MAX_THRESHOLD_DB': '0.0'
            },
            'STORAGE': {
                'OUTPUT_DIRECTORY': 'grabaciones',
                'FILENAME_FORMAT': 'grabacion_%Y%m%d_%H%M%S.wav'
            },
            'DISPLAY': {
                'VOLUME_UPDATE_INTERVAL': '100',
                'MIN_DISPLAY_DB': '-60'
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                config.read(self.config_file, encoding='utf-8')
                print(f"Configuración cargada desde {self.config_file}")
            else:
                print(f"Archivo {self.config_file} no encontrado, usando valores por defecto")
                
            # Función auxiliar para extraer solo el número de una cadena
            def extract_number(value_str):
                import re
                # Buscar el primer número (entero o decimal) en la cadena
                match = re.search(r'-?\d+\.?\d*', value_str)
                return match.group(0) if match else value_str
                
            # Cargar valores de audio
            record_seconds_str = config.get('AUDIO', 'RECORD_SECONDS', fallback=defaults['AUDIO']['RECORD_SECONDS'])
            self.config_record_seconds = float(extract_number(record_seconds_str))
            
            sample_rate_str = config.get('AUDIO', 'SAMPLE_RATE', fallback=defaults['AUDIO']['SAMPLE_RATE'])
            self.config_sample_rate = int(extract_number(sample_rate_str))
            
            channels_str = config.get('AUDIO', 'CHANNELS', fallback=defaults['AUDIO']['CHANNELS'])
            self.config_channels = int(extract_number(channels_str))
            
            format_str = config.get('AUDIO', 'FORMAT', fallback=defaults['AUDIO']['FORMAT'])
            format_bits = int(extract_number(format_str))
            
            chunk_str = config.get('AUDIO', 'CHUNK_SIZE', fallback=defaults['AUDIO']['CHUNK_SIZE'])
            self.config_chunk_size = int(extract_number(chunk_str))
            
            # Convertir bits a formato PyAudio
            if format_bits == 16:
                self.config_format = pyaudio.paInt16
                self.config_bit_depth = 16
            elif format_bits == 24:
                self.config_format = pyaudio.paInt24
                self.config_bit_depth = 24
            elif format_bits == 32:
                self.config_format = pyaudio.paInt32
                self.config_bit_depth = 32
            else:
                self.config_format = pyaudio.paInt16
                self.config_bit_depth = 16
                
            # Cargar valores de interfaz
            threshold_str = config.get('INTERFACE', 'DEFAULT_THRESHOLD_DB', fallback=defaults['INTERFACE']['DEFAULT_THRESHOLD_DB'])
            self.config_threshold_db = float(extract_number(threshold_str))
            
            min_threshold_str = config.get('INTERFACE', 'MIN_THRESHOLD_DB', fallback=defaults['INTERFACE']['MIN_THRESHOLD_DB'])
            self.config_min_threshold_db = float(extract_number(min_threshold_str))
            
            max_threshold_str = config.get('INTERFACE', 'MAX_THRESHOLD_DB', fallback=defaults['INTERFACE']['MAX_THRESHOLD_DB'])
            self.config_max_threshold_db = float(extract_number(max_threshold_str))
            
            # Cargar valores de almacenamiento
            self.config_output_dir = config.get('STORAGE', 'OUTPUT_DIRECTORY', fallback=defaults['STORAGE']['OUTPUT_DIRECTORY'])
            # Eliminar comillas si las tiene
            self.config_output_dir = self.config_output_dir.strip('"\'')
            
            self.config_filename_format = config.get('STORAGE', 'FILENAME_FORMAT', fallback=defaults['STORAGE']['FILENAME_FORMAT'])
            self.config_filename_format = self.config_filename_format.strip('"\'')
            
            # Cargar valores de display
            volume_update_str = config.get('DISPLAY', 'VOLUME_UPDATE_INTERVAL', fallback=defaults['DISPLAY']['VOLUME_UPDATE_INTERVAL'])
            self.config_volume_update_interval = int(extract_number(volume_update_str))
            
            min_display_str = config.get('DISPLAY', 'MIN_DISPLAY_DB', fallback=defaults['DISPLAY']['MIN_DISPLAY_DB'])
            self.config_min_display_db = float(extract_number(min_display_str))
            
            print(f"Configuración aplicada: {self.config_sample_rate}Hz, {self.config_bit_depth}bit, {self.config_channels}ch, Umbral: {self.config_threshold_db}dB")
            
        except Exception as e:
            print(f"Error cargando configuración: {e}")
            # Usar valores por defecto en caso de error
            self.config_record_seconds = 30
            self.config_sample_rate = 44100
            self.config_channels = 1
            self.config_format = pyaudio.paInt16
            self.config_bit_depth = 16
            self.config_chunk_size = 1024
            self.config_threshold_db = -40.0
            self.config_min_threshold_db = -60.0
            self.config_max_threshold_db = 0.0
            self.config_output_dir = "grabaciones"
            self.config_filename_format = "grabacion_%Y%m%d_%H%M%S.wav"
            self.config_volume_update_interval = 100
            self.config_min_display_db = -60
            
    def save_config(self, show_messages=False):
        """Guarda la configuración actual en el archivo config.ini"""
        config = configparser.ConfigParser()
        
        # Crear secciones
        config.add_section('AUDIO')
        config.add_section('INTERFACE')
        config.add_section('STORAGE')
        config.add_section('DISPLAY')
        
        try:
            # Guardar valores actuales
            config.set('AUDIO', 'RECORD_SECONDS', str(int(self.record_duration.get())))
            config.set('AUDIO', 'SAMPLE_RATE', str(self.RATE))
            config.set('AUDIO', 'CHANNELS', str(self.CHANNELS))
            config.set('AUDIO', 'FORMAT', str(self.config_bit_depth))
            config.set('AUDIO', 'CHUNK_SIZE', str(self.CHUNK))
            
            config.set('INTERFACE', 'DEFAULT_THRESHOLD_DB', str(self.threshold_db.get()))
            config.set('INTERFACE', 'MIN_THRESHOLD_DB', str(self.config_min_threshold_db))
            config.set('INTERFACE', 'MAX_THRESHOLD_DB', str(self.config_max_threshold_db))
            
            config.set('STORAGE', 'OUTPUT_DIRECTORY', f'"{self.output_dir}"')
            # Escapar los % para evitar problemas con interpolación
            filename_format_escaped = self.config_filename_format.replace('%', '%%')
            config.set('STORAGE', 'FILENAME_FORMAT', f'"{filename_format_escaped}"')
            
            config.set('DISPLAY', 'VOLUME_UPDATE_INTERVAL', str(self.config_volume_update_interval))
            config.set('DISPLAY', 'MIN_DISPLAY_DB', str(self.config_min_display_db))
            
            # Escribir al archivo con comentarios personalizados
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write("# Configuración del Grabador de Audio\n")
                f.write("# Este archivo permite personalizar algunos aspectos del grabador\n\n")
                
                f.write("[AUDIO]\n")
                f.write(f"# Duración de cada grabación en segundos\n")
                f.write(f"RECORD_SECONDS = {int(self.record_duration.get())}\n\n")
                
                f.write(f"# Calidad de audio\n")
                f.write(f"SAMPLE_RATE = {self.RATE}  # Hz\n")
                f.write(f"CHANNELS = {self.CHANNELS}  # 1 = mono, 2 = estéreo\n")
                f.write(f"FORMAT = {self.config_bit_depth}  # bits\n\n")
                
                f.write(f"# Tamaño del buffer\n")
                f.write(f"CHUNK_SIZE = {self.CHUNK}\n\n")
                
                f.write("[INTERFACE]\n")
                f.write(f"# Umbral por defecto en decibelios\n")
                f.write(f"DEFAULT_THRESHOLD_DB = {self.threshold_db.get()}\n\n")
                
                f.write(f"# Rango del slider de umbral\n")
                f.write(f"MIN_THRESHOLD_DB = {self.config_min_threshold_db}\n")
                f.write(f"MAX_THRESHOLD_DB = {self.config_max_threshold_db}\n\n")
                
                f.write("[STORAGE]\n")
                f.write(f"# Directorio donde guardar las grabaciones\n")
                f.write(f'OUTPUT_DIRECTORY = "{self.output_dir}"\n\n')
                
                f.write(f"# Formato del nombre de archivo (usando strftime)\n")
                f.write(f'FILENAME_FORMAT = "{self.config_filename_format}"\n\n')
                
                f.write("[DISPLAY]\n")
                f.write(f"# Actualización del monitor de volumen (milisegundos)\n")
                f.write(f"VOLUME_UPDATE_INTERVAL = {self.config_volume_update_interval}\n\n")
                
                f.write(f"# Limitar el nivel mínimo de dB mostrado\n")
                f.write(f"MIN_DISPLAY_DB = {self.config_min_display_db}\n")
                
            if show_messages:
                print(f"Configuración guardada en {self.config_file}")
            
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            if show_messages:
                messagebox.showerror("Error", f"No se pudo guardar la configuración: {str(e)}")
        
    def refresh_audio_devices(self):
        """Obtiene la lista de dispositivos de audio de entrada disponibles y los valida"""
        try:
            # Inicializar PyAudio temporalmente para obtener dispositivos
            temp_audio = pyaudio.PyAudio()
            
            self.audio_devices = []
            device_names = []
            
            # Configuración de prueba estándar (más compatible)
            test_format = pyaudio.paInt16
            test_channels = 1
            test_rate = 44100
            
            # Obtener información de todos los dispositivos
            for i in range(temp_audio.get_device_count()):
                try:
                    device_info = temp_audio.get_device_info_by_index(i)
                    
                    # Solo dispositivos de entrada (micrófonos)
                    if device_info['maxInputChannels'] > 0:
                        # Probar si el dispositivo es compatible con nuestra configuración estándar
                        is_compatible = False
                        try:
                            # Intentar abrir el dispositivo con configuración estándar
                            test_stream = temp_audio.open(
                                format=test_format,
                                channels=min(test_channels, device_info['maxInputChannels']),
                                rate=int(device_info['defaultSampleRate']) if device_info['defaultSampleRate'] > 0 else test_rate,
                                input=True,
                                input_device_index=i,
                                frames_per_buffer=1024
                            )
                            test_stream.close()
                            is_compatible = True
                        except Exception as e:
                            print(f"Dispositivo {device_info['name']} no compatible: {e}")
                            is_compatible = False
                        
                        if is_compatible:
                            device_name = f"{device_info['name']} (ID: {i})"
                            device_names.append(device_name)
                            self.audio_devices.append({
                                'index': i,
                                'name': device_info['name'],
                                'display_name': device_name,
                                'channels': min(device_info['maxInputChannels'], 2),  # Limitar a máximo 2 canales
                                'sample_rate': int(device_info['defaultSampleRate']) if device_info['defaultSampleRate'] > 0 else 44100
                            })
                            
                except Exception as e:
                    print(f"Error evaluando dispositivo {i}: {e}")
                    continue
            
            temp_audio.terminate()
            
            # Establecer el dispositivo por defecto si hay dispositivos disponibles
            if self.audio_devices:
                self.selected_device.set(self.audio_devices[0]['display_name'])
            else:
                # Añadir dispositivo por defecto si no se encuentra ninguno compatible
                self.audio_devices.append({
                    'index': None,
                    'name': 'Dispositivo por defecto',
                    'display_name': 'Dispositivo por defecto del sistema',
                    'channels': 1,
                    'sample_rate': 44100
                })
                device_names.append('Dispositivo por defecto del sistema')
                self.selected_device.set('Dispositivo por defecto del sistema')
            
            return device_names
            
        except Exception as e:
            print(f"Error obteniendo dispositivos de audio: {e}")
            # Configuración de emergencia
            self.audio_devices = [{
                'index': None,
                'name': 'Dispositivo por defecto',
                'display_name': 'Dispositivo por defecto del sistema',
                'channels': 1,
                'sample_rate': 44100
            }]
            return ["Dispositivo por defecto del sistema"]
        
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Configurar el grid del root para que se expanda
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)  # Row 1 para el contenido principal
        
        # Crear barra de menús
        self.create_menu_bar()
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar el grid del frame principal
        main_frame.columnconfigure(0, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="Grabador de Audio con Detección de Volumen", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Monitor de volumen (PRIMER ELEMENTO)
        self.create_volume_monitor(main_frame, row=1)
        
        # Estado Actual (SEGUNDO ELEMENTO)
        self.create_status_frame(main_frame, row=2)
        
        # Estadísticas (TERCER ELEMENTO)
        self.create_statistics_frame(main_frame, row=3)
        
        # Botones (CUARTO ELEMENTO)
        self.create_buttons_frame(main_frame, row=4)
        
        # Inicializar la lista de dispositivos
        self.update_device_list()
        
    def create_menu_bar(self):
        """Crea la barra de menús"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menú Config único con submenús
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="⚙️ Config", menu=config_menu)
        
        # Submenú Audio
        config_menu.add_command(label="🎙️ Audio...", command=self.open_audio_config)
        
        # Submenú Grabación  
        config_menu.add_command(label="📊 Grabación...", command=self.open_recording_config)
        
        # Separador
        config_menu.add_separator()
        
        # Acerca de
        config_menu.add_command(label="ℹ️ Acerca de...", command=self.show_about)
        
    def create_volume_monitor(self, parent, row):
        """Crea el monitor de volumen"""
        volume_frame = ttk.LabelFrame(parent, text="Monitor de Volumen", padding="15")
        volume_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        volume_frame.columnconfigure(0, weight=1)
        
        self.volume_bar = ttk.Progressbar(volume_frame, length=400, mode='determinate')
        self.volume_bar.grid(row=0, column=0, pady=5, sticky=(tk.W, tk.E))
        
    def create_status_frame(self, parent, row):
        """Crea el frame de estado actual"""
        status_frame = ttk.LabelFrame(parent, text="Estado Actual", padding="15")
        status_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Estado:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.status, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Volumen actual:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.current_volume).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Tramo actual:").grid(row=2, column=0, sticky=tk.W)
        self.current_status_label = ttk.Label(status_frame, textvariable=self.will_save_current, font=('Arial', 10, 'bold'))
        self.current_status_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Tiempo transcurrido en el bucle actual
        ttk.Label(status_frame, text="Tiempo bucle:").grid(row=3, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.current_recording_time, font=('Arial', 10, 'bold')).grid(row=3, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Calidad actual:").grid(row=4, column=0, sticky=tk.W)
        self.quality_info = tk.StringVar(value=f"{self.RATE}Hz, {16}bit, {'Mono'}")
        ttk.Label(status_frame, textvariable=self.quality_info, font=('Arial', 9)).grid(row=4, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Micrófono:").grid(row=5, column=0, sticky=tk.W)
        self.mic_info = tk.StringVar(value="Seleccionar micrófono")
        ttk.Label(status_frame, textvariable=self.mic_info, font=('Arial', 9)).grid(row=5, column=1, sticky=tk.W, padx=(10, 0))
        
    def create_statistics_frame(self, parent, row):
        """Crea el frame de estadísticas"""
        stats_frame = ttk.LabelFrame(parent, text="Estadísticas", padding="15")
        stats_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        stats_frame.columnconfigure(1, weight=1)
        
        ttk.Label(stats_frame, text="Grabaciones guardadas:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(stats_frame, textvariable=self.recordings_saved, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(stats_frame, text="Grabaciones eliminadas:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(stats_frame, textvariable=self.recordings_deleted, font=('Arial', 10, 'bold')).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
    def create_buttons_frame(self, parent, row):
        """Crea el frame de botones"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, pady=20)
        
        self.start_button = ttk.Button(button_frame, text="🎙️ Iniciar Grabación", 
                                     command=self.start_recording)
        self.start_button.grid(row=0, column=0, padx=(0, 15))
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Detener Grabación", 
                                    command=self.stop_recording, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(15, 0))
        
    def update_device_list(self):
        """Actualiza la lista de dispositivos en el combobox"""
        try:
            device_names = []
            for device in self.audio_devices:
                device_names.append(device['display_name'])
            
            if hasattr(self, 'device_combo'):
                self.device_combo['values'] = device_names
                
        except Exception as e:
            print(f"Error actualizando lista de dispositivos: {e}")
            
    def open_audio_config(self):
        """Abre la ventana modal de configuración de audio"""
        # Crear ventana modal
        audio_window = tk.Toplevel(self.root)
        audio_window.title("Configuración de Audio")
        audio_window.geometry("550x550")
        audio_window.resizable(False, False)
        audio_window.transient(self.root)
        audio_window.grab_set()  # Modal
        
        # Centrar la ventana
        audio_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Frame principal
        main_frame = ttk.Frame(audio_window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = ttk.Label(main_frame, text="Configuración de Audio", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Selector de micrófono
        mic_frame = ttk.LabelFrame(main_frame, text="Selección de Micrófono", padding="15")
        mic_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(mic_frame, text="Micrófono:").pack(anchor="w")
        
        # Información adicional
        info_label = ttk.Label(mic_frame, 
                              text="Selecciona el dispositivo de entrada. Solo se muestran dispositivos compatibles con la configuración actual.",
                              font=('Arial', 9), foreground='gray', wraplength=450)
        info_label.pack(anchor="w", pady=(0, 10))
        
        # Frame para el combo y botón
        combo_frame = ttk.Frame(mic_frame)
        combo_frame.pack(fill="x", pady=5)
        
        device_combo = ttk.Combobox(combo_frame, textvariable=self.selected_device, 
                                   state="readonly")
        device_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        refresh_btn = ttk.Button(combo_frame, text="🔄 Refrescar Dispositivos", 
                               command=lambda: self.refresh_devices_modal(device_combo))
        refresh_btn.pack(side="right")
        
        # Configuración de calidad
        quality_frame = ttk.LabelFrame(main_frame, text="Calidad de Audio", padding="15")
        quality_frame.pack(fill="x", pady=(0, 20))
        
        # Información sobre calidad
        quality_info = ttk.Label(quality_frame, 
                               text="Configura la calidad de audio. Mayor frecuencia y bits = mejor calidad pero archivos más grandes.",
                               font=('Arial', 9), foreground='gray', wraplength=450)
        quality_info.pack(anchor="w", pady=(0, 15))
        
        # Frame para controles de calidad en grid
        controls_frame = ttk.Frame(quality_frame)
        controls_frame.pack(fill="x")
        
        # Frecuencia de muestreo
        ttk.Label(controls_frame, text="Frecuencia de muestreo:").grid(row=0, column=0, sticky="w", pady=5)
        sample_combo = ttk.Combobox(controls_frame, textvariable=self.sample_rate,
                                   values=["44100", "48000", "96000"], state="readonly", width=15)
        sample_combo.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
        
        # Profundidad de bits
        ttk.Label(controls_frame, text="Profundidad de bits:").grid(row=1, column=0, sticky="w", pady=5)
        bit_combo = ttk.Combobox(controls_frame, textvariable=self.bit_depth,
                                values=["16", "24", "32"], state="readonly", width=15)
        bit_combo.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)
        
        # Canales
        ttk.Label(controls_frame, text="Canales:").grid(row=2, column=0, sticky="w", pady=5)
        channels_combo = ttk.Combobox(controls_frame, textvariable=self.channels_mode,
                                     values=["Mono", "Estéreo"], state="readonly", width=15)
        channels_combo.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=5)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(button_frame, text="✅ Aplicar y Cerrar", 
                  command=lambda: self.apply_audio_config_modal(audio_window)).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="❌ Cancelar", 
                  command=audio_window.destroy).pack(side="right")
        
        # Inicializar valores en el modal
        device_combo['values'] = [device['display_name'] for device in self.audio_devices]
        
    def open_recording_config(self):
        """Abre la ventana modal de configuración de grabación"""
        # Crear ventana modal
        config_window = tk.Toplevel(self.root)
        config_window.title("Configuración de Grabación")
        config_window.geometry("450x550")
        config_window.resizable(False, False)
        config_window.transient(self.root)
        config_window.grab_set()  # Modal
        
        # Centrar la ventana
        config_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Frame principal
        main_frame = ttk.Frame(config_window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = ttk.Label(main_frame, text="Configuración de Grabación", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Umbral de volumen
        threshold_frame = ttk.LabelFrame(main_frame, text="Umbral de Volumen", padding="15")
        threshold_frame.pack(fill="x", pady=(0, 15))
        
        # Información sobre el umbral
        threshold_info = ttk.Label(threshold_frame,
                                 text="Solo se guardarán las grabaciones que superen este umbral de volumen. Valores más altos = más selectivo.",
                                 font=('Arial', 9), foreground='gray', wraplength=380)
        threshold_info.pack(anchor="w", pady=(0, 10))
        
        ttk.Label(threshold_frame, text="Umbral de volumen (dB):").pack(anchor="w")
        
        threshold_scale = ttk.Scale(threshold_frame, from_=self.config_min_threshold_db, to=self.config_max_threshold_db,
                                   variable=self.threshold_db, orient=tk.HORIZONTAL, length=300)
        threshold_scale.pack(fill="x", pady=8)
        
        self.threshold_label_modal = ttk.Label(threshold_frame, text=f"{self.threshold_db.get():.1f} dB")
        self.threshold_label_modal.pack(anchor="w")
        
        threshold_scale.configure(command=self.update_threshold_label_modal)
        
        # Duración de grabación
        duration_frame = ttk.LabelFrame(main_frame, text="Duración de Grabación", padding="15")
        duration_frame.pack(fill="x", pady=(0, 15))
        
        # Información sobre la duración
        duration_info = ttk.Label(duration_frame,
                                text="Duración de cada tramo de grabación. Tramos más largos detectan mejor el audio pero ocupan más espacio.",
                                font=('Arial', 9), foreground='gray', wraplength=380)
        duration_info.pack(anchor="w", pady=(0, 10))
        
        ttk.Label(duration_frame, text="Duración de grabación (segundos):").pack(anchor="w")
        
        duration_scale = ttk.Scale(duration_frame, from_=10, to=60,
                                  variable=self.record_duration, orient=tk.HORIZONTAL, length=300)
        duration_scale.pack(fill="x", pady=8)
        
        self.duration_label_modal = ttk.Label(duration_frame, text=f"{self.record_duration.get():.0f} seg")
        self.duration_label_modal.pack(anchor="w")
        
        duration_scale.configure(command=self.update_duration_label_modal)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(button_frame, text="✅ Aplicar", 
                  command=lambda: self.close_recording_config(config_window)).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="❌ Cancelar", 
                  command=config_window.destroy).pack(side="right")
                  
    def close_recording_config(self, window):
        """Cierra la ventana de configuración de grabación y guarda automáticamente"""
        try:
            # Guardar configuración automáticamente
            self.save_config(show_messages=True)
            window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error guardando configuración: {str(e)}")
            
    def show_about(self):
        """Muestra información acerca del programa"""
        about_text = """Grabador de Audio con Detección de Volumen v2.0
        
Características:
• Grabación continua con duración configurable
• Detección automática de volumen
• Selección de micrófono
• Alta calidad de audio configurable
• Guardado automático inteligente

Creado con Python y Tkinter"""
        
        messagebox.showinfo("Acerca de", about_text)
        
    def refresh_devices_modal(self, combo_widget):
        """Refresca los dispositivos en el modal de audio"""
        try:
            device_names = self.refresh_audio_devices()
            combo_widget['values'] = device_names
            self.update_device_list()
            
            if device_names and device_names[0] != "Error obteniendo dispositivos":
                messagebox.showinfo("Dispositivos actualizados", 
                                  f"Se encontraron {len(device_names)} dispositivos de entrada")
            else:
                messagebox.showwarning("Sin dispositivos", 
                                     "No se encontraron dispositivos de entrada disponibles")
        except Exception as e:
            messagebox.showerror("Error", f"Error refrescando dispositivos: {str(e)}")
            
    def apply_audio_config_modal(self, window):
        """Aplica la configuración de audio desde el modal y guarda en config.ini"""
        try:
            self.apply_audio_quality()
            # Guardar configuración actualizada
            self.save_config(show_messages=True)
            window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Error aplicando configuración: {str(e)}")
            
    def update_threshold_label_modal(self, value):
        """Actualiza la etiqueta del umbral en el modal y programa guardado automático"""
        if hasattr(self, 'threshold_label_modal'):
            self.threshold_label_modal.config(text=f"{float(value):.1f} dB")
            
        # Cancelar timer anterior si existe
        if hasattr(self, 'threshold_save_timer'):
            self.root.after_cancel(self.threshold_save_timer)
            
        # Programar guardado automático con retraso de 1 segundo
        self.threshold_save_timer = self.root.after(1000, self.save_config)
            
    def update_duration_label_modal(self, value):
        """Actualiza la etiqueta de duración en el modal y programa guardado automático"""
        if hasattr(self, 'duration_label_modal'):
            self.duration_label_modal.config(text=f"{float(value):.0f} seg")
            
        # Actualizar también el contador de tiempo si no estamos grabando
        if not self.is_recording:
            duration_int = int(float(value))
            self.current_recording_time.set(f"0/{duration_int} seg")
            
        # Cancelar timer anterior si existe
        if hasattr(self, 'duration_save_timer'):
            self.root.after_cancel(self.duration_save_timer)
            
        # Programar guardado automático con retraso de 1 segundo
        self.duration_save_timer = self.root.after(1000, self.save_config)
        
    def update_threshold_label(self, value):
        """Actualiza la etiqueta del umbral cuando cambia el slider (mantener para compatibilidad)"""
        pass  # No se usa en la nueva interfaz, pero se mantiene para evitar errores
        
    def update_duration_label(self, value):
        """Actualiza la etiqueta de duración cuando cambia el slider (mantener para compatibilidad)"""
        pass  # No se usa en la nueva interfaz, pero se mantiene para evitar errores
        
    def apply_audio_quality(self):
        """Aplica la configuración de calidad de audio con validación"""
        if self.is_recording:
            messagebox.showwarning("Advertencia", "No se puede cambiar la calidad durante la grabación")
            return
            
        try:
            # Obtener el dispositivo seleccionado
            device_index = self.get_selected_device_index()
            selected_device_info = None
            
            for device in self.audio_devices:
                if device['index'] == device_index:
                    selected_device_info = device
                    break
            
            # Configuración propuesta
            proposed_rate = int(self.sample_rate.get())
            proposed_bit_depth = int(self.bit_depth.get())
            proposed_channels = 2 if self.channels_mode.get() == "Estéreo" else 1
            
            # Validar con el dispositivo seleccionado
            if selected_device_info:
                # Ajustar canales según las capacidades del dispositivo
                max_device_channels = selected_device_info.get('channels', 1)
                if proposed_channels > max_device_channels:
                    proposed_channels = max_device_channels
                    self.channels_mode.set("Mono" if proposed_channels == 1 else "Estéreo")
                    messagebox.showwarning("Ajuste automático", 
                                         f"El dispositivo seleccionado solo soporta {max_device_channels} canal(es). "
                                         f"Configurando a {'Mono' if proposed_channels == 1 else 'Estéreo'}.")
            
            # Probar la configuración antes de aplicarla
            test_audio = pyaudio.PyAudio()
            
            # Determinar formato
            if proposed_bit_depth == 16:
                test_format = pyaudio.paInt16
            elif proposed_bit_depth == 24:
                test_format = pyaudio.paInt24
            elif proposed_bit_depth == 32:
                test_format = pyaudio.paInt32
            else:
                test_format = pyaudio.paInt16  # Fallback
                
            try:
                # Intentar abrir con la configuración propuesta
                test_stream = test_audio.open(
                    format=test_format,
                    channels=proposed_channels,
                    rate=proposed_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024
                )
                test_stream.close()
                
                # Si llegamos aquí, la configuración es válida
                self.RATE = proposed_rate
                self.FORMAT = test_format
                self.CHANNELS = proposed_channels
                
                # Ajustar chunk size según la calidad
                if self.RATE >= 96000:
                    self.CHUNK = 4096
                elif self.RATE >= 48000:
                    self.CHUNK = 2048
                else:
                    self.CHUNK = 1024
                    
            except Exception as e:
                # Si falla, usar configuración segura
                print(f"Configuración propuesta falló: {e}")
                messagebox.showwarning("Configuración no soportada", 
                                     "La configuración seleccionada no es compatible. Usando configuración estándar segura.")
                
                # Configuración de emergencia
                self.RATE = 44100
                self.FORMAT = pyaudio.paInt16
                self.CHANNELS = 1
                self.CHUNK = 1024
                
                # Actualizar los controles
                self.sample_rate.set("44100")
                self.bit_depth.set("16")
                self.channels_mode.set("Mono")
                
            test_audio.terminate()
            
            # Actualizar la información de calidad mostrada
            bit_depth_display = "16" if self.FORMAT == pyaudio.paInt16 else "24" if self.FORMAT == pyaudio.paInt24 else "32"
            channels_text = 'Estéreo' if self.CHANNELS == 2 else 'Mono'
            self.quality_info.set(f"{self.RATE}Hz, {bit_depth_display}bit, {channels_text}")
            
            # Actualizar información del micrófono
            selected_name = self.selected_device.get()
            if selected_name and selected_name != "Dispositivo por defecto del sistema":
                # Extraer solo el nombre del dispositivo (sin el ID)
                mic_name = selected_name.split(' (ID:')[0]
                if len(mic_name) > 25:
                    mic_name = mic_name[:25] + "..."
                self.mic_info.set(mic_name)
            else:
                self.mic_info.set("Dispositivo por defecto")
                
            messagebox.showinfo("Éxito", 
                f"Configuración aplicada correctamente:\n"
                f"• Frecuencia: {self.RATE} Hz\n"
                f"• Bits: {bit_depth_display} bits\n"
                f"• Canales: {self.CHANNELS} ({channels_text})\n"
                f"• Buffer: {self.CHUNK} frames\n"
                f"• Micrófono: {self.mic_info.get()}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al aplicar configuración: {str(e)}\nUsando configuración por defecto.")
            # Configuración de emergencia
            self.RATE = 44100
            self.FORMAT = pyaudio.paInt16
            self.CHANNELS = 1
            self.CHUNK = 1024
    def refresh_devices_ui(self):
        """Refresca la lista de dispositivos de audio en la interfaz (mantener para compatibilidad)"""
        try:
            device_names = self.refresh_audio_devices()
            self.update_device_list()
            
            if device_names and device_names[0] != "Error obteniendo dispositivos":
                messagebox.showinfo("Dispositivos actualizados", 
                                  f"Se encontraron {len(device_names)} dispositivos de entrada")
            else:
                messagebox.showwarning("Sin dispositivos", 
                                     "No se encontraron dispositivos de entrada disponibles")
                                     
        except Exception as e:
            messagebox.showerror("Error", f"Error refrescando dispositivos: {str(e)}")
            
    def get_selected_device_index(self):
        """Obtiene el índice del dispositivo seleccionado"""
        selected_name = self.selected_device.get()
        
        for device in self.audio_devices:
            if device['display_name'] == selected_name:
                return device['index']
                
        return None  # Usar dispositivo por defecto si no se encuentra
        
    def calculate_db(self, audio_data):
        """Calcula el nivel de volumen en decibelios con soporte para múltiples formatos"""
        if len(audio_data) == 0:
            return -60  # Silencio
            
        try:
            # Determinar el tipo de datos y valor máximo según el formato
            if self.FORMAT == pyaudio.paInt16:
                audio_float = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                max_val = 32767.0
            elif self.FORMAT == pyaudio.paInt24:
                # Para 24-bit, necesitamos procesamiento especial
                audio_bytes = np.frombuffer(audio_data, dtype=np.uint8)
                # Convertir de 3 bytes a int32
                audio_int = np.zeros(len(audio_bytes) // 3, dtype=np.int32)
                for i in range(len(audio_int)):
                    # Little endian: byte0 + byte1*256 + byte2*65536
                    audio_int[i] = (audio_bytes[i*3] + 
                                   (audio_bytes[i*3+1] << 8) + 
                                   (audio_bytes[i*3+2] << 16))
                    # Convertir a signed
                    if audio_int[i] >= 2**23:
                        audio_int[i] -= 2**24
                audio_float = audio_int.astype(np.float32)
                max_val = 8388607.0  # 2^23 - 1
            elif self.FORMAT == pyaudio.paInt32:
                audio_float = np.frombuffer(audio_data, dtype=np.int32).astype(np.float32)
                max_val = 2147483647.0  # 2^31 - 1
            else:
                # Fallback para otros formatos
                audio_float = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                max_val = 32767.0
                
            # Si es estéreo, calcular el RMS de ambos canales
            if self.CHANNELS == 2 and len(audio_float) > 1:
                # Separar canales izquierdo y derecho
                left = audio_float[0::2]
                right = audio_float[1::2]
                # Calcular RMS de ambos canales y tomar el máximo
                rms_left = np.sqrt(np.mean(left**2))
                rms_right = np.sqrt(np.mean(right**2))
                rms = max(rms_left, rms_right)
            else:
                # Calcular RMS normal
                rms = np.sqrt(np.mean(audio_float**2))
            
            if rms == 0:
                return -60  # Silencio
                
            # Convertir a decibelios
            db = 20 * np.log10(rms / max_val)
            
            return max(db, -60)  # Limitar a -60 dB como mínimo
            
        except Exception as e:
            print(f"Error calculando dB: {e}")
            return -60  # Silencio en caso de error
        
    def record_audio_chunk(self):
        """Graba un chunk de audio con duración configurable y manejo robusto de errores"""
        try:
            # Reiniciar el estado del tramo actual
            self.current_max_volume = -60.0
            self.root.after(0, self.update_current_status, "Grabando...")
            
            # Obtener el índice del dispositivo seleccionado
            device_index = self.get_selected_device_index()
            
            # Intentar abrir el stream con manejo de errores
            stream = None
            try:
                stream = self.audio.open(format=self.FORMAT,
                                       channels=self.CHANNELS,
                                       rate=self.RATE,
                                       input=True,
                                       input_device_index=device_index,
                                       frames_per_buffer=self.CHUNK)
            except Exception as e:
                print(f"Error abriendo stream con dispositivo específico: {e}")
                # Intentar con dispositivo por defecto
                try:
                    stream = self.audio.open(format=self.FORMAT,
                                           channels=self.CHANNELS,
                                           rate=self.RATE,
                                           input=True,
                                           frames_per_buffer=self.CHUNK)
                    print("Usando dispositivo por defecto")
                except Exception as e2:
                    print(f"Error abriendo stream con dispositivo por defecto: {e2}")
                    # Último intento con configuración mínima
                    try:
                        stream = self.audio.open(format=pyaudio.paInt16,
                                               channels=1,
                                               rate=44100,
                                               input=True,
                                               frames_per_buffer=1024)
                        print("Usando configuración de emergencia")
                        # Actualizar configuración actual
                        self.FORMAT = pyaudio.paInt16
                        self.CHANNELS = 1
                        self.RATE = 44100
                        self.CHUNK = 1024
                    except Exception as e3:
                        raise Exception(f"No se pudo abrir ningún stream de audio: {e3}")
            
            if stream is None:
                raise Exception("No se pudo crear el stream de audio")
            
            frames = []
            max_volume_db = -60
            record_seconds = self.record_duration.get()
            
            # Inicializar el tiempo de inicio
            import time as time_module
            self.recording_start_time = time_module.time()
            
            # Calcular cuántos chunks necesitamos para la duración seleccionada
            chunks_needed = int(self.RATE / self.CHUNK * record_seconds)
            
            for i in range(chunks_needed):
                if not self.is_recording:
                    break
                    
                try:
                    data = stream.read(self.CHUNK, exception_on_overflow=False)
                    frames.append(data)
                    
                    # Calcular tiempo transcurrido
                    elapsed_time = time_module.time() - self.recording_start_time
                    elapsed_seconds = int(elapsed_time)
                    total_seconds = int(record_seconds)
                    
                    # Actualizar tiempo en la interfaz
                    self.root.after(0, lambda: self.current_recording_time.set(f"{elapsed_seconds}/{total_seconds} seg"))
                    
                    # Calcular volumen actual
                    current_db = self.calculate_db(data)
                    max_volume_db = max(max_volume_db, current_db)
                    self.current_max_volume = max_volume_db
                    
                    # Actualizar UI en el hilo principal
                    self.root.after(0, self.update_volume_display, current_db)
                    self.root.after(0, self.update_current_status_by_volume)
                    
                except Exception as e:
                    print(f"Error leyendo datos de audio: {e}")
                    # Continuar con el siguiente chunk
                    continue
                
            stream.stop_stream()
            stream.close()
            
            return frames, max_volume_db
            
        except Exception as e:
            print(f"Error en record_audio_chunk: {e}")
            messagebox.showerror("Error de Grabación", 
                               f"Error durante la grabación: {str(e)}\n\n"
                               "Sugerencias:\n"
                               "• Verificar que el micrófono esté conectado\n"
                               "• Probar con configuración más simple (16-bit, Mono, 44.1kHz)\n"
                               "• Seleccionar otro dispositivo de audio")
            return None, -60
            
    def update_volume_display(self, db_level):
        """Actualiza la visualización del volumen"""
        self.current_volume.set(f"{db_level:.1f} dB")
        
        # Actualizar barra de progreso (convertir dB a porcentaje)
        # -60 dB = 0%, 0 dB = 100%
        percentage = max(0, min(100, (db_level + 60) * 100 / 60))
        self.volume_bar['value'] = percentage
        
    def update_current_status(self, status_text):
        """Actualiza el texto de estado del tramo actual"""
        self.will_save_current.set(status_text)
        
    def update_current_status_by_volume(self):
        """Actualiza el estado del tramo actual basado en el volumen máximo detectado"""
        threshold = self.threshold_db.get()
        if self.current_max_volume >= threshold:
            self.will_save_current.set(f"✅ SE GUARDARÁ (Max: {self.current_max_volume:.1f} dB)")
            # Cambiar color a verde
            self.current_status_label.config(foreground='green')
        else:
            self.will_save_current.set(f"❌ Se eliminará (Max: {self.current_max_volume:.1f} dB)")
            # Cambiar color a rojo
            self.current_status_label.config(foreground='red')
        
    def save_recording(self, frames, timestamp=None):
        """Guarda la grabación en un archivo WAV con validación robusta"""
        try:
            # Generar nombre de archivo usando el formato de config.ini
            if timestamp is None:
                timestamp = datetime.now()
            
            # Usar el formato de nombre desde la configuración
            if hasattr(self, 'config_filename_format'):
                filename = timestamp.strftime(self.config_filename_format)
            else:
                filename = f"grabacion_{timestamp.strftime('%Y%m%d_%H%M%S')}.wav"
                
            filepath = os.path.join(self.output_dir, filename)
            # Validar que tenemos frames para guardar
            if not frames or len(frames) == 0:
                print("No hay datos de audio para guardar")
                return
                
            # Obtener información del formato actual
            sample_width = self.audio.get_sample_size(self.FORMAT)
            channels = self.CHANNELS
            framerate = self.RATE
            
            print(f"Guardando audio: {channels} canales, {framerate}Hz, {sample_width} bytes por muestra")
            
            # Crear archivo WAV
            wf = wave.open(filepath, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(framerate)
            
            # Concatenar todos los frames
            audio_data = b''.join(frames)
            
            # Validar que tenemos datos
            if len(audio_data) == 0:
                print("Datos de audio vacíos")
                wf.close()
                return
            
            # Escribir datos
            wf.writeframes(audio_data)
            wf.close()
            
            # Verificar que el archivo se creó correctamente
            if os.path.exists(filepath) and os.path.getsize(filepath) > 44:  # 44 bytes = header WAV mínimo
                self.recordings_saved.set(self.recordings_saved.get() + 1)
                print(f"Grabación guardada exitosamente: {filepath}")
                print(f"Tamaño del archivo: {os.path.getsize(filepath)} bytes")
            else:
                print(f"Error: El archivo no se creó correctamente o está vacío")
                
        except Exception as e:
            error_msg = f"Error al guardar la grabación: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error de Guardado", error_msg)
            
            # Intentar crear un archivo de prueba con configuración básica
            try:
                print("Intentando guardar con configuración básica...")
                wf = wave.open(filepath, 'wb')
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(44100)  # 44.1 kHz
                
                # Si los frames están en formato diferente, intentar convertir
                if frames:
                    audio_data = b''.join(frames)
                    wf.writeframes(audio_data)
                
                wf.close()
                print("Archivo guardado con configuración básica")
                
            except Exception as e2:
                print(f"Error también con configuración básica: {e2}")
                messagebox.showerror("Error Crítico", 
                                   f"No se pudo guardar el archivo de audio.\n"
                                   f"Error original: {str(e)}\n"
                                   f"Error de respaldo: {str(e2)}")
            
    def recording_loop(self):
        """Bucle principal de grabación"""
        while self.is_recording:
            timestamp = datetime.now()  # Pasar objeto datetime completo
            
            # Grabar con duración configurable
            duration = self.record_duration.get()
            self.status.set(f"Grabando ({duration:.0f}s)...")
            frames, max_volume = self.record_audio_chunk()
            
            if frames is None:
                break
                
            # Verificar si el volumen superó el umbral
            threshold = self.threshold_db.get()
            
            if max_volume >= threshold:
                # Guardar la grabación
                self.save_recording(frames, timestamp)
                self.status.set(f"Grabación guardada (Vol: {max_volume:.1f} dB)")
                self.root.after(0, self.update_current_status, f"✅ GUARDADA ({max_volume:.1f} dB)")
                self.root.after(0, lambda: self.current_status_label.config(foreground='green'))
            else:
                # Descartar la grabación
                self.recordings_deleted.set(self.recordings_deleted.get() + 1)
                self.status.set(f"Grabación descartada (Vol: {max_volume:.1f} dB)")
                self.root.after(0, self.update_current_status, f"❌ ELIMINADA ({max_volume:.1f} dB)")
                self.root.after(0, lambda: self.current_status_label.config(foreground='red'))
                
            # Pequeña pausa antes del siguiente ciclo
            if self.is_recording:
                # Resetear el contador de tiempo para mostrar que esperamos el próximo ciclo
                duration_int = int(duration)
                self.root.after(0, lambda: self.current_recording_time.set(f"0/{duration_int} seg"))
                
                time.sleep(2)  # Pausa un poco más larga para mostrar el resultado
                self.root.after(0, self.update_current_status, "Esperando...")
                self.root.after(0, lambda: self.current_status_label.config(foreground='black'))
                time.sleep(1)
                
    def start_recording(self):
        """Inicia la grabación en bucle"""
        try:
            self.audio = pyaudio.PyAudio()
            self.is_recording = True
            
            # Deshabilitar botón de inicio y habilitar el de parar
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Iniciar el hilo de grabación
            self.recording_thread = threading.Thread(target=self.recording_loop, daemon=True)
            self.recording_thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar la grabación: {str(e)}")
            self.stop_recording()
            
    def stop_recording(self):
        """Detiene la grabación"""
        self.is_recording = False
        self.status.set("Detenido")
        
        # Resetear el estado del tramo actual
        self.will_save_current.set("Esperando...")
        self.current_status_label.config(foreground='black')
        
        # Resetear el contador de tiempo
        duration = int(self.record_duration.get())
        self.current_recording_time.set(f"0/{duration} seg")
        
        # Habilitar botón de inicio y deshabilitar el de parar
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # Cerrar PyAudio
        if self.audio:
            self.audio.terminate()
            self.audio = None
            
    def on_closing(self):
        """Maneja el cierre de la aplicación y guarda la configuración"""
        if self.is_recording:
            self.stop_recording()
        # Guardar configuración antes de cerrar
        self.save_config(show_messages=False)  # Sin mensajes al cerrar
        self.root.destroy()
        
    def run(self):
        """Ejecuta la aplicación"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    # Verificar dependencias
    try:
        import pyaudio
        import numpy
    except ImportError as e:
        print(f"Error: Falta instalar dependencias: {e}")
        print("Ejecuta: pip install pyaudio numpy")
        exit(1)
        
    app = AudioRecorder()
    app.run()