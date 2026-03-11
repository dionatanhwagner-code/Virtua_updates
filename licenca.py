import hashlib
import subprocess
import json
import os
import sys
import tkinter as tk

def get_machine_id():
    """Gera um ID único baseado no hardware da máquina."""
    try:
        # Serial da placa mãe
        mb = subprocess.check_output(
            "wmic baseboard get serialnumber",
            shell=True, stderr=subprocess.DEVNULL
        ).decode(errors="ignore").split()[-1].strip()
    except:
        mb = "unknown_mb"

    try:
        # UUID da máquina
        uuid = subprocess.check_output(
            "wmic csproduct get uuid",
            shell=True, stderr=subprocess.DEVNULL
        ).decode(errors="ignore").split()[-1].strip()
    except:
        uuid = "unknown_uuid"

    try:
        # Serial do disco C:
        disk = subprocess.check_output(
            "wmic diskdrive get serialnumber",
            shell=True, stderr=subprocess.DEVNULL
        ).decode(errors="ignore").split()[-1].strip()
    except:
        disk = "unknown_disk"

    raw = f"{mb}-{uuid}-{disk}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def verificar_licenca(config_path):
    """
    Verifica a licença da máquina.
    - Primeira execução: salva o ID no config.json
    - Execuções seguintes: verifica se o ID bate
    - Se não bater: mostra tela de bloqueio e fecha
    """
    machine_id = get_machine_id()

    # Carrega o config.json
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8-sig") as f:
            config = json.load(f)
    else:
        config = {}

    # Primeira execução — salva o ID
    if not config.get("machine_id"):
        config["machine_id"] = machine_id
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True  # Liberado!

    # Execuções seguintes — verifica
    if config["machine_id"] == machine_id:
        return True  # Máquina autorizada!

    # Máquina diferente — bloqueia
    _tela_bloqueio()
    return False


def _tela_bloqueio():
    """Tela de bloqueio quando a licença não é válida."""
    root = tk.Tk()
    root.title("VIRTUA — Licença Inválida")
    root.configure(bg="#000010")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    w, h = 480, 320
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    tk.Label(root, text="[ VIRTUA ]", bg="#000010", fg="#FFFFFF",
             font=("Courier", 20, "bold")).pack(pady=(40, 4))

    tk.Label(root, text="⛔  LICENÇA INVÁLIDA", bg="#000010", fg="#FF4444",
             font=("Courier", 14, "bold")).pack(pady=(10, 4))

    tk.Label(root,
             text="Esta licença está registrada em outro computador.\nEntre em contato para suporte.",
             bg="#000010", fg="#888888",
             font=("Courier", 10), justify="center").pack(pady=(10, 30))

    tk.Button(root, text="Fechar", bg="#1a0000", fg="#FF4444",
              font=("Courier", 11, "bold"), bd=0, padx=20, pady=8,
              cursor="hand2", command=lambda: [root.destroy(), sys.exit()]
              ).pack()

    root.mainloop()
    sys.exit()
