import subprocess
import time
import threading
import os

import RNS
from lib.whisplay_client import create_whisplay_hardware


class WhisplayInterface:
    LONG_PRESS_THRESHOLD = 0.5
    DOUBLE_PRESS_THRESHOLD = 0.3
    
    def __init__(self):
        self.board = None
        self._lock = threading.Lock()
        self._is_pressing = False
        self._is_double_pressing = False
        self._is_long_pressing = False
        self._long_press_timer_thread = None
        self._button_press_start = None
        self._button_press_end = None
        self._on_press_callback = None
        self._on_release_callback = None 
        self._on_long_press_callback = None
        self._on_long_release_callback = None 
        self._on_double_press_callback = None
        self._on_double_release_callback = None
        self._wm8960_device = None

        self.create_board()
        self.initialize_wm8960_device(speaker=200, mic=80)

    def create_board(self):
        self.board = create_whisplay_hardware(
            app_id=os.getenv("WHISPLAY_APP_ID", "whisplay-lxst-client"),
            display_name="LXST Client",
            icon="L",
            exit_gesture="quad_press",
            use_daemon_default_log=False,
        )
        self.board.on_button_press(self._on_button_press)
        self.board.on_button_release(self._on_button_release)
        self.board.set_backlight(70)

    def on_press(self, callback):
        self._on_press_callback = callback
    
    def on_release(self, callback):
        self._on_release_callback = callback

    def on_long_press(self, callback):
        self._on_long_press_callback = callback

    def on_long_release(self, callback):
        self._on_long_release_callback = callback  
        
    def on_double_press(self, callback):
        self._on_double_press_callback = callback
    
    def on_double_release(self, callback):
        self._on_double_release_callback = callback 

    def _on_button_press(self):
        with self._lock:
            self._is_pressing = True
            self._button_press_start = time.time()
            if self._button_press_end is not None:
                time_since_last_press = self._button_press_start - self._button_press_end
                if time_since_last_press <= self.DOUBLE_PRESS_THRESHOLD:
                    self._is_double_pressing = True
                    if self._on_double_press_callback:
                        self._on_double_press_callback()
            if not self._is_double_pressing:
                if self._on_press_callback:
                    self._on_press_callback()
                self._long_press_timer_thread = threading.Timer(self.LONG_PRESS_THRESHOLD, self._long_press_timer)
                self._long_press_timer_thread.start()

    def _on_button_release(self):
        with self._lock:
            self._long_press_timer_thread.cancel()
            self._is_pressing = False
            self._button_press_end = time.time()
            if self._is_double_pressing:
                if self._on_double_release_callback:
                    self._on_double_release_callback()
                    self._is_double_pressing = False
            elif self._is_long_pressing:
                if self._on_long_release_callback:
                    self._on_long_release_callback()
                self._is_long_pressing = False
            else:
                if self._on_release_callback:
                    self._on_release_callback()

    def _long_press_timer(self):
        with self._lock:
            if self._is_pressing:
                self._is_long_pressing = True
                if self._on_long_press_callback:
                    self._on_long_press_callback()


    def initialize_wm8960_device(self, speaker: int = 0, mic: int = 0):
        CARD_NAME = 'wm8960soundcard'
        DEVICE_ARG = f'hw:{CARD_NAME}'
        self._wm8960_device = f"plughw:{CARD_NAME},0"
        RNS.log(f"Whisplay audio: WM8960 card {CARD_NAME} ready", RNS.LOG_DEBUG)
        try:
            subprocess.run(['amixer', '-D', DEVICE_ARG, 'sset', 'Speaker',
                            str(speaker)], check=False, capture_output=True)
            subprocess.run(['amixer', '-D', DEVICE_ARG, 'sset',
                            'Capture', str(mic)], check=False, capture_output=True)
        except Exception as e:
            RNS.log(f"ERROR: Failed to set volume: {e}", RNS.LOG_ERROR)
