import threading
from PIL import Image, ImageDraw

import pystray

from app.lifecycle import State, LifecycleManager
from app import settings


class TrayIcon:
    def __init__(self, lifecycle: LifecycleManager, on_exit=None):
        self.lifecycle = lifecycle
        self.on_exit = on_exit
        self.icon = None

    def _create_image(self):
        size = 64
        img = Image.new("RGB", (size, size), (30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.ellipse(
            [size // 4, size // 4, 3 * size // 4, 3 * size // 4],
            fill=(0, 200, 100),
        )
        return img

    def _get_state_label(self, item=None):
        state = self.lifecycle.state
        icons = {
            State.STARTING: "🔄",
            State.READY: "✅",
            State.LISTENING: "🎤",
            State.PROCESSING: "🧠",
            State.SPEAKING: "🔊",
            State.IDLE: "💤",
            State.SHUTDOWN: "⏹️",
        }
        return f"{icons.get(state, '❓')} Jarvis - {state.value}"

    def _on_open(self, icon, item):
        pass

    def _on_restart(self, icon, item):
        print("[Tray] Restart requested")

    def _on_reload(self, icon, item):
        print("[Tray] Reload plugins requested")

    def _on_toggle_auto_start(self, icon, item):
        if settings.is_auto_start_enabled():
            settings.disable_auto_start()
            print("[Tray] Auto start disabled")
        else:
            settings.enable_auto_start()
            print("[Tray] Auto start enabled")

    def _on_open_logs(self, icon, item):
        import subprocess
        from pathlib import Path

        log_dir = Path(__file__).parent.parent / "logs"
        if log_dir.exists():
            subprocess.Popen(["explorer", str(log_dir)])

    def _on_exit(self, icon, item):
        print("[Tray] Exit requested")
        if self.on_exit:
            self.on_exit()
        icon.stop()

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                self._get_state_label,
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open", self._on_open),
            pystray.MenuItem("Restart AI", self._on_restart),
            pystray.MenuItem("Reload Plugins", self._on_reload),
            pystray.MenuItem(
                "Auto Start with Windows",
                self._on_toggle_auto_start,
                checked=lambda item: settings.is_auto_start_enabled(),
            ),
            pystray.MenuItem("Open Logs", self._on_open_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_exit),
        )

    def _update_state_label(self, old_state, new_state):
        if self.icon:
            self.icon.title = self._get_state_label()

    def start(self):
        self.lifecycle.on_change(self._update_state_label)

        self.icon = pystray.Icon(
            "Jarvis",
            self._create_image(),
            self._get_state_label(),
            self._build_menu(),
        )

        tray_thread = threading.Thread(target=self.icon.run, daemon=True)
        tray_thread.start()

    def stop(self):
        if self.icon:
            self.icon.stop()
