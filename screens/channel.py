import time
import RNS

from enum import StrEnum, auto
from LXST.Primitives.Telephony import Profiles

class ChannelStateEnum(StrEnum):
    READY = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    ENDED = auto()

class ChannelScreen:        
    def __init__(self, app):
        self.app = app
        self._phone_state = ChannelStateEnum.READY
        self._muted = False
        self._ptt_enabled = True
        self.channel_hash = None
        self.channel_name = None        
        
    @property
    def phone_state(self):
        return self._phone_state
        
    @property
    def ptt_enabled(self):
        return self._ptt_enabled
    
    @property
    def muted(self):
        return self._muted
    
    @phone_state.setter
    def phone_state(self, value):
        self._phone_state = value
        self.display()
    
    @ptt_enabled.setter
    def ptt_enabled(self, value):
        self._ptt_enabled = value
        self.display()
        
    @muted.setter
    def muted(self, value):
        self._muted = value
        self.display()
    
        
    def mount(self):
        try:
            if self.ptt_enabled:
                self._mute()
            self.app.ui.on_press(self._on_press)
            self.app.ui.on_release(self._on_release)
            self.app.ui.on_long_press(self._on_long_press)
            self.app.ui.on_long_release(self._on_long_release)
            self.app.ui.on_double_press(self._on_double_press)
            self.app.ui.on_double_release(self._on_double_release)
            self.app.state.set_on_change_callback(self._on_app_change)
            
            relay_name, relay_hash = self.app.state.current_channel
            relay_identity = RNS.Identity.recall(bytes.fromhex(relay_hash))
            if relay_identity is None:
                print("Could not discover channel identity")
                self.app.router.navigate("channels_list")
            self.app.telephone.set_ringing_callback(self._on_call_ringing)
            self.app.telephone.set_established_callback(self._on_call_established)
            self.app.telephone.set_ended_callback(self._on_call_ended)
            self.app.telephone.call(relay_identity, profile=Profiles.BANDWIDTH_VERY_LOW)
            self.channel_hash = relay_hash
            self.channel_name = relay_name
            
            self.display()
        except Exception as e:
            print(e)
        
    def _on_press(self):
        if self.ptt_enabled and self.phone_state == ChannelStateEnum.CONNECTED:
            self._unmute()
                
    def _on_release(self):
        if self.ptt_enabled and self.phone_state == ChannelStateEnum.CONNECTED:
            self._mute()
                
    def _on_long_press(self):
        pass
    
    def _on_long_release(self):
        self._on_release()
    
    def _on_double_press(self):
        self.app.telephone.hangup()
        self.app.router.navigate("channels_list")  
    
    def _on_double_release(self):
        pass
    
    def _on_app_change(self, name, value):
        pass
    
    def _on_call_ringing(self, identity):
        self.phone_state = ChannelStateEnum.CONNECTING
        
    def _on_call_established(self, identity):
        self.phone_state = ChannelStateEnum.CONNECTED
        
    def _on_call_ended(self, identity):
        self.phone_state = ChannelStateEnum.ENDED
        
    def _mute(self):
        self.muted = True
        self.app.ui.set_mic_muted(True)

    def _unmute(self):
        self.muted = False
        self.app.ui.set_mic_muted(False)

    def display(self):
        try:
            name, hash = self.app.state.current_channel
            title = name
            body_lines = [self.phone_state, "PTT: " if self.ptt_enabled else "Always-On", "Muted" if self.muted else "Unmuted"]
            footer = "short: mode | dbl: end"
            self.app.ui.render(title, body_lines, accent=(60, 150, 255), footer=footer)
        except Exception as e:
            print(e)
            