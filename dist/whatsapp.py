"""
whatsapp.py — Monitor WhatsApp via win32 COM / Shell notification
"""
import threading, time, os, re

_parar          = threading.Event()
_ultimo_anuncio = {}
INTERVALO       = 20

def _pode_anunciar(key):
    agora = time.time()
    if agora - _ultimo_anuncio.get(key, 0) > INTERVALO:
        _ultimo_anuncio[key] = agora
        return True
    return False

def _eh_chamada(texto):
    return any(t in texto.lower() for t in [
        "chamada","call","ligacao","voice","video call"])

def _monitor(falar_func, ouvir_func, parar_evento):
    try:
        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()

        # Monitora via Shell.Application — acessa notificações da bandeja
        # Alternativa: monitorar o log de eventos do Windows
        _monitor_eventlog(falar_func, ouvir_func, parar_evento)

    except Exception as e:
        print(f"[WhatsApp] win32 erro: {e}")
        _monitor_accessibility(falar_func, ouvir_func, parar_evento)

def _monitor_eventlog(falar_func, ouvir_func, parar_evento):
    """Monitora via Windows Event Log — WhatsApp registra eventos."""
    try:
        import win32evtlog
        import win32con

        server   = None  # local
        logtype  = "Application"
        hand     = win32evtlog.OpenEventLog(server, logtype)
        flags    = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

        print("[WhatsApp] Monitorando via EventLog...")
        ids_vistos = set()
        primeiro   = True

        while not parar_evento.is_set():
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            for ev in events:
                eid = (ev.RecordNumber, ev.TimeGenerated)
                if eid in ids_vistos: continue
                ids_vistos.add(eid)
                src = str(ev.SourceName).lower()
                msg = str(ev.StringInserts) if ev.StringInserts else ""
                if "whatsapp" in src or "whatsapp" in msg.lower():
                    if not primeiro:
                        print(f"[WhatsApp] EventLog: {src} | {msg[:100]}")
            primeiro = False
            time.sleep(3)

    except Exception as e:
        print(f"[WhatsApp] EventLog falhou: {e}")
        _monitor_accessibility(falar_func, ouvir_func, parar_evento)

def _monitor_accessibility(falar_func, ouvir_func, parar_evento):
    """
    Monitora via UI Automation — lê o conteúdo da janela do WhatsApp Desktop.
    Detecta badge de notificação na taskbar ou mudanças na lista de conversas.
    """
    try:
        import comtypes.client
        comtypes.client.GetModule("UIAutomationCore.dll")
        import comtypes.gen.UIAutomationClient as uia_client

        IUIAutomation = comtypes.CoCreateInstance(
            uia_client.CUIAutomation._reg_clsid_,
            interface=uia_client.IUIAutomation,
            clstype=uia_client.CUIAutomation
        )
        print("[WhatsApp] UI Automation ativo ✓")

        ultimo_badge = 0

        while not parar_evento.is_set():
            try:
                import pygetwindow as gw
                # Tenta ler badge da taskbar via UI Automation
                root = IUIAutomation.GetRootElement()
                cond = IUIAutomation.CreatePropertyCondition(
                    uia_client.UIA_NamePropertyId, "WhatsApp"
                )
                el = root.FindFirst(uia_client.TreeScope_Descendants, cond)
                if el:
                    name = el.CurrentName
                    print(f"[WhatsApp] UI: {name}")
                    m = re.search(r'(\d+)', name)
                    if m:
                        count = int(m.group(1))
                        if count > ultimo_badge and _pode_anunciar("msg"):
                            falar_func(f"Dioni, {count} mensagem no WhatsApp.")
                        ultimo_badge = count
            except: pass
            time.sleep(3)

    except Exception as e:
        print(f"[WhatsApp] UIAutomation falhou: {e}")
        _monitor_simples(falar_func, ouvir_func, parar_evento)

def _monitor_simples(falar_func, ouvir_func, parar_evento):
    """
    Última alternativa: screenshot da área de notificação da taskbar
    e OCR para detectar badge do WhatsApp.
    """
    try:
        import pygetwindow as gw
        import pyautogui
        from PIL import Image
        import pytesseract

        print("[WhatsApp] Monitor via screenshot/OCR ativo ✓")
        ultimo = 0

        while not parar_evento.is_set():
            try:
                # Captura só a barra de tarefas (parte inferior)
                w, h = pyautogui.size()
                img = pyautogui.screenshot(region=(0, h-50, w, 50))
                txt = pytesseract.image_to_string(img)
                nums = re.findall(r'\b(\d{1,3})\b', txt)
                for n in nums:
                    count = int(n)
                    if count > 0 and count != ultimo and _pode_anunciar("badge"):
                        print(f"[WhatsApp] Badge detectado: {count}")
                        falar_func(f"Dioni, mensagem nova no WhatsApp.")
                        ultimo = count
            except: pass
            time.sleep(5)

    except Exception as e:
        print(f"[WhatsApp] Todas as abordagens falharam: {e}")
        print("[WhatsApp] WhatsApp Desktop não expõe notificações acessíveis.")

def _abrir_whatsapp():
    try:
        import pygetwindow as gw
        jans = [w for w in gw.getAllWindows() if "whatsapp" in w.title.lower()]
        if jans: jans[0].activate(); return
    except: pass
    try: os.startfile("whatsapp:")
    except: pass

def iniciar(falar_func, ouvir_func=None):
    _parar.clear()
    threading.Thread(
        target=_monitor,
        args=(falar_func, ouvir_func, _parar),
        daemon=True
    ).start()
    print("[WhatsApp] Monitor iniciado ✓")

def parar():
    _parar.set()

if __name__ == "__main__":
    def falar_teste(t): print(f"🔊 VIRTUA: {t}")
    iniciar(falar_teste)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        parar()
