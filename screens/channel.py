from enum import StrEnum, auto

import RNS

class ChannelState(StrEnum):
    READY = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    ENDED = auto()

class ChannelScreen:    
    def __init__(self, app):
        self.app = app
        self._phone_state = ChannelState.READY
        self.channel_hash = None
        self.channel_name = None
        self._ptt_enabled = False
        
    @property
    def phone_state(self):
        return self._phone_state
        
    @phone_state.setter
    def phone_state(self, value):
        self._phone_state = value
        self.display()
        
    def mount(self):
        try:
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
            
            self.app.telephone.call(relay_identity)
            self.channel_hash = relay_hash
            self.channel_name = relay_name
            
            self.display()
        except Exception as e:
            print(e)
        
    def _on_press(self):
        pass
    
    def _on_release(self):
        pass
            
    def _on_long_press(self):
        pass
    
    def _on_long_release(self):
        pass
    
    def _on_double_press(self):
        self.app.telephone.hangup()
        self.app.router.navigate("channels_list")  
    
    def _on_double_release(self):
        pass
    
    def _on_app_change(self, name, value):
        pass
    
    def _on_call_ringing(self, identity):
        self.phone_state = ChannelState.CONNECTING
        
    def _on_call_established(self, identity):
        self.phone_state = ChannelState.CONNECTED
        
    def _on_call_ended(self, identity):
        self.phone_state = ChannelState.ENDED


    def display(self):
        try:
            name, hash = self.app.state.current_channel
            title = name
            body_lines = [self.phone_state, "PTT: Off"]
            footer = "short: mode | long: talk"
            self.app.ui.render(title, body_lines, accent=(60, 150, 255), footer=footer)
        except Exception as e:
            print(e)
            