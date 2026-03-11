import os
import json
import threading
import time

# ==================== CONFIGURAÇÃO ====================

_appdata = os.path.join(os.environ.get('APPDATA', ''), 'Virtua')
os.makedirs(_appdata, exist_ok=True)
DISPOSITIVOS_FILE = os.path.join(_appdata, 'dispositivos.json')

# ==================== GERENCIAMENTO DE DISPOSITIVOS ====================

def carregar_dispositivos():
    if os.path.exists(DISPOSITIVOS_FILE):
        with open(DISPOSITIVOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_dispositivos(dispositivos):
    with open(DISPOSITIVOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(dispositivos, f, ensure_ascii=False, indent=2)

def adicionar_dispositivo(nome, tipo, marca, device_id, ip="", local_key="", extra={}, incluir_no_tudo=True):
    dispositivos = carregar_dispositivos()
    dispositivo = {
        "nome": nome.lower().strip(),
        "tipo": tipo,       # lampada, tomada, ar, ir, samsung
        "marca": marca,     # tuya, samsung, outro
        "device_id": device_id,
        "ip": ip,
        "local_key": local_key,
        "extra": extra,     # dados extras (ex: token SmartThings)
        "incluir_no_tudo": incluir_no_tudo,
        "ligado": False
    }
    # Atualiza se já existe
    for i, d in enumerate(dispositivos):
        if d["nome"] == dispositivo["nome"]:
            dispositivos[i] = dispositivo
            salvar_dispositivos(dispositivos)
            return dispositivo
    dispositivos.append(dispositivo)
    salvar_dispositivos(dispositivos)
    return dispositivo

def remover_dispositivo(nome):
    dispositivos = carregar_dispositivos()
    dispositivos = [d for d in dispositivos if d["nome"] != nome.lower().strip()]
    salvar_dispositivos(dispositivos)

def buscar_dispositivo(nome_falado):
    """Busca dispositivo por nome parcial falado."""
    dispositivos = carregar_dispositivos()
    nome_falado = nome_falado.lower().strip()
    # Busca exata primeiro
    for d in dispositivos:
        if d["nome"] == nome_falado:
            return d
    # Busca parcial
    for d in dispositivos:
        if d["nome"] in nome_falado or nome_falado in d["nome"]:
            return d
    return None

# ==================== CONTROLE TUYA ====================

def _tuya_comando(dispositivo, ligar):
    try:
        import tinytuya
        d = tinytuya.OutletDevice(
            dev_id=dispositivo["device_id"],
            address=dispositivo["ip"],
            local_key=dispositivo["local_key"],
            version=3.3
        )
        d.set_status(ligar, switch=1)
        return True
    except Exception as e:
        print(f"Erro Tuya ({dispositivo['nome']}): {e}")
        return False

def _tuya_lampada_cor(dispositivo, r, g, b):
    try:
        import tinytuya
        d = tinytuya.BulbDevice(
            dev_id=dispositivo["device_id"],
            address=dispositivo["ip"],
            local_key=dispositivo["local_key"],
            version=3.3
        )
        d.set_colour(r, g, b)
        return True
    except Exception as e:
        print(f"Erro Tuya cor ({dispositivo['nome']}): {e}")
        return False

def _tuya_ar(dispositivo, ligar, temperatura=24, modo="auto"):
    try:
        import tinytuya
        d = tinytuya.Device(
            dev_id=dispositivo["device_id"],
            address=dispositivo["ip"],
            local_key=dispositivo["local_key"],
            version=3.3
        )
        if ligar:
            d.set_multiple_values({
                "1": True,
                "2": modo,
                "16": temperatura
            })
        else:
            d.set_value(1, False)
        return True
    except Exception as e:
        print(f"Erro Tuya AR ({dispositivo['nome']}): {e}")
        return False

def _tuya_ir(dispositivo, comando):
    """Envia comando IR (tv, som, etc)."""
    try:
        import tinytuya
        d = tinytuya.Device(
            dev_id=dispositivo["device_id"],
            address=dispositivo["ip"],
            local_key=dispositivo["local_key"],
            version=3.3
        )
        # Comandos IR mapeados no extra do dispositivo
        comandos_ir = dispositivo.get("extra", {}).get("comandos", {})
        if comando in comandos_ir:
            d.set_value(201, comandos_ir[comando])
            return True
        else:
            print(f"Comando IR '{comando}' não mapeado para {dispositivo['nome']}")
            return False
    except Exception as e:
        print(f"Erro Tuya IR ({dispositivo['nome']}): {e}")
        return False

# ==================== CONTROLE SAMSUNG SMARTTHINGS ====================

def _samsung_comando(dispositivo, ligar):
    try:
        import asyncio
        import aiohttp

        token = dispositivo.get("extra", {}).get("token", "")
        device_id = dispositivo["device_id"]

        async def _executar():
            async with aiohttp.ClientSession() as session:
                url = f"https://api.smartthings.com/v1/devices/{device_id}/commands"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                comando = "on" if ligar else "off"
                payload = {"commands": [{"component": "main", "capability": "switch", "command": comando}]}
                async with session.post(url, headers=headers, json=payload) as resp:
                    return resp.status == 200

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_executar())
        loop.close()
        return result
    except Exception as e:
        print(f"Erro Samsung ({dispositivo['nome']}): {e}")
        return False

def _samsung_volume(dispositivo, volume):
    try:
        import asyncio
        import aiohttp

        token = dispositivo.get("extra", {}).get("token", "")
        device_id = dispositivo["device_id"]

        async def _executar():
            async with aiohttp.ClientSession() as session:
                url = f"https://api.smartthings.com/v1/devices/{device_id}/commands"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                payload = {"commands": [{"component": "main", "capability": "audioVolume", "command": "setVolume", "arguments": [volume]}]}
                async with session.post(url, headers=headers, json=payload) as resp:
                    return resp.status == 200

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_executar())
        loop.close()
        return result
    except Exception as e:
        print(f"Erro Samsung volume ({dispositivo['nome']}): {e}")
        return False

