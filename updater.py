import os
import sys
import shutil
import subprocess
import psutil
import time

APP_NAME = "virtua_alunos.exe"
APP_DIR = os.path.join(os.environ.get("APPDATA",""), "Virtua")
APP_PATH = os.path.join(APP_DIR, APP_NAME)
UPDATE_DIR = os.path.join(APP_DIR, "_update")
NEW_PATH = os.path.join(UPDATE_DIR, APP_NAME)

def fechar_app():
    for proc in psutil.process_iter(['pid','name']):
        if proc.info['name'] and proc.info['name'].lower() == APP_NAME.lower():
            proc.kill()
    time.sleep(2)

def substituir_exe():
    if not os.path.exists(NEW_PATH):
        print("Novo EXE não encontrado na pasta _update!")
        sys.exit()
    if os.path.exists(APP_PATH):
        os.remove(APP_PATH)
    shutil.move(NEW_PATH, APP_PATH)

def iniciar_app():
    subprocess.Popen([APP_PATH])

if __name__ == "__main__":
    fechar_app()
    substituir_exe()
    iniciar_app()
    sys.exit()