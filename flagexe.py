import os
import sys
import time
import requests
import pystray
from PIL import Image
import winreg as reg
import threading
import ctypes

# ------------------------------------------------------------------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

FLAGS_DIR = resource_path("flags")
UPDATE_INTERVAL = 60

stop_event = threading.Event()
refresh_event = threading.Event()

# ------------------------------------------------------------------
def get_country():
    try:
        resp = requests.get("https://freeipapi.com/api/json", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        code = (data.get("countryCode", "") or "").lower()
        name = data.get("countryName", "Unknown")
        return code, name
    except Exception:
        return "", "Unknown"

def load_flag(code: str) -> Image.Image:
    if code:
        for ext in (".png", ".ico"):
            path = os.path.join(FLAGS_DIR, code + ext)
            if os.path.exists(path):
                return Image.open(path).resize((32, 32), Image.Resampling.LANCZOS)
    return Image.new("RGB", (32, 32), (255, 0, 0))

# ------------------------------------------------------------------
def updater(icon: pystray.Icon):
    last_code = None
    last_update = 0

    while not stop_event.is_set():
        now = time.time()
        if refresh_event.is_set() or now - last_update >= UPDATE_INTERVAL:
            refresh_event.clear()
            code, name = get_country()

            icon.title = f"{name} ({code.upper()})" if code else name
            if code != last_code:
                icon.icon = load_flag(code)
                if last_code is not None and code:
                    icon.notify(f"{name} ({code.upper()})", "CountryFlags")
                last_code = code
            last_update = now

        stop_event.wait(1)

def on_refresh(icon, item):
    refresh_event.set()

def on_exit(icon, item):
    stop_event.set()
    icon.stop()

# ------------------------------------------------------------------
def sync_startup():
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        exe_path = f'"{sys.executable}"'
        with reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS) as rk:
            # Удаляем старое имя ключа если осталось
            try:
                reg.DeleteValue(rk, "CountryFlagsTray")
            except FileNotFoundError:
                pass
            # Создаём или обновляем (если путь изменился — при переносе папки)
            try:
                current, _ = reg.QueryValueEx(rk, "CountryFlags")
                if current != exe_path:
                    reg.SetValueEx(rk, "CountryFlags", 0, reg.REG_SZ, exe_path)
            except FileNotFoundError:
                reg.SetValueEx(rk, "CountryFlags", 0, reg.REG_SZ, exe_path)
    except Exception:
        pass

def ensure_single_instance():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "CountryFlagsTrayMutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)
    return mutex  # держим ссылку, чтобы мьютекс жил

# ------------------------------------------------------------------
def main():
    _mutex = ensure_single_instance()
    sync_startup()

    img = Image.new("RGB", (32, 32), (50, 50, 50))
    menu = pystray.Menu(
        pystray.MenuItem("Обновить сейчас", on_refresh),
        pystray.MenuItem("Выход", on_exit),
    )
    icon = pystray.Icon("CountryFlags", icon=img, title="IP Flag", menu=menu)

    threading.Thread(target=updater, args=(icon,), daemon=True).start()
    icon.run()

# ------------------------------------------------------------------
if __name__ == "__main__":
    main()