# ==================== INTERFACE UNIFICADA ====================

def ligar(nome_dispositivo):
    d = buscar_dispositivo(nome_dispositivo)
    if not d:
        return False, f"Dispositivo '{nome_dispositivo}' não encontrado."
    ok = False
    if d["marca"] == "tuya":
        ok = _tuya_comando(d, True)
    elif d["marca"] == "samsung":
        ok = _samsung_comando(d, True)
    if ok:
        # Atualiza estado
        dispositivos = carregar_dispositivos()
        for disp in dispositivos:
            if disp["nome"] == d["nome"]:
                disp["ligado"] = True
        salvar_dispositivos(dispositivos)
        return True, f"{d['nome'].capitalize()} ligado!"
    return False, f"Erro ao ligar {d['nome']}."

def desligar(nome_dispositivo):
    d = buscar_dispositivo(nome_dispositivo)
    if not d:
        return False, f"Dispositivo '{nome_dispositivo}' não encontrado."
    ok = False
    if d["marca"] == "tuya":
        ok = _tuya_comando(d, False)
    elif d["marca"] == "samsung":
        ok = _samsung_comando(d, False)
    if ok:
        dispositivos = carregar_dispositivos()
        for disp in dispositivos:
            if disp["nome"] == d["nome"]:
                disp["ligado"] = False
        salvar_dispositivos(dispositivos)
        return True, f"{d['nome'].capitalize()} desligado!"
    return False, f"Erro ao desligar {d['nome']}."

def controlar_ar(nome_dispositivo, ligar_ar, temperatura=24, modo="auto"):
    d = buscar_dispositivo(nome_dispositivo)
    if not d:
        return False, f"Dispositivo '{nome_dispositivo}' não encontrado."
    ok = False
    if d["marca"] == "tuya":
        ok = _tuya_ar(d, ligar_ar, temperatura, modo)
    if ok:
        acao = f"ligado em {temperatura} graus" if ligar_ar else "desligado"
        return True, f"Ar condicionado {acao}!"
    return False, f"Erro ao controlar ar condicionado."

def controlar_volume(nome_dispositivo, volume):
    d = buscar_dispositivo(nome_dispositivo)
    if not d:
        return False, f"Dispositivo '{nome_dispositivo}' não encontrado."
    ok = False
    if d["marca"] == "samsung":
        ok = _samsung_volume(d, volume)
    if ok:
        return True, f"Volume da {d['nome']} ajustado para {volume}!"
    return False, f"Erro ao ajustar volume."

def comando_ir(nome_dispositivo, comando):
    d = buscar_dispositivo(nome_dispositivo)
    if not d:
        return False, f"Dispositivo '{nome_dispositivo}' não encontrado."
    ok = _tuya_ir(d, comando)
    if ok:
        return True, f"Comando '{comando}' enviado para {d['nome']}!"
    return False, f"Comando não mapeado."

def ligar_tudo():
    dispositivos = carregar_dispositivos()
    sucessos = 0
    for d in dispositivos:
        if d.get("incluir_no_tudo", True):
            ok, _ = ligar(d["nome"])
            if ok:
                sucessos += 1
    return sucessos

def desligar_tudo():
    dispositivos = carregar_dispositivos()
    sucessos = 0
    for d in dispositivos:
        if d.get("incluir_no_tudo", True):
            ok, _ = desligar(d["nome"])
            if ok:
                sucessos += 1
    return sucessos

def listar_dispositivos():
    dispositivos = carregar_dispositivos()
    if not dispositivos:
        return "Nenhum dispositivo cadastrado."
    nomes = [f"{d['nome']} ({'ligado' if d.get('ligado') else 'desligado'})" for d in dispositivos]
    return ", ".join(nomes)
