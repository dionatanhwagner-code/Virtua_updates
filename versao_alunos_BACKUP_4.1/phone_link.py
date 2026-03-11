"""
phone_link.py — Monitor de chamadas do Phone Link para Virtua
"""
import sqlite3, os, time, threading, re, shutil, datetime

PHONELINK_HANDLERS = [
    "Microsoft.YourPhone_8wekyb3d8bbwe!YourPhoneCalling",
    "Microsoft.YourPhone_8wekyb3d8bbwe!YourPhoneMessages",
    "Microsoft.YourPhone_8wekyb3d8bbwe!App",
]

def _get_db_path():
    return os.path.join(os.environ.get("LOCALAPPDATA",""),
                        r"Microsoft\Windows\Notifications\wpndatabase.db")

def _eh_phonelink(handler_id):
    return any(h in handler_id for h in PHONELINK_HANDLERS)

def _extrair_chamador(xml):
    m = re.search(r'<text[^>]*>([^<]{3,60})</text>', xml, re.IGNORECASE)
    if m:
        txt = m.group(1).strip()
        for p in ["Chamada de ", "Incoming call from ", "Call from "]:
            if txt.lower().startswith(p.lower()):
                txt = txt[len(p):]
        return txt
    return "número desconhecido"

def _monitor(falar_func, ouvir_func, parar_evento):
    db_path    = _get_db_path()
    ids_vistos = set()
    primeiro   = True
    print(f"[PhoneLink] Monitorando: {db_path}")

    while not parar_evento.is_set():
        try:
            if not os.path.exists(db_path):
                time.sleep(10); continue

            tmp = db_path + ".tmp_virtua"
            shutil.copy2(db_path, tmp)
            conn = sqlite3.connect(tmp)
            cur  = conn.cursor()
            cur.execute("""
                SELECT n.Id, h.PrimaryId, n.Payload, n.ArrivalTime
                FROM Notification n
                JOIN NotificationHandler h ON n.HandlerId = h.RecordId
                WHERE h.PrimaryId LIKE '%YourPhone%'
                ORDER BY n.ArrivalTime DESC LIMIT 20
            """)
            rows = cur.fetchall()
            conn.close()
            os.remove(tmp)

            if primeiro:
                for r in rows: ids_vistos.add(r[0])
                primeiro = False
                time.sleep(2); continue

            for nid, handler, payload, arrival in rows:
                if nid in ids_vistos: continue
                ids_vistos.add(nid)
                if not _eh_phonelink(str(handler)): continue

                p = payload.decode("utf-8", errors="ignore") if isinstance(payload, bytes) else str(payload)
                chamador = _extrair_chamador(p)
                eh_chamada = any(x in p.lower() for x in ["call","chamada","ligação"])

                if eh_chamada:
                    print(f"[PhoneLink] 📞 Chamada de: {chamador}")
                    falar_func(f"Dioni, chamada recebida de {chamador}.")
                    if ouvir_func:
                        time.sleep(0.8)
                        falar_func("Diga atender ou recusar.")
                        cmd = ouvir_func()
                        if cmd and "atender" in cmd.lower():
                            _atender_chamada()
                            falar_func("Atendendo chamada.")
                        elif cmd and any(x in cmd.lower() for x in ["recusar","rejeitar"]):
                            _recusar_chamada()
                            falar_func("Chamada recusada.")
                else:
                    print(f"[PhoneLink] 💬 Mensagem de: {chamador}")
                    falar_func(f"Dioni, você tem uma mensagem nova.")
        except Exception as e:
            print(f"[PhoneLink] Erro: {e}")
        time.sleep(3)

def _atender_chamada():
    try:
        import pygetwindow as gw, pyautogui, time
        for titulo in ["Vincular ao Celular", "Phone Link", "Your Phone"]:
            jans = gw.getWindowsWithTitle(titulo)
            if jans:
                jans[0].activate(); time.sleep(0.5)
                x = jans[0].left + jans[0].width  // 2 - 60
                y = jans[0].top  + jans[0].height - 80
                pyautogui.click(x, y); return
    except Exception as e:
        print(f"[PhoneLink] Erro atender: {e}")

def _recusar_chamada():
    try:
        import pygetwindow as gw, pyautogui, time
        for titulo in ["Vincular ao Celular", "Phone Link", "Your Phone"]:
            jans = gw.getWindowsWithTitle(titulo)
            if jans:
                jans[0].activate(); time.sleep(0.5)
                x = jans[0].left + jans[0].width  // 2 + 60
                y = jans[0].top  + jans[0].height - 80
                pyautogui.click(x, y); return
    except Exception as e:
        print(f"[PhoneLink] Erro recusar: {e}")

_parar = threading.Event()

def iniciar(falar_func, ouvir_func=None):
    _parar.clear()
    threading.Thread(target=_monitor, args=(falar_func, ouvir_func, _parar), daemon=True).start()
    print("[PhoneLink] Monitor iniciado ✓")

def parar():
    _parar.set()

if __name__ == "__main__":
    def falar_teste(t): print(f"🔊 VIRTUA: {t}")
    print("Testando Phone Link...")
    iniciar(falar_teste)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        parar()
