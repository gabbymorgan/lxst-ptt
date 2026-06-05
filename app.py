import argparse
import json
import os
import threading
import time
import LXMF
import RNS

from PIL import Image, ImageDraw, ImageFont
from whisplay_interface import WhisplayInterface
from screens.channels_list import ChannelsListScreen
from screens.channel import ChannelScreen
from LXST.Primitives.Telephony import Telephone



class App:
    def __init__(self, configdir=None, rnsconfigdir=None, whitelist_path=None,
                 verbosity=0, announce_interval=0, display_name="LXST PTT User"):
        self.should_run = False
        self.whisplay_interface = WhisplayInterface()
        self.state = AppState()
        self.router = Router(self)
        self.reticulum_instance = None
        self.reticulum_identity = None
        self.lxmf_storage_path = None
        self.lxmf_destination = None
        self.lxmf_router = None
        self.telephone = None
        self._responses = []
        self._response_event = threading.Event()

        self._init_reticulum(configdir, rnsconfigdir, verbosity)
        self._init_lxmf(display_name)
        self._init_telephone()
        
    def run(self):
        self.should_run = True
        while self.should_run:
            time.sleep(1)

    def _init_reticulum(self, configdir, rnsconfigdir, verbosity):
        self.reticulum = RNS.Reticulum(
            configdir=rnsconfigdir, loglevel=3 + verbosity)
        
        if configdir is None:
            if os.path.isdir("/etc/lxst-ptt"):
                self.configdir = "/etc/lxst-ptt"
            else:
                userdir = RNS.Reticulum.userdir
                self.configdir = os.path.join(userdir, ".lxst-ptt")
        else:
            self.configdir = configdir
        os.makedirs(self.configdir, exist_ok=True)
        
        identity_path = os.path.join(self.configdir, "identity")
        if os.path.isfile(identity_path):
            self.reticulum_identity = RNS.Identity.from_file(identity_path)
            if self.reticulum_identity is None:
                self.reticulum_identity = RNS.Identity()
                self.reticulum_identity.to_file(identity_path)
        else:
            RNS.log("No identity found, generating new", RNS.LOG_NOTICE)
            self.reticulum_identity = RNS.Identity()
            self.reticulum_identity.to_file(identity_path)
            RNS.log(
                f"Generated identity: {RNS.prettyhexrep(self.reticulum_identity.hash)}",
                RNS.LOG_NOTICE,
            )
            
    def _init_lxmf(self, display_name):
        self.lxmf_storage_path = os.path.join(self.configdir, "lxmf")
        os.makedirs(self.lxmf_storage_path, exist_ok=True)
        
        self.lxmf_router = LXMF.LXMRouter(
            identity=self.reticulum_identity,
            storagepath=self.lxmf_storage_path,
        )
        
        self.lxmf_destination = self.lxmf_router.register_delivery_identity(
            self.reticulum_identity,
            display_name=display_name,
        )
        
        self.lxmf_router.register_delivery_callback(self._lxmf_delivery_callback)
        
        self.lxmf_destination.announce()

    def _init_telephone(self):
        self.telephone = Telephone(self.reticulum_identity)
        if self.whisplay_interface._wm8960_device:
            self.telephone.set_speaker(self.whisplay_interface._wm8960_device)
            self.telephone.set_microphone(self.whisplay_interface._wm8960_device)
            self.telephone.set_ringer(self.whisplay_interface._wm8960_device)
        self.telephone.set_established_callback(self._on_call_established)
        self.telephone.set_ended_callback(self._on_call_ended)
        self.telephone.announce()
    
    def _lxmf_delivery_callback(self, message):
        # handle incoming LXMF message, extract content and sender, and add to channel list if appropriate
        # checks sender against whitelist using reticulum as source of truth for identities
        content = message.content_as_string().strip()
        print(f"Received LXMF message from {RNS.prettyhexrep(message.source_hash)}: {content}")
        sender_hex = RNS.hexrep(message.source_hash, delimit=False)
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for h in data:
                    if isinstance(h, str) and len(h) in (32, 64):
                        self._responses.append({
                            "hash": h,
                            "relay": sender_hex,
                        })
        except (json.JSONDecodeError, ValueError):
            pass
        self._response_event.set()
        
    def _on_call_established(self, remote_identity):
        print(f"Call established with {RNS.prettyhexrep(remote_identity.hash)}")


    def _on_call_ended(self, remote_identity):
        print(f"Call ended with {RNS.prettyhexrep(remote_identity.hash)}")

class Router:
    def __init__(self, app):
        self.app = app
        self.current_screen = None
        self.screens = {
            "channels_list": ChannelsListScreen(app),
            "channel": ChannelScreen(app)
        }
    
    def navigate(self, screen_name):
        if screen_name in self.screens:
            self.current_screen = self.screens[screen_name]
            self.current_screen.display()
        else:
            print(f"Screen '{screen_name}' not found.")

class AppState:
    def __init__(self):
        self.channels = []
        self.current_channel = None


def main():
    parser = argparse.ArgumentParser(description="LXST PTT")
    parser.add_argument(
        "--config", "-c", default=None, help="config directory",
    )
    parser.add_argument(
        "--rnsconfig", default=None,
        help="path to alternative Reticulum config directory",
    )
    parser.add_argument(
        "--whitelist", "-w", default="./bridge_whitelist.json",
        help="path to bridge_whitelist.json",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="lxst_ptt 0.1.0",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument(
        "--announce_interval",
        default=0,
        help="seconds between destination announces (0 = announce once at startup, default)",
        type=int,
    )
    parser.add_argument(
        "--display_name",
        help="display name for this device (default: 'LXST PTT User')",
    )
    args = parser.parse_args()

    app = App(
        configdir=args.config,
        rnsconfigdir=args.rnsconfig,
        whitelist_path=args.whitelist,
        verbosity=args.verbose,
        announce_interval=args.announce_interval,
        display_name=args.display_name,
    )

    try:
        app.run()
    except KeyboardInterrupt:
        app.cleanup()
        print()

if __name__ == "__main__":
    main()
