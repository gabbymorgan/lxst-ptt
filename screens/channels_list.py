class ChannelsListScreen:
    def __init__(self, app):
        self.app = app
        self.channels = app.state.channels
        app.whisplay_interface.on_press(self._on_press)
        app.whisplay_interface.on_release(self._on_release)
        app.whisplay_interface.on_long_press(self._on_long_press)
        app.whisplay_interface.on_long_release(self._on_long_release)
        app.whisplay_interface.on_double_press(self._on_double_press)
        app.whisplay_interface.on_double_release(self._on_double_release)

    def _on_press(self):
        pass
    
    def _on_release(self):
        pass
    
    def _on_long_press(self):
        pass
    
    def _on_long_release(self):
        pass
    
    def _on_double_press(self):
        pass  
    
    def _on_double_release(self):
        pass    

    def display(self):
        print("Channels List:")
        for channel in self.channels:
            print(f"- {channel}")