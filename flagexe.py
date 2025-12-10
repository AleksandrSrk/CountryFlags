import os
import sys
import time
import requests
import pystray
from PIL import Image
import winreg as reg


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Папка с флагами
FLAGS_DIR = resource_path("flags")
UPDATE_INTERVAL = 60  # секунд

# Глобальный флаг для ручного обновления
force_refresh = False


def get_country():
    try:
        resp = requests.get("https://freeipapi.com/api/json", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        code = (data.get("countryCode", "") or "").lower()
        name = data.get("countryName", "Unknown")
        print("country OK:", code, name)
        return {"country_code": code, "country_name": name}
    except Exception as e:
        print("get_country ERROR:", repr(e))
        return {"country_code": "", "country_name": "Unknown"}


def load_flag(code: str) -> Image.Image:
    try:
        if not code:
            raise FileNotFoundError("empty country code")

        path_png = os.path.join(FLAGS_DIR, f"{code}.png")
        path_ico = os.path.join(FLAGS_DIR, f"{code}.ico")

        if os.path.exists(path_png):
            path = path_png
        elif os.path.exists(path_ico):
            path = path_ico
        else:
            raise FileNotFoundError(f"flag not found for {code}")

        img = Image.open(path)
        img = img.resize((32, 32), Image.Resampling.LANCZOS)
        print("flag loaded from", path)
        return img
    except Exception as e:
        print("load_flag ERROR:", repr(e))
        return Image.new("RGB", (32, 32), (255, 0, 0))


def updater(icon: pystray.Icon):
    print("updater started")
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
                img = load_flag(code)
                icon.icon = img
                last_code = code

            last_update = now
        time.sleep(1)


def on_exit(icon, item):
    icon.stop()


def on_refresh(icon, item):
    global force_refresh
    print("manual refresh requested")
    force_refresh = True


def add_to_startup():
    """Добавляет программу в автозагрузку Windows (только один раз)"""
    try:
        key = reg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        exe_path = sys.executable

        with reg.OpenKey(key, key_path, 0, reg.KEY_ALL_ACCESS) as reg_key:
            try:
                reg.QueryValueEx(reg_key, "CountryFlagsTray")
                return  # уже есть
            except FileNotFoundError:
                reg.SetValueEx(reg_key, "CountryFlagsTray", 0, reg.REG_SZ, exe_path)
                print("Добавлено в автозагрузку")
    except PermissionError:
        print("Нет прав для записи в реестр")
    except Exception as e:
        print("Ошибка автозагрузки:", e)


def main():
    img = Image.new("RGB", (32, 32), (50, 50, 50))
    menu = pystray.Menu(
        pystray.MenuItem("Обновить сейчас", on_refresh),
        pystray.MenuItem("Выход", on_exit),
    )
    icon = pystray.Icon("ip_flag", icon=img, title="IP Flag", menu=menu)
    icon.run_detached()
    updater(icon)


# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
# Автозагрузка — вызываем сразу при запуске
add_to_startup()
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

if __name__ == "__main__":
    main()