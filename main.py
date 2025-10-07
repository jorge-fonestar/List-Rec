#!/usr/bin/env python3
"""
Grabador de Audio para Android
Versión móvil de la aplicación de grabación con detección de volumen
"""

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
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.logger import Logger

# Importaciones para Android
from android.permissions import request_permissions, Permission
from plyer import audio

import numpy as np
import threading
import os
from datetime import datetime
import time
import configparser
import sys

class AudioRecorderApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Grabador de Audio"
        
    def build(self):
        # Solicitar permisos en Android
        self.request_android_permissions()
        
        # Configurar ventana para móvil
        Window.title = "Grabador de Audio"
        # En Android, el tamaño se ajusta automáticamente
        
        # Crear instancia del grabador
        self.recorder = AudioRecorderMobile()
        return self.recorder.setup_ui()
    
    def request_android_permissions(self):
        """Solicita los permisos necesarios en Android"""
        try:
            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ])
            Logger.info("App: Permisos solicitados")
        except Exception as e:
            Logger.warning(f"App: Error solicitando permisos: {e}")
    
    def on_stop(self):
        """Método llamado cuando la aplicación se cierra"""
        if hasattr(self, 'recorder'):
            self.recorder.on_closing()
        return super().on_stop()

class AudioRecorderMobile:
    def __init__(self):
        # Configuración básica para móvil
        self.config_file = "config.ini"
        self.load_config()
        
        # Variables de estado
        self.is_recording = False
        self.threshold_db = -40.0
        self.record_duration = 30
        self.current_volume_text = "0.0 dB"
        self.status_text = "Detenido"
        self.recordings_saved_count = 0
        self.recordings_deleted_count = 0
        self.will_save_current_text = "Esperando..."
        self.current_max_volume = -60.0
        
        # Directorio para grabaciones
        self.output_dir = self.get_storage_path()
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except Exception as e:
                Logger.warning(f"No se pudo crear directorio: {e}")
                self.output_dir = "/sdcard"  # Fallback
        
        # Referencias a widgets
        self.volume_bar = None
        self.current_volume_label = None
        self.status_label = None
        self.current_status_label = None
        self.recordings_saved_label = None
        self.recordings_deleted_label = None
        self.start_button = None
        self.stop_button = None
        
    def get_storage_path(self):
        """Obtiene la ruta de almacenamiento apropiada para Android"""
        try:
            from android.storage import primary_external_storage_path
            storage_path = primary_external_storage_path()
            return os.path.join(storage_path, "AudioRecorder")
        except Exception as e:
            Logger.warning(f"Error obteniendo ruta de almacenamiento: {e}")
            return "/sdcard/AudioRecorder"
    
    def load_config(self):
        """Carga configuración básica"""
        # Configuración por defecto para móvil
        self.config_record_seconds = 30
        self.config_threshold_db = -40.0
        self.config_min_threshold_db = -60.0
        self.config_max_threshold_db = 0.0
        self.config_output_dir = "grabaciones"
        
    def setup_ui(self):
        """Configura la interfaz optimizada para móvil"""
        # Layout principal con más espaciado para pantallas táctiles
        main_layout = BoxLayout(
            orientation='vertical', 
            padding=dp(15), 
            spacing=dp(20)
        )
        
        # Título
        title_label = Label(
            text="Grabador de Audio",
            size_hint_y=None,
            height=dp(50),
            font_size='20sp',
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
        
        # Control de umbral
        threshold_layout = self.create_threshold_control()
        main_layout.add_widget(threshold_layout)
        
        # Estadísticas
        stats_layout = self.create_statistics_frame()
        main_layout.add_widget(stats_layout)
        
        # Botones grandes para móvil
        buttons_layout = self.create_buttons_frame()
        main_layout.add_widget(buttons_layout)
        
        return main_layout
    
    def create_volume_monitor(self):
        """Monitor de volumen"""
        container = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            height=dp(100), 
            spacing=dp(10)
        )
        
        title = Label(
            text="Monitor de Volumen",
            size_hint_y=None,
            height=dp(30),
            font_size='16sp',
            bold=True
        )
        container.add_widget(title)
        
        self.volume_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(25)
        )
        container.add_widget(self.volume_bar)
        
        self.current_volume_label = Label(
            text=self.current_volume_text,
            size_hint_y=None,
            height=dp(30),
            font_size='14sp'
        )
        container.add_widget(self.current_volume_label)
        
        return container
    
    def create_status_frame(self):
        """Estado actual"""
        container = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            height=dp(120), 
            spacing=dp(5)
        )
        
        title = Label(
            text="Estado",
            size_hint_y=None,
            height=dp(30),
            font_size='16sp',
            bold=True
        )
        container.add_widget(title)
        
        self.status_label = Label(
            text=self.status_text,
            size_hint_y=None,
            height=dp(40),
            font_size='18sp',
            bold=True,
            color=(0, 0.7, 0, 1)
        )
        container.add_widget(self.status_label)
        
        self.current_status_label = Label(
            text=self.will_save_current_text,
            size_hint_y=None,
            height=dp(30),
            font_size='14sp'
        )
        container.add_widget(self.current_status_label)
        
        return container
    
    def create_threshold_control(self):
        """Control de umbral de volumen"""
        container = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            height=dp(120), 
            spacing=dp(10)
        )
        
        title = Label(
            text=f"Umbral: {self.threshold_db:.1f} dB",
            size_hint_y=None,
            height=dp(30),
            font_size='16sp',
            bold=True
        )
        container.add_widget(title)
        self.threshold_label = title
        
        threshold_slider = Slider(
            min=-60,
            max=0,
            value=self.threshold_db,
            step=1,
            size_hint_y=None,
            height=dp(40)
        )
        threshold_slider.bind(value=self.on_threshold_change)
        container.add_widget(threshold_slider)
        
        return container
    
    def create_statistics_frame(self):
        """Estadísticas"""
        container = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            height=dp(100), 
            spacing=dp(10)
        )
        
        title = Label(
            text="Estadísticas",
            size_hint_y=None,
            height=dp(30),
            font_size='16sp',
            bold=True
        )
        container.add_widget(title)
        
        stats_grid = GridLayout(cols=2, size_hint_y=None, height=dp(60))
        
        stats_grid.add_widget(Label(text="Guardadas:", font_size='14sp'))
        self.recordings_saved_label = Label(
            text=str(self.recordings_saved_count), 
            font_size='14sp', 
            bold=True
        )
        stats_grid.add_widget(self.recordings_saved_label)
        
        stats_grid.add_widget(Label(text="Eliminadas:", font_size='14sp'))
        self.recordings_deleted_label = Label(
            text=str(self.recordings_deleted_count), 
            font_size='14sp', 
            bold=True
        )
        stats_grid.add_widget(self.recordings_deleted_label)
        
        container.add_widget(stats_grid)
        return container
    
    def create_buttons_frame(self):
        """Botones grandes para móvil"""
        button_layout = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            height=dp(140), 
            spacing=dp(20)
        )
        
        self.start_button = Button(
            text="▶ INICIAR GRABACIÓN",
            size_hint_y=None,
            height=dp(60),
            font_size='18sp',
            background_color=(0, 0.7, 0, 1),
            on_press=self.start_recording
        )
        button_layout.add_widget(self.start_button)
        
        self.stop_button = Button(
            text="⏹ DETENER GRABACIÓN",
            size_hint_y=None,
            height=dp(60),
            font_size='18sp',
            background_color=(0.7, 0, 0, 1),
            disabled=True,
            on_press=self.stop_recording
        )
        button_layout.add_widget(self.stop_button)
        
        return button_layout
    
    def on_threshold_change(self, instance, value):
        """Actualiza el umbral"""
        self.threshold_db = value
        if hasattr(self, 'threshold_label'):
            self.threshold_label.text = f"Umbral: {value:.1f} dB"
    
    def start_recording(self, instance=None):
        """Inicia la grabación usando Plyer"""
        try:
            if not self.is_recording:
                self.is_recording = True
                self.status_text = "Grabando..."
                self.status_label.text = self.status_text
                self.status_label.color = (1, 0, 0, 1)  # Rojo para grabando
                
                self.start_button.disabled = True
                self.stop_button.disabled = False
                
                # Iniciar grabación en hilo separado
                self.recording_thread = threading.Thread(target=self.recording_loop_mobile)
                self.recording_thread.daemon = True
                self.recording_thread.start()
                
                Logger.info("Grabación iniciada")
                
        except Exception as e:
            Logger.error(f"Error iniciando grabación: {e}")
            self.show_message("Error", f"No se pudo iniciar la grabación: {str(e)}")
    
    def stop_recording(self, instance=None):
        """Detiene la grabación"""
        self.is_recording = False
        self.status_text = "Detenido"
        self.status_label.text = self.status_text
        self.status_label.color = (0, 0.7, 0, 1)  # Verde para detenido
        
        self.start_button.disabled = False
        self.stop_button.disabled = True
        
        self.will_save_current_text = "Esperando..."
        self.current_status_label.text = self.will_save_current_text
        
        Logger.info("Grabación detenida")
    
    def recording_loop_mobile(self):
        """Bucle de grabación simplificado para móvil"""
        while self.is_recording:
            try:
                # Simular grabación (en una implementación real usarías plyer.audio)
                filename = f"grabacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                filepath = os.path.join(self.output_dir, filename)
                
                # Simular un volumen aleatorio para demostración
                import random
                simulated_volume = random.uniform(-60, -20)
                
                Clock.schedule_once(lambda dt: self.update_volume_display(simulated_volume))
                
                if simulated_volume >= self.threshold_db:
                    # Simular guardado
                    Clock.schedule_once(lambda dt: self.increment_saved_count())
                    Clock.schedule_once(lambda dt: self.update_current_status(
                        f"GUARDADO: {simulated_volume:.1f} dB"
                    ))
                else:
                    Clock.schedule_once(lambda dt: self.increment_deleted_count())
                    Clock.schedule_once(lambda dt: self.update_current_status(
                        f"Eliminado: {simulated_volume:.1f} dB"
                    ))
                
                # Esperar duración configurada
                time.sleep(self.record_duration)
                
            except Exception as e:
                Logger.error(f"Error en grabación: {e}")
                break
    
    def update_volume_display(self, db_level):
        """Actualiza la visualización del volumen"""
        self.current_volume_text = f"{db_level:.1f} dB"
        if self.current_volume_label:
            self.current_volume_label.text = self.current_volume_text
        
        # Actualizar barra de progreso
        percentage = max(0, min(100, (db_level + 60) * 100 / 60))
        if self.volume_bar:
            self.volume_bar.value = percentage
    
    def update_current_status(self, status_text):
        """Actualiza el estado del tramo actual"""
        self.will_save_current_text = status_text
        if self.current_status_label:
            self.current_status_label.text = status_text
    
    def increment_saved_count(self):
        """Incrementa el contador de grabaciones guardadas"""
        self.recordings_saved_count += 1
        if self.recordings_saved_label:
            self.recordings_saved_label.text = str(self.recordings_saved_count)
    
    def increment_deleted_count(self):
        """Incrementa el contador de grabaciones eliminadas"""
        self.recordings_deleted_count += 1
        if self.recordings_deleted_label:
            self.recordings_deleted_label.text = str(self.recordings_deleted_count)
    
    def show_message(self, title, message):
        """Muestra un mensaje"""
        popup_content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        
        message_label = Label(
            text=message,
            text_size=(dp(300), None),
            halign='center',
            valign='middle'
        )
        popup_content.add_widget(message_label)
        
        close_btn = Button(
            text="Cerrar",
            size_hint_y=None,
            height=dp(50),
            on_press=lambda x: popup.dismiss()
        )
        popup_content.add_widget(close_btn)
        
        popup = Popup(
            title=title,
            content=popup_content,
            size_hint=(0.9, 0.5)
        )
        popup.open()
    
    def on_closing(self):
        """Limpieza al cerrar"""
        self.is_recording = False
        Logger.info("Aplicación cerrada correctamente")

if __name__ == "__main__":
    app = AudioRecorderApp()
    app.run()