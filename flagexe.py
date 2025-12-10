import os
import sys
import time
import requests
import pystray
from PIL import Image
import winreg as reg
import threading
import ctypes
from ctypes import wintypes

# ------------------------------------------------------------------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

FLAGS_DIR = resource_path("flags")
UPDATE_INTERVAL = 60
force_refresh = False

# ------------------------------------------------------------------
def get_country():
    try:
        resp = requests.get("https://freeipapi.com/api/json", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        code = (data.get("countryCode", "") or "").lower()
        name = data.get("countryName", "Unknown")
        return {"country_code": code, "country_name": name}
    except:
        return {"country_code": "", "country_name": "Unknown"}

def load_flag(code: str) -> Image.Image:
    try:
        if not code:
            raise FileNotFoundError
        for ext in (".png", ".ico"):
            path = os.path.join(FLAGS_DIR, code + ext)
            if os.path.exists(path):
                img = Image.open(path).resize((32, 32), Image.Resampling.LANCZOS)
                return img
        raise FileNotFoundError
    except:
        return Image.new("RGB", (32, 32), (255, 0, 0))

# ------------------------------------------------------------------
def updater(icon: pystray.Icon):
    last_code = None
    last_update = 0
    global force_refresh

    while True:
        now = time.time()
        if force_refresh or now - last_update >= UPDATE_INTERVAL:
            force_refresh = False
            info = get_country()
            code = info["country_code"]
            name = info["country_name"]

            icon.title = f"{name} ({code.upper()})" if code else name
            if code != last_code:
                icon.icon = load_flag(code)
                last_code = code
            last_update = now
        time.sleep(1)

def on_refresh(icon, item):
    global force_refresh
    force_refresh = True

def on_exit(icon, item):
    icon.stop()
    # Принудительно убиваем ВЕСЬ процесс Windows-стилем
    ctypes.windll.kernel32.ExitProcess(0)

# ------------------------------------------------------------------
def add_to_startup():
    try:
        key = reg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        exe_path = sys.executable

        with reg.OpenKey(key, key_path, 0, reg.KEY_ALL_ACCESS) as rk:
            try:
                reg.QueryValueEx(rk, "CountryFlagsTray")
                return
            except FileNotFoundError:
                reg.SetValueEx(rk, "CountryFlagsTray", 0, reg.REG_SZ, exe_path)
    except:
        pass

# ------------------------------------------------------------------
def main():
    img = Image.new("RGB", (32, 32), (50, 50, 50))
    menu = pystray.Menu(
        pystray.MenuItem("Обновить сейчас", on_refresh),
        pystray.MenuItem("Выход", on_exit),
    )
    icon = pystray.Icon("CountryFlags", icon=img, title="IP Flag", menu=menu)

    # Запускаем иконку в отдельном НЕ-демоническом потоке
    threading.Thread(target=icon.run, daemon=False).start()

    # Основной цикл — updater
    updater(icon)

# ------------------------------------------------------------------
add_to_startup()

if __name__ == "__main__":
    main()