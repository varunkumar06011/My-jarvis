import winreg
import os
import sys
from pathlib import Path


APP_NAME = "Jarvis"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_auto_start_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable_auto_start():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        python_exe = sys.executable
        bootstrap_path = Path(__file__).parent / "bootstrap.py"
        value = f'"{python_exe}" "{bootstrap_path}"'
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        return True
    except OSError as e:
        print(f"Failed to enable auto start: {e}")
        return False


def disable_auto_start():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except OSError as e:
        print(f"Failed to disable auto start: {e}")
        return False
