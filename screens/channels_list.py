class ChannelsListScreen:
    def __init__(self, app):
        self.app = app
        self._channels = app.state.get_state().get("channels")
        self._selected_channel_index = 0
        app.ui.on_press(self._on_press)
        app.ui.on_release(self._on_release)
        app.ui.on_long_press(self._on_long_press)
        app.ui.on_long_release(self._on_long_release)
        app.ui.on_double_press(self._on_double_press)
        app.ui.on_double_release(self._on_double_release)

        app.state.set_on_change_callback(self._on_app_change)

    def _on_press(self):
        pass
    
    def _on_release(self):
        self.next_channel()
        
    def _on_long_press(self):
        pass
    
    def _on_long_release(self):
        pass
    
    def _on_double_press(self):
        pass  
    
    def _on_double_release(self):
        pass
    
    def _on_app_change(self, name, value):
        if name == "_channels":
            self._channels = value
            self.display()

    def display(self):
        title = "Channels"
        body_lines = []
        footer = "short: scroll | long: call"
        if self._channels and len(self._channels) > 0:
            selected_channel = self._channels[self._selected_channel_index]
            body_lines = [(f"{channel[0]}_{channel[1][-6:]}", selected_channel == channel) for channel in self._channels]
        self.app.ui.render(title, body_lines, accent=(60, 150, 255), footer=footer)
        
    def next_channel(self):
        self._selected_channel_index = (self._selected_channel_index + 1) % len(self._channels)
        self.display()