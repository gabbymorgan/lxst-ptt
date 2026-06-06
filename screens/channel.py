from enum import StrEnum, auto

import RNS

class ChannelState(StrEnum):
    READY = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    DISCONNECTING = auto()

class ChannelScreen:    
    def __init__(self, app):
        self.app = app
        self.phone_state = ChannelState.READY
        self.channel_hash = None
        self.channel_name = None
        
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
            print(bytes.fromhex(relay_hash))
            relay_identity = RNS.Identity.recall(bytes.fromhex(relay_hash))
            if relay_identity is None:
                print("Could not discover channel identity")
                self.app.router.navigate("channels_list")
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
        self.app.router.navigate("channels_list")  
    
    def _on_double_release(self):
        pass
    
    def _on_app_change(self, name, value):
        pass

    def display(self):
        try:
            name, hash = self.app.state.current_channel
            title = name
            body_lines = [self.phone_state, "PTT: On"]
            footer = "short: mode | long: talk"
            self.app.ui.render(title, body_lines, accent=(60, 150, 255), footer=footer)
        except Exception as e:
            print(e)
            