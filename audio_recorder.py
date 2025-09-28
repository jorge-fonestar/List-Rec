import kivy
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window

import pyaudio
import wave
import numpy as np
import threading
import os
from datetime import datetime
import time
import configparser

class AudioRecorderApp(App):
    def build(self):
        # Configurar ventana
        Window.title = "Grabador de Audio con Detección de Volumen"
        Window.size = (500, 600)
        Window.minimum_width = 400
        Window.minimum_height = 500
        
        # Crear instancia del grabador
        self.recorder = AudioRecorder()
        return self.recorder.setup_ui()
    
    def on_stop(self):
        """Método de Kivy llamado cuando la aplicación se cierra"""
        if hasattr(self, 'recorder'):
            self.recorder.on_closing()
        return super().on_stop()

class AudioRecorder:
    def __init__(self):
        # Archivo de configuración
        self.config_file = "config.ini"
        
        # Cargar configuración desde archivo
        self.load_config()
        
        # Configuración de audio - Cargada desde config.ini
        self.CHUNK = self.config_chunk_size
        self.FORMAT = self.config_format
        self.CHANNELS = self.config_channels
        self.RATE = self.config_sample_rate
        # RECORD_SECONDS será definido dinámicamente desde self.record_duration
        
        # Variables de estado - Inicializadas desde config.ini
        self.is_recording = False
        self.audio = None
        self.threshold_db = self.config_threshold_db
        self.record_duration = self.config_record_seconds
        self.current_volume_text = "0.0 dB"
        self.status_text = "Detenido"
        self.recordings_saved_count = 0
        self.recordings_deleted_count = 0
        self.will_save_current_text = "Esperando..."  # Estado del tramo actual
        self.current_max_volume = -60.0  # Volumen máximo del tramo actual
        
        # Variables para tracking de tiempo
        self.recording_start_time = 0  # Tiempo de inicio de la grabación actual
        self.current_recording_time_text = "0/30 seg"  # Tiempo transcurrido/total
        
        # Variables para calidad de audio - Inicializadas desde config.ini
        self.sample_rate_text = str(self.config_sample_rate)
        self.bit_depth_text = str(self.config_bit_depth)
        self.channels_mode_text = "Estéreo" if self.config_channels == 2 else "Mono"
        self.selected_device_text = ""  # Dispositivo de audio seleccionado
        self.audio_devices = []  # Lista de dispositivos disponibles
        
        # Directorio para guardar grabaciones - Desde config.ini
        self.output_dir = self.config_output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Referencias a widgets Kivy (se asignarán en setup_ui)
        self.volume_bar = None
        self.current_volume_label = None
        self.status_label = None
        self.current_status_label = None
        self.recordings_saved_label = None
        self.recordings_deleted_label = None
        self.start_button = None
        self.stop_button = None
            
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
            config.set('AUDIO', 'RECORD_SECONDS', str(int(self.record_duration)))
            config.set('AUDIO', 'SAMPLE_RATE', str(self.RATE))
            config.set('AUDIO', 'CHANNELS', str(self.CHANNELS))
            config.set('AUDIO', 'FORMAT', str(self.config_bit_depth))
            config.set('AUDIO', 'CHUNK_SIZE', str(self.CHUNK))
            
            config.set('INTERFACE', 'DEFAULT_THRESHOLD_DB', str(self.threshold_db))
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
                f.write(f"RECORD_SECONDS = {int(self.record_duration)}\n\n")
                
                f.write(f"# Calidad de audio\n")
                f.write(f"SAMPLE_RATE = {self.RATE}  # Hz\n")
                f.write(f"CHANNELS = {self.CHANNELS}  # 1 = mono, 2 = estéreo\n")
                f.write(f"FORMAT = {self.config_bit_depth}  # bits\n\n")
                
                f.write(f"# Tamaño del buffer\n")
                f.write(f"CHUNK_SIZE = {self.CHUNK}\n\n")
                
                f.write("[INTERFACE]\n")
                f.write(f"# Umbral por defecto en decibelios\n")
                f.write(f"DEFAULT_THRESHOLD_DB = {self.threshold_db}\n\n")
                
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
                self.show_message("Error", f"No se pudo guardar la configuración: {str(e)}", "error")
        
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
                self.selected_device_name = self.audio_devices[0]['display_name']
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
                self.selected_device_name = 'Dispositivo por defecto del sistema'
            
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
        """Configura la interfaz de usuario en Kivy"""
        # Layout principal
        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Título
        title_label = Label(
            text="Grabador de Audio con Detección de Volumen",
            size_hint_y=None,
            height=dp(40),
            font_size='18sp',
            bold=True,
            color=(0.2, 0.2, 0.2, 1)
        )
        main_layout.add_widget(title_label)
        
        # Monitor de volumen
        volume_layout = self.create_volume_monitor()
        main_layout.add_widget(volume_layout)
        
        # Estado actual
        status_layout = self.create_status_frame()
        main_layout.add_widget(status_layout)
        
        # Estadísticas
        stats_layout = self.create_statistics_frame()
        main_layout.add_widget(stats_layout)
        
        # Botones
        buttons_layout = self.create_buttons_frame()
        main_layout.add_widget(buttons_layout)
        
        # Menú mediante botones
        menu_layout = self.create_menu_bar()
        main_layout.add_widget(menu_layout)
        
        return main_layout
        
    def create_menu_bar(self):
        """Crea una barra de menús usando botones"""
        menu_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        # Botón de configuración de audio
        audio_btn = Button(
            text="Audio",
            size_hint_x=None,
            width=dp(100),
            on_press=self.open_audio_config
        )
        menu_layout.add_widget(audio_btn)
        
        # Botón de configuración de grabación
        recording_btn = Button(
            text="Grabación",
            size_hint_x=None,
            width=dp(120),
            on_press=self.open_recording_config
        )
        menu_layout.add_widget(recording_btn)
        
        # Espacio flexible
        menu_layout.add_widget(Label())
        
        # Botón de salir
        exit_btn = Button(
            text="Salir",
            size_hint_x=None,
            width=dp(100),
            on_press=self.show_exit_confirmation
        )
        menu_layout.add_widget(exit_btn)
        
        return menu_layout
        
    def create_volume_monitor(self):
        """Crea el monitor de volumen"""
        # Layout contenedor
        container = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100), spacing=dp(10))
        
        # Título
        title = Label(
            text="Monitor de Volumen",
            size_hint_y=None,
            height=dp(30),
            font_size='14sp',
            bold=True
        )
        container.add_widget(title)
        
        # Barra de progreso
        self.volume_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(20)
        )
        container.add_widget(self.volume_bar)
        
        return container
        
    def create_status_frame(self):
        """Crea el frame de estado actual"""
        # Layout contenedor
        container = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(180), spacing=dp(5))
        
        # Título
        title = Label(
            text="Estado Actual",
            size_hint_y=None,
            height=dp(30),
            font_size='14sp',
            bold=True
        )
        container.add_widget(title)
        
        # Grid de información
        info_grid = GridLayout(cols=2, size_hint_y=None, height=dp(150), spacing=dp(10))
        
        # Estado
        info_grid.add_widget(Label(text="Estado:", halign='left', valign='middle'))
        self.status_label = Label(text=self.status_text, halign='left', valign='middle', bold=True)
        info_grid.add_widget(self.status_label)
        
        # Volumen actual
        info_grid.add_widget(Label(text="Volumen actual:", halign='left', valign='middle'))
        self.current_volume_label = Label(text=self.current_volume_text, halign='left', valign='middle')
        info_grid.add_widget(self.current_volume_label)
        
        # Tramo actual
        info_grid.add_widget(Label(text="Tramo actual:", halign='left', valign='middle'))
        self.current_status_label = Label(text=self.will_save_current_text, halign='left', valign='middle', bold=True)
        info_grid.add_widget(self.current_status_label)
        
        # Tiempo de bucle
        info_grid.add_widget(Label(text="Tiempo bucle:", halign='left', valign='middle'))
        self.current_recording_time_label = Label(text=self.current_recording_time_text, halign='left', valign='middle', bold=True)
        info_grid.add_widget(self.current_recording_time_label)
        
        # Calidad actual
        quality_text = f"{self.RATE}Hz, {16}bit, {'Mono'}"
        info_grid.add_widget(Label(text="Calidad actual:", halign='left', valign='middle'))
        self.quality_info_label = Label(text=quality_text, halign='left', valign='middle', font_size='12sp')
        info_grid.add_widget(self.quality_info_label)
        
        # Micrófono
        info_grid.add_widget(Label(text="Micrófono:", halign='left', valign='middle'))
        self.mic_info_label = Label(text="Seleccionar micrófono", halign='left', valign='middle', font_size='12sp')
        info_grid.add_widget(self.mic_info_label)
        
        container.add_widget(info_grid)
        return container
        
    def create_statistics_frame(self):
        """Crea el frame de estadísticas"""
        # Layout contenedor
        container = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100), spacing=dp(10))
        
        # Título
        title = Label(
            text="Estadísticas",
            size_hint_y=None,
            height=dp(30),
            font_size='14sp',
            bold=True
        )
        container.add_widget(title)
        
        # Grid de estadísticas
        stats_grid = GridLayout(cols=2, size_hint_y=None, height=dp(60), spacing=dp(10))
        
        # Grabaciones guardadas
        stats_grid.add_widget(Label(text="Grabaciones guardadas:", halign='left', valign='middle'))
        self.recordings_saved_label = Label(text=str(self.recordings_saved_count), halign='left', valign='middle', bold=True)
        stats_grid.add_widget(self.recordings_saved_label)
        
        # Grabaciones eliminadas
        stats_grid.add_widget(Label(text="Grabaciones eliminadas:", halign='left', valign='middle'))
        self.recordings_deleted_label = Label(text=str(self.recordings_deleted_count), halign='left', valign='middle', bold=True)
        stats_grid.add_widget(self.recordings_deleted_label)
        
        container.add_widget(stats_grid)
        return container
        
    def create_buttons_frame(self):
        """Crea el frame de botones"""
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), spacing=dp(20))
        
        # Botón iniciar
        self.start_button = Button(
            text="Iniciar Grabación",
            size_hint_x=0.5,
            on_press=self.start_recording
        )
        button_layout.add_widget(self.start_button)
        
        # Botón detener
        self.stop_button = Button(
            text="Detener Grabación",
            size_hint_x=0.5,
            disabled=True,
            on_press=self.stop_recording
        )
        button_layout.add_widget(self.stop_button)
        
        return button_layout
        
    def update_device_list(self):
        """Actualiza la lista de dispositivos (mantener para compatibilidad)"""
        pass  # No se usa en Kivy, pero mantenemos para compatibilidad
        
    def show_message(self, title, message, message_type="info"):
        """Muestra un mensaje usando popup de Kivy"""
        popup_content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        
        # Mensaje
        message_label = Label(
            text=message,
            text_size=(dp(300), None),
            halign='center',
            valign='middle'
        )
        popup_content.add_widget(message_label)
        
        # Botón cerrar
        close_btn = Button(
            text="Cerrar",
            size_hint_y=None,
            height=dp(40),
            on_press=lambda x: popup.dismiss()
        )
        popup_content.add_widget(close_btn)
        
        popup = Popup(
            title=title,
            content=popup_content,
            size_hint=(0.8, 0.4)
        )
        popup.open()
        
    def on_threshold_change(self, instance, value):
        """Actualiza el valor del umbral cuando cambia el slider"""
        self.threshold_db = value
        if hasattr(self, 'threshold_value_label'):
            self.threshold_value_label.text = f"{value:.1f} dB"
        # Programar guardado automático
        Clock.unschedule(self.save_config)
        Clock.schedule_once(lambda dt: self.save_config(show_messages=False), 1)
        
    def on_duration_change(self, instance, value):
        """Actualiza el valor de duración cuando cambia el slider"""
        self.record_duration = value
        if hasattr(self, 'duration_value_label'):
            self.duration_value_label.text = f"{value:.0f} seg"
        # Actualizar contador si no estamos grabando
        if not self.is_recording:
            self.current_recording_time_text = f"0/{int(value)} seg"
            if hasattr(self, 'current_recording_time_label'):
                self.current_recording_time_label.text = self.current_recording_time_text
        # Programar guardado automático
        Clock.unschedule(self.save_config)
        Clock.schedule_once(lambda dt: self.save_config(show_messages=False), 1)
            
    def open_audio_config(self, instance=None):
        """Abre la configuración de audio en un popup"""
        # Contenido del popup
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Título
        title_label = Label(
            text="Configuración de Audio",
            size_hint_y=None,
            height=dp(30),
            font_size='16sp',
            bold=True
        )
        content.add_widget(title_label)
        
        # Selector de micrófono
        mic_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120), spacing=dp(10))
        mic_layout.add_widget(Label(text="Selección de Micrófono", font_size='14sp', bold=True, size_hint_y=None, height=dp(25)))
        
        device_names = [device['display_name'] for device in self.audio_devices]
        if not device_names:
            device_names = ["Dispositivo por defecto del sistema"]
            
        self.device_spinner = Spinner(
            text=self.selected_device_text or (device_names[0] if device_names else "No disponible"),
            values=device_names,
            size_hint_y=None,
            height=dp(40)
        )
        mic_layout.add_widget(self.device_spinner)
        
        refresh_btn = Button(
            text="Refrescar Dispositivos",
            size_hint_y=None,
            height=dp(35),
            on_press=self.refresh_devices_popup
        )
        mic_layout.add_widget(refresh_btn)
        content.add_widget(mic_layout)
        
        # Configuración de calidad
        quality_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(180), spacing=dp(10))
        quality_layout.add_widget(Label(text="Calidad de Audio", font_size='14sp', bold=True, size_hint_y=None, height=dp(25)))
        
        # Frecuencia de muestreo
        sample_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35))
        sample_layout.add_widget(Label(text="Frecuencia:", size_hint_x=0.4))
        self.sample_rate_spinner = Spinner(
            text=self.sample_rate_text,
            values=["44100", "48000", "96000"],
            size_hint_x=0.6
        )
        sample_layout.add_widget(self.sample_rate_spinner)
        quality_layout.add_widget(sample_layout)
        
        # Profundidad de bits
        bit_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35))
        bit_layout.add_widget(Label(text="Bits:", size_hint_x=0.4))
        self.bit_depth_spinner = Spinner(
            text=self.bit_depth_text,
            values=["16", "24", "32"],
            size_hint_x=0.6
        )
        bit_layout.add_widget(self.bit_depth_spinner)
        quality_layout.add_widget(bit_layout)
        
        # Canales
        channels_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(35))
        channels_layout.add_widget(Label(text="Canales:", size_hint_x=0.4))
        self.channels_spinner = Spinner(
            text=self.channels_mode_text,
            values=["Mono", "Estéreo"],
            size_hint_x=0.6
        )
        channels_layout.add_widget(self.channels_spinner)
        quality_layout.add_widget(channels_layout)
        content.add_widget(quality_layout)
        
        # Botones
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        cancel_btn = Button(
            text="Cancelar",
            size_hint_x=0.5,
            on_press=lambda x: popup.dismiss()
        )
        buttons_layout.add_widget(cancel_btn)
        
        apply_btn = Button(
            text="Aplicar",
            size_hint_x=0.5,
            on_press=lambda x: self.apply_audio_config_popup(popup)
        )
        buttons_layout.add_widget(apply_btn)
        content.add_widget(buttons_layout)
        
        # Crear popup
        popup = Popup(
            title="Configuración de Audio",
            content=content,
            size_hint=(0.9, 0.8)
        )
        popup.open()
        
    def refresh_devices_popup(self, instance=None):
        """Refresca los dispositivos en el popup"""
        try:
            device_names = self.refresh_audio_devices()
            if hasattr(self, 'device_spinner'):
                self.device_spinner.values = device_names
            self.show_message("Dispositivos actualizados", f"Se encontraron {len(device_names)} dispositivos")
        except Exception as e:
            self.show_message("Error", f"Error refrescando dispositivos: {str(e)}")
        
    def apply_audio_config_popup(self, popup):
        """Aplica la configuración de audio desde el popup"""
        try:
            # Actualizar valores desde los spinners
            if hasattr(self, 'device_spinner'):
                self.selected_device_text = self.device_spinner.text
            if hasattr(self, 'sample_rate_spinner'):
                self.sample_rate_text = self.sample_rate_spinner.text
            if hasattr(self, 'bit_depth_spinner'):
                self.bit_depth_text = self.bit_depth_spinner.text
            if hasattr(self, 'channels_spinner'):
                self.channels_mode_text = self.channels_spinner.text
                
            self.apply_audio_quality()
            self.save_config(show_messages=True)
            popup.dismiss()
        except Exception as e:
            self.show_message("Error", f"Error aplicando configuración: {str(e)}")
        
    def open_recording_config(self, instance=None):
        """Abre la configuración de grabación en un popup"""
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Título
        title_label = Label(
            text="Configuración de Grabación",
            size_hint_y=None,
            height=dp(30),
            font_size='16sp',
            bold=True
        )
        content.add_widget(title_label)
        
        # Umbral de volumen
        threshold_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120), spacing=dp(10))
        threshold_layout.add_widget(Label(text="Umbral de Volumen (dB)", font_size='14sp', bold=True, size_hint_y=None, height=dp(25)))
        
        self.threshold_slider = Slider(
            min=self.config_min_threshold_db,
            max=self.config_max_threshold_db,
            value=self.threshold_db,
            step=1,
            size_hint_y=None,
            height=dp(30)
        )
        self.threshold_slider.bind(value=self.on_threshold_change)
        threshold_layout.add_widget(self.threshold_slider)
        
        self.threshold_value_label = Label(
            text=f"{self.threshold_db:.1f} dB",
            size_hint_y=None,
            height=dp(25)
        )
        threshold_layout.add_widget(self.threshold_value_label)
        content.add_widget(threshold_layout)
        
        # Duración de grabación
        duration_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120), spacing=dp(10))
        duration_layout.add_widget(Label(text="Duración de Grabación (segundos)", font_size='14sp', bold=True, size_hint_y=None, height=dp(25)))
        
        self.duration_slider = Slider(
            min=10,
            max=60,
            value=self.record_duration,
            step=1,
            size_hint_y=None,
            height=dp(30)
        )
        self.duration_slider.bind(value=self.on_duration_change)
        duration_layout.add_widget(self.duration_slider)
        
        self.duration_value_label = Label(
            text=f"{self.record_duration:.0f} seg",
            size_hint_y=None,
            height=dp(25)
        )
        duration_layout.add_widget(self.duration_value_label)
        content.add_widget(duration_layout)
        
        # Botones
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        cancel_btn = Button(
            text="Cancelar",
            size_hint_x=0.5,
            on_press=lambda x: popup.dismiss()
        )
        buttons_layout.add_widget(cancel_btn)
        
        apply_btn = Button(
            text="Aplicar",
            size_hint_x=0.5,
            on_press=lambda x: self.close_recording_config_popup(popup)
        )
        buttons_layout.add_widget(apply_btn)
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title="Configuración de Grabación",
            content=content,
            size_hint=(0.8, 0.7)
        )
        popup.open()
        
    def close_recording_config_popup(self, popup):
        """Cierra el popup de configuración de grabación y guarda automáticamente"""
        try:
            self.save_config(show_messages=True)
            popup.dismiss()
        except Exception as e:
            self.show_message("Error", f"Error guardando configuración: {str(e)}")
            
    def show_exit_confirmation(self, instance=None):
        """Muestra una ventana de confirmación para salir de la aplicación"""
        popup_content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Mensaje de confirmación
        message_label = Label(
            text="¿Estás seguro de que deseas salir de la aplicación?",
            text_size=(dp(300), None),
            halign='center',
            valign='middle',
            font_size='16sp'
        )
        popup_content.add_widget(message_label)
        
        # Información adicional si está grabando
        if self.is_recording:
            warning_label = Label(
                text="⚠️ La grabación se detendrá automáticamente",
                text_size=(dp(300), None),
                halign='center',
                valign='middle',
                font_size='14sp',
                color=(1, 0.5, 0, 1)  # Color naranja para advertencia
            )
            popup_content.add_widget(warning_label)
        
        # Botones
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        cancel_btn = Button(
            text="Cancelar",
            size_hint_x=0.5,
            on_press=lambda x: popup.dismiss()
        )
        buttons_layout.add_widget(cancel_btn)
        
        exit_btn = Button(
            text="Salir",
            size_hint_x=0.5,
            on_press=lambda x: self.exit_application(popup)
        )
        buttons_layout.add_widget(exit_btn)
        
        popup_content.add_widget(buttons_layout)
        
        popup = Popup(
            title="Confirmar Salida",
            content=popup_content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False  # No permitir cerrar haciendo clic fuera
        )
        popup.open()
        
    def exit_application(self, popup):
        """Cierra la aplicación de forma segura"""
        popup.dismiss()
        
        # Detener grabación si está activa
        if self.is_recording:
            self.stop_recording()
        
        # Guardar configuración
        self.save_config(show_messages=False)
        
        # Cerrar PyAudio si está abierto
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
            self.audio = None
        
        # Cerrar la aplicación
        import sys
        sys.exit(0)
        
    def refresh_devices_modal(self, combo_widget):
        """Refresca los dispositivos en el modal de audio"""
        try:
            device_names = self.refresh_audio_devices()
            combo_widget['values'] = device_names
            self.update_device_list()
            
            if device_names and device_names[0] != "Error obteniendo dispositivos":
                self.show_message("Dispositivos actualizados", 
                                  f"Se encontraron {len(device_names)} dispositivos de entrada",
                                  "info")
            else:
                self.show_message("Sin dispositivos", 
                                     "No se encontraron dispositivos de entrada disponibles",
                                     "warning")
        except Exception as e:
            self.show_message("Error", f"Error refrescando dispositivos: {str(e)}", "error")
            
    def apply_audio_config_modal(self, window):
        """Aplica la configuración de audio desde el modal y guarda en config.ini"""
        try:
            self.apply_audio_quality()
            # Guardar configuración actualizada
            self.save_config(show_messages=True)
            window.destroy()
        except Exception as e:
            self.show_message("Error", f"Error aplicando configuración: {str(e)}", "error")
            
    def update_threshold_label_modal(self, value):
        """Actualiza la etiqueta del umbral en el modal y programa guardado automático"""
        if hasattr(self, 'threshold_label_modal'):
            self.threshold_label_modal.config(text=f"{float(value):.1f} dB")
            
        # Cancelar timer anterior si existe
        if hasattr(self, 'threshold_save_timer'):
            Clock.unschedule(self.threshold_save_timer)
            
        # Programar guardado automático con retraso de 1 segundo
        self.threshold_save_timer = Clock.schedule_once(lambda dt: self.save_config(), 1)
            
    def update_duration_label_modal(self, value):
        """Actualiza la etiqueta de duración en el modal y programa guardado automático"""
        if hasattr(self, 'duration_label_modal'):
            self.duration_label_modal.config(text=f"{float(value):.0f} seg")
            
        # Actualizar también el contador de tiempo si no estamos grabando
        if not self.is_recording:
            duration_int = int(float(value))
            self.current_recording_time_text = f"0/{duration_int} seg"
            if hasattr(self, 'current_recording_time_label'):
                self.current_recording_time_label.text = self.current_recording_time_text
            
        # Cancelar timer anterior si existe
        if hasattr(self, 'duration_save_timer'):
            Clock.unschedule(self.duration_save_timer)
            
        # Programar guardado automático con retraso de 1 segundo
        self.duration_save_timer = Clock.schedule_once(lambda dt: self.save_config(), 1)
        
    def update_threshold_label(self, value):
        """Actualiza la etiqueta del umbral cuando cambia el slider (mantener para compatibilidad)"""
        pass  # No se usa en la nueva interfaz, pero se mantiene para evitar errores
        
    def update_duration_label(self, value):
        """Actualiza la etiqueta de duración cuando cambia el slider (mantener para compatibilidad)"""
        pass  # No se usa en la nueva interfaz, pero se mantiene para evitar errores
        
    def apply_audio_quality(self):
        """Aplica la configuración de calidad de audio con validación"""
        if self.is_recording:
            self.show_message("Advertencia", "No se puede cambiar la calidad durante la grabación", "warning")
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
            proposed_rate = int(self.sample_rate_text)
            proposed_bit_depth = int(self.bit_depth_text)
            proposed_channels = 2 if self.channels_mode_text == "Estéreo" else 1
            
            # Validar con el dispositivo seleccionado
            if selected_device_info:
                # Ajustar canales según las capacidades del dispositivo
                max_device_channels = selected_device_info.get('channels', 1)
                if proposed_channels > max_device_channels:
                    proposed_channels = max_device_channels
                    if hasattr(self, 'channels_spinner'):
                        self.channels_spinner.text = "Mono" if proposed_channels == 1 else "Estéreo"
                    self.show_message("Ajuste automático", 
                                         f"El dispositivo seleccionado solo soporta {max_device_channels} canal(es). "
                                         f"Configurando a {'Mono' if proposed_channels == 1 else 'Estéreo'}.",
                                         "warning")
            
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
                self.show_message("Configuración no soportada", 
                                     "La configuración seleccionada no es compatible. Usando configuración estándar segura.",
                                     "warning")
                
                # Configuración de emergencia
                self.RATE = 44100
                self.FORMAT = pyaudio.paInt16
                self.CHANNELS = 1
                self.CHUNK = 1024
                
                # Actualizar los controles
                if hasattr(self, 'sample_rate_spinner'):
                    self.sample_rate_spinner.text = "44100"
                if hasattr(self, 'bit_depth_spinner'):
                    self.bit_depth_spinner.text = "16"  
                if hasattr(self, 'channels_spinner'):
                    self.channels_spinner.text = "Mono"
                
            test_audio.terminate()
            
            # Actualizar la información de calidad mostrada
            bit_depth_display = "16" if self.FORMAT == pyaudio.paInt16 else "24" if self.FORMAT == pyaudio.paInt24 else "32"
            channels_text = 'Estéreo' if self.CHANNELS == 2 else 'Mono'
            self.quality_info_text = f"{self.RATE}Hz, {bit_depth_display}bit, {channels_text}"
            if hasattr(self, 'quality_info_label'):
                self.quality_info_label.text = self.quality_info_text
            
            # Actualizar información del micrófono
            selected_name = self.selected_device_name if hasattr(self, 'selected_device_name') else ""
            if selected_name and selected_name != "Dispositivo por defecto del sistema":
                # Extraer solo el nombre del dispositivo (sin el ID)
                mic_name = selected_name.split(' (ID:')[0]
                if len(mic_name) > 25:
                    mic_name = mic_name[:25] + "..."
                self.mic_info_text = mic_name
            else:
                self.mic_info_text = "Dispositivo por defecto"
            
            if hasattr(self, 'mic_info_label'):
                self.mic_info_label.text = self.mic_info_text
                
            self.show_message("Éxito", 
                f"Configuración aplicada correctamente:\n"
                f"• Frecuencia: {self.RATE} Hz\n"
                f"• Bits: {bit_depth_display} bits\n"
                f"• Canales: {self.CHANNELS} ({channels_text})\n"
                f"• Buffer: {self.CHUNK} frames\n"
                f"• Micrófono: {self.mic_info_text}",
                "info")
                
        except Exception as e:
            self.show_message("Error", f"Error al aplicar configuración: {str(e)}\nUsando configuración por defecto.", "error")
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
                self.show_message("Dispositivos actualizados", 
                                  f"Se encontraron {len(device_names)} dispositivos de entrada",
                                  "info")
            else:
                self.show_message("Sin dispositivos", 
                                     "No se encontraron dispositivos de entrada disponibles",
                                     "warning")
                                     
        except Exception as e:
            self.show_message("Error", f"Error refrescando dispositivos: {str(e)}", "error")
            
    def get_selected_device_index(self):
        """Obtiene el índice del dispositivo seleccionado"""
        selected_name = self.selected_device_name if hasattr(self, 'selected_device_name') else ""
        
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
            self.update_current_status("Grabando...")
            
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
            record_seconds = self.record_duration
            
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
                    Clock.schedule_once(lambda dt: setattr(self, 'current_recording_time_text', f"{elapsed_seconds}/{total_seconds} seg") or 
                                     (hasattr(self, 'current_recording_time_label') and setattr(self.current_recording_time_label, 'text', self.current_recording_time_text)))
                    
                    # Calcular volumen actual
                    current_db = self.calculate_db(data)
                    max_volume_db = max(max_volume_db, current_db)
                    self.current_max_volume = max_volume_db
                    
                    # Actualizar UI en el hilo principal
                    Clock.schedule_once(lambda dt: self.update_volume_display(current_db))
                    Clock.schedule_once(lambda dt: self.update_current_status_by_volume())
                    
                except Exception as e:
                    print(f"Error leyendo datos de audio: {e}")
                    # Continuar con el siguiente chunk
                    continue
                
            stream.stop_stream()
            stream.close()
            
            return frames, max_volume_db
            
        except Exception as e:
            print(f"Error en record_audio_chunk: {e}")
            # Programar el mensaje de error para el hilo principal
            Clock.schedule_once(lambda dt: self.show_message("Error de Grabación", 
                               f"Error durante la grabación: {str(e)}\n\n"
                               "Sugerencias:\n"
                               "• Verificar que el micrófono esté conectado\n"
                               "• Probar con configuración más simple (16-bit, Mono, 44.1kHz)\n"
                               "• Seleccionar otro dispositivo de audio",
                               "error"))
            return None, -60
            
    def update_volume_display(self, db_level):
        """Actualiza la visualización del volumen"""
        self.current_volume_text = f"{db_level:.1f} dB"
        if hasattr(self, 'current_volume_label'):
            self.current_volume_label.text = self.current_volume_text
        
        # Actualizar barra de progreso (convertir dB a porcentaje)
        # -60 dB = 0%, 0 dB = 100%
        percentage = max(0, min(100, (db_level + 60) * 100 / 60))
        if hasattr(self, 'volume_bar'):
            self.volume_bar.value = percentage
        
    def update_current_status(self, status_text):
        """Actualiza el texto de estado del tramo actual"""
        self.will_save_current_text = status_text
        if hasattr(self, 'current_status_label'):
            self.current_status_label.text = status_text
        
    def update_current_status_by_volume(self):
        """Actualiza el estado del tramo actual basado en el volumen máximo detectado"""
        if self.current_max_volume >= self.threshold_db:
            status_text = f"SE GUARDARÁ (Max: {self.current_max_volume:.1f} dB)"
            color = (0, 1, 0, 1)  # Verde
        else:
            status_text = f"Se eliminará (Max: {self.current_max_volume:.1f} dB)"
            color = (1, 0, 0, 1)  # Rojo
            
        self.will_save_current_text = status_text
        if hasattr(self, 'current_status_label'):
            self.current_status_label.text = status_text
            self.current_status_label.color = color
        
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
                self.recordings_saved_count += 1
                print(f"Grabación guardada exitosamente: {filepath}")
                print(f"Tamaño del archivo: {os.path.getsize(filepath)} bytes")
            else:
                print(f"Error: El archivo no se creó correctamente o está vacío")
                
        except Exception as e:
            error_msg = f"Error al guardar la grabación: {str(e)}"
            print(error_msg)
            self.show_message("Error de Guardado", error_msg, "error")
            
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
                self.show_message("Error Crítico", 
                                   f"No se pudo guardar el archivo de audio.\n"
                                   f"Error original: {str(e)}\n"
                                   f"Error de respaldo: {str(e2)}", 
                                   "error")
            
    def recording_loop(self):
        """Bucle principal de grabación"""
        while self.is_recording:
            timestamp = datetime.now()  # Pasar objeto datetime completo
            
            # Grabar con duración configurable
            duration = self.record_duration
            self.status_text = f"Grabando ({duration:.0f}s)..."
            if hasattr(self, 'status_label'):
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', self.status_text))
            frames, max_volume = self.record_audio_chunk()
            
            if frames is None:
                break
                
            # Verificar si el volumen superó el umbral
            threshold = self.threshold_db
            
            if max_volume >= threshold:
                # Guardar la grabación
                self.save_recording(frames, timestamp)
                self.status_text = f"Grabación guardada (Vol: {max_volume:.1f} dB)"
                Clock.schedule_once(lambda dt: self.update_current_status(f"GUARDADA ({max_volume:.1f} dB)"))
                if hasattr(self, 'current_status_label'):
                    Clock.schedule_once(lambda dt: setattr(self.current_status_label, 'color', (0, 1, 0, 1)))
            else:
                # Descartar la grabación
                self.recordings_deleted_count += 1
                self.status_text = f"Grabación descartada (Vol: {max_volume:.1f} dB)"
                Clock.schedule_once(lambda dt: self.update_current_status(f"ELIMINADA ({max_volume:.1f} dB)"))
                if hasattr(self, 'current_status_label'):
                    Clock.schedule_once(lambda dt: setattr(self.current_status_label, 'color', (1, 0, 0, 1)))
                
            # Pequeña pausa antes del siguiente ciclo
            if self.is_recording:
                # Resetear el contador de tiempo para mostrar que esperamos el próximo ciclo
                duration_int = int(duration)
                Clock.schedule_once(lambda dt: (
                    setattr(self, 'current_recording_time_text', f"0/{duration_int} seg") or
                    (hasattr(self, 'current_recording_time_label') and setattr(self.current_recording_time_label, 'text', self.current_recording_time_text))
                ))
                
                time.sleep(2)  # Pausa un poco más larga para mostrar el resultado
                Clock.schedule_once(lambda dt: self.update_current_status("Esperando..."))
                if hasattr(self, 'current_status_label'):
                    Clock.schedule_once(lambda dt: setattr(self.current_status_label, 'color', (0, 0, 0, 1)))
                time.sleep(1)
                
    def start_recording(self, instance=None):
        """Inicia la grabación en bucle"""
        try:
            self.audio = pyaudio.PyAudio()
            self.is_recording = True
            
            # Deshabilitar botón de inicio y habilitar el de parar
            self.start_button.disabled = True
            self.stop_button.disabled = False
            
            # Iniciar el hilo de grabación
            self.recording_thread = threading.Thread(target=self.recording_loop, daemon=True)
            self.recording_thread.start()
            
        except Exception as e:
            self.show_message("Error", f"No se pudo iniciar la grabación: {str(e)}", "error")
            self.stop_recording()
            
    def stop_recording(self, instance=None):
        """Detiene la grabación"""
        self.is_recording = False
        self.status_text = "Detenido"
        if hasattr(self, 'status_label'):
            self.status_label.text = self.status_text
        
        # Resetear el estado del tramo actual
        self.will_save_current_text = "Esperando..."
        if hasattr(self, 'current_status_label'):
            self.current_status_label.text = self.will_save_current_text
            self.current_status_label.color = (0, 0, 0, 1)  # Negro
        
        # Resetear el contador de tiempo
        self.current_recording_time_text = f"0/{self.record_duration} seg"
        if hasattr(self, 'current_recording_time_label'):
            self.current_recording_time_label.text = self.current_recording_time_text
        
        # Habilitar botón de inicio y deshabilitar el de parar
        self.start_button.disabled = False
        self.stop_button.disabled = True
        
        # Cerrar PyAudio
        if self.audio:
            self.audio.terminate()
            self.audio = None
            
    def on_closing(self):
        """Maneja el cierre de la aplicación y guarda la configuración"""
        if self.is_recording:
            self.stop_recording()
        # Guardar configuración antes de cerrar
        self.save_config(show_messages=False)
        
        # Cerrar PyAudio si está abierto
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
            self.audio = None  # Sin mensajes al cerrar

if __name__ == "__main__":
    # Verificar dependencias
    try:
        import pyaudio
        import numpy
    except ImportError as e:
        print(f"Error: Falta instalar dependencias: {e}")
        print("Ejecuta: pip install pyaudio numpy")
        exit(1)
        
    app = AudioRecorderApp()
    app.run()