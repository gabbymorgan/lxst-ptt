import subprocess
import time
import threading
import os

import RNS
from PIL import Image, ImageDraw, ImageFont
from lib.whisplay_client import create_whisplay_hardware


class WhisplayInterface:
    LONG_PRESS_THRESHOLD = 1
    DOUBLE_PRESS_THRESHOLD = 0.3
    
    def __init__(self):
        self.board = None
        self.canvas = None
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
        
        self._title_font = self._load_font(24, bold=True)
        self._body_font = self._load_font(18, bold=False)
        self._body_compact_font = self._load_font(16, bold=False)
        self._small_font = self._load_font(14, bold=False)
        self._small_compact_font = self._load_font(12, bold=False)

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
            
    def set_mic_muted(self, muted):
        if self._wm8960_device is None:
            return
        card = self._wm8960_device.split(",")[0].split(":")[-1]
        state = "off" if muted else "on"
        try:
            subprocess.run(
                ["amixer", "-c", card, "cset", "name='Capture Switch'", state],
                check=False, capture_output=True, timeout=2,
            )
        except Exception as e:
            print(e)

    def render(self, title, body_lines, accent=(60, 150, 255), footer=""):
        BODY_FONT_SIZE = 20
        width, height = self.board.LCD_WIDTH, self.board.LCD_HEIGHT
        image = Image.new("RGB", (width, height), (11, 16, 24))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((12, 16, width - 12, height - 16), radius=18,
                               fill=(20, 28, 40), outline=(40, 55, 72), width=2)
        draw.rounded_rectangle((20, 22, width - 20, 54), radius=12, fill=accent)
        draw.text((28, 30), title, fill=(255, 255, 255), font=self._title_font)
        y_position = 70
        max_width = width - 56
        for line in body_lines:
            if y_position >= height - 50:
                break
            if not line:
                y_position += 8
                continue
            is_selected = False
            current_text = line
            if isinstance(line, tuple):
                current_text, is_selected = line
            wrapped_text = self._wrap_text(draw, current_text, self._body_font, max_width)
            for wrapped_line in wrapped_text:
                if is_selected:
                    bb = draw.textbbox((0, 0), wrapped_line, font=self._body_font)
                    lw = bb[2] - bb[0]
                    draw.rounded_rectangle((22, y_position - 2, 22 + lw + 12, y_position + 20),
                                           radius=6, fill=(accent[0] // 3, accent[1] // 3, accent[2] // 3))
                    draw.text((BODY_FONT_SIZE, y_position), wrapped_line, fill=(255, 255, 255), font=self._body_font)
                else:
                    draw.text((BODY_FONT_SIZE, y_position), wrapped_line, fill=(180, 195, 210), font=self._body_font)
                y_position += 22
        if footer:
            draw.rounded_rectangle((20, height - 38, width - 20, height - 22), radius=10, fill=(28, 37, 50))
            draw.text((28, height - 34), footer, fill=(140, 195, 255), font=self._small_font)
        
        frame = self._rgb565_bytes(image)
        self.board.draw_image(0, 0, self.board.LCD_WIDTH, self.board.LCD_HEIGHT, frame)
        
        
    def _rgb565_bytes(self, image: Image.Image) -> bytes:
        rgb = image.convert("RGB")
        output = bytearray()
        for y in range(rgb.height):
            for x in range(rgb.width):
                r, g, b = rgb.getpixel((x, y))
                value = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                output.append((value >> 8) & 0xFF)
                output.append(value & 0xFF)
        return bytes(output)
    
    def _wrap_text(self, draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
        if not text:
            return [""]
        words = text.split()
        if not words:
            return [text]

        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines


    def _load_font(self, size: int, bold: bool):
        candidates = []
        if bold:
            candidates.extend(
                [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                ]
            )
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ]
        )
        for path in candidates:
            if not os.path.exists(path):
                continue
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()
