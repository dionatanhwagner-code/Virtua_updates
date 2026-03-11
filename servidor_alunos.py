from flask import Flask, request, jsonify, render_template_string, Response
import threading
import json
import os
import datetime
import time

from pywebpush import webpush, WebPushException
import base64

# Chaves VAPID (geradas uma vez, fixas)
VAPID_PRIVATE_KEY = "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgmSf2jU9hCHDUYoB5j7bpXzFFvWvTd_DTttng6NEwPzmhRANCAAQHdgwdGjs1rQYDGK8gGNcpPlWrRWdpWYh-RaglUXEoIGSGFzJjC4m_IYlmk_FUrvc-p-Qo8CZ8ebp5S_zUpZFT"
VAPID_PUBLIC_KEY  = "BAd2DB0aOzWtBgMYryAY1yk-VatFZ2lZiH5FqCVRcSggZIYXMmMLib8hiWaT8VSu9z6n5CjwJnx5unlL_NSlkVM"
VAPID_CLAIMS      = {"sub": "mailto:virtua@local.com"}

# Subscriptions persistentes
_appdata = os.path.join(os.environ.get('APPDATA', ''), 'Virtua')
os.makedirs(_appdata, exist_ok=True)
SUBS_FILE = os.path.join(_appdata, 'subscriptions.json')

def carregar_subs():
    if os.path.exists(SUBS_FILE):
        with open(SUBS_FILE, 'r') as f:
            return json.load(f)
    return []

def salvar_subs(subs):
    with open(SUBS_FILE, 'w') as f:
        json.dump(subs, f)

subscriptions = carregar_subs()
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response

fila_comandos = []
respostas_virtua = {}

AGENDA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agenda.json')

def carregar_agenda():
    if os.path.exists(AGENDA_FILE):
        with open(AGENDA_FILE, encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_agenda_arquivo(agenda):
    with open(AGENDA_FILE, 'w', encoding='utf-8') as f:
        json.dump(agenda, f, ensure_ascii=False, indent=2)

HTML = r"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>VIRTUA</title>
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/icon.png">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
  background:#000010; color:#00FFFF;
  font-family:'Courier New',monospace;
  min-height:100vh; display:flex;
  flex-direction:column; align-items:center; padding:16px;
}
h1 { font-size:22px; letter-spacing:8px; margin-bottom:4px; color:#FFFFFF; }
.sub { font-size:11px; color:#004466; margin-bottom:16px; letter-spacing:2px; }
.status {
  background:#000D1A; border:1px solid #003344; border-radius:8px;
  padding:10px 20px; font-size:12px; color:#00AACC;
  margin-bottom:14px; width:100%; max-width:420px; text-align:center;
}
.input-area { display:flex; width:100%; max-width:420px; gap:8px; margin-bottom:10px; }
input[type=text] {
  flex:1; background:#000D1A; border:1px solid #003344; border-radius:8px;
  color:#00FFFF; font-family:'Courier New'; font-size:13px; padding:11px; outline:none;
}
input[type=text]::placeholder { color:#003355; }
input[type=date], input[type=time] {
  background:#000D1A; border:1px solid #003344; border-radius:8px;
  color:#00FFFF; font-family:'Courier New'; font-size:11px; padding:8px; outline:none; flex:1;
}
.btn-send {
  background:#003344; border:1px solid #00FFFF; border-radius:8px;
  color:#00FFFF; font-size:18px; padding:11px 16px; cursor:pointer;
}
.btn-mic {
  width:100%; max-width:420px; background:#1a0000;
  border:1px solid #FF4444; border-radius:8px; color:#FF6666;
  font-size:14px; padding:12px; cursor:pointer; margin-bottom:12px; text-align:center;
}
.btn-mic.ativo { background:#330000; animation:pulsar 0.8s infinite; }
@keyframes pulsar { 0%,100%{opacity:1} 50%{opacity:0.5} }
.secao { width:100%; max-width:420px; margin-bottom:6px; border:1px solid #003344; border-radius:8px; overflow:hidden; }
.secao-header {
  background:#000D1A; padding:12px 16px;
  display:flex; justify-content:space-between; align-items:center;
  cursor:pointer; user-select:none;
}
.secao-header:active { background:#001a2a; }
.secao-titulo { font-size:12px; letter-spacing:3px; color:#00AACC; }
.secao-arrow { color:#004466; font-size:14px; transition:transform 0.3s; }
.secao-arrow.aberto { transform:rotate(180deg); }
.secao-body { display:none; padding:10px; background:#00050f; }
.secao-body.aberto { display:block; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.btn {
  background:#001122; border:1px solid #003344; border-radius:8px;
  color:#00FFFF; font-family:'Courier New'; font-size:12px;
  padding:12px 8px; cursor:pointer; text-align:center; width:100%;
}
.btn:active { background:#003344; }
.btn-full {
  background:#001122; border:1px solid #003344; border-radius:8px;
  color:#00FFFF; font-family:'Courier New'; font-size:12px;
  padding:12px; cursor:pointer; text-align:center; width:100%; margin-bottom:8px;
}
.btn-full:active { background:#003344; }
.btn-green { border-color:#00FF88; color:#00FF88; background:#001a00; }
.btn-red { border-color:#FF4444; color:#FF6666; background:#1a0000; }
.btn-gold { border-color:#FFB300; color:#FFB300; background:#1a0e00; }
.ag-input {
  width:100%; background:#000D1A; border:1px solid #003344;
  border-radius:8px; color:#00FFFF; font-family:'Courier New';
  font-size:12px; padding:10px; margin-bottom:8px; outline:none;
}
.ag-row { display:flex; gap:8px; margin-bottom:8px; }
.agenda-div {
  background:#000D1A; border:1px solid #003344; border-radius:8px;
  padding:10px; font-size:11px; color:#AADDFF; margin-bottom:8px; display:none;
}
.resposta {
  background:#000D1A; border:1px solid #003344; border-radius:8px;
  padding:12px; font-size:12px; color:#AADDFF;
  width:100%; max-width:420px; min-height:50px; margin-top:12px; line-height:1.6;
}
.label { color:#004466; font-size:10px; margin-bottom:6px; }
</style>
</head>
<body>

<h1>[ VIRTUA ]</h1>
<div class="sub">ASSISTENTE VIRTUAL • DIONI</div>
<div class="status" id="status">○ Aguardando...</div>

<div class="input-area">
  <input type="text" id="cmd" placeholder="Digite um comando..." onkeypress="if(event.key==='Enter') enviar()">
  <button class="btn-send" onclick="enviar()">►</button>
</div>
<button class="btn-mic" id="micBtn" onclick="toggleMic()">🎤 Toque para falar</button>

<!-- AGENDA -->
<div class="secao">
  <div class="secao-header" onclick="toggle(this)">
    <span class="secao-titulo">📅 AGENDA</span>
    <span class="secao-arrow">▼</span>
  </div>
  <div class="secao-body">
    <button class="btn-full btn-green" onclick="verAgenda()">📋 Ver Compromissos de Hoje</button>
    <div class="agenda-div" id="agenda"></div>
    <input class="ag-input" type="text" id="ag_desc" placeholder="O que? Ex: Reunião com cliente">
    <div class="ag-row">
      <input type="date" id="ag_data">
      <input type="time" id="ag_hora">
    </div>
    <button class="btn-full btn-green" onclick="salvarAgenda()">✓ Salvar Compromisso</button>
  </div>
</div>

<!-- GASTOS -->
<div class="secao">
  <div class="secao-header" onclick="toggle(this)">
    <span class="secao-titulo">💸GASTOS</span>
    <span class="secao-arrow">▼</span>
  </div>
  <div class="secao-body">
    <input class="ag-input" type="text" id="gasto_desc" placeholder="Ex: mercado, combustivel, farmacia">
    <input class="ag-input" type="number" id="gasto_valor" placeholder="Valor em R$ Ex: 150.00" step="0.01">
    <button class="btn-full btn-green" onclick="registrarGasto()">✓ Registrar Gasto</button>
  </div>
</div>

<!-- MERCADO -->
<div class="secao">
  <div class="secao-header" onclick="toggle(this)">
    <span class="secao-titulo">💰 MERCADO</span>
    <span class="secao-arrow">▼</span>
  </div>
  <div class="secao-body">
    <div class="grid">
      <button class="btn" onclick="cmd('preco do ouro')">💰 Ouro</button>
      <button class="btn" onclick="cmd('preco do dolar')">💵 Dólar</button>
      <button class="btn" onclick="cmd('mercado abriu')">📊 Mercado</button>
      <button class="btn" onclick="cmd('me motiva')">⚡ Motiva</button>
    </div>
  </div>
</div>

<!-- PROGRAMAS -->
<div class="secao">
  <div class="secao-header" onclick="toggle(this)">
    <span class="secao-titulo">💻 PROGRAMAS</span>
    <span class="secao-arrow">▼</span>
  </div>
  <div class="secao-body">
    <div class="grid">
      <button class="btn" onclick="cmd('abrir mt5')">📈 MT5</button>
      <button class="btn" onclick="cmd('youtube')">▶️ YouTube</button>
      <button class="btn" onclick="cmd('whatsapp')">💬 WhatsApp</button>
      <button class="btn" onclick="cmd('instagram')">📷 Instagram</button>
      <button class="btn" onclick="cmd('google')">🔍 Google</button>
      <button class="btn" onclick="cmd('calculadora')">🔢 Calculadora</button>
      <button class="btn" onclick="cmd('bloco de notas')">📝 Bloco Notas</button>
      <button class="btn" onclick="cmd('paint')">🎨 Paint</button>
    </div>
  </div>
</div>

<!-- SISTEMA -->
<div class="secao">
  <div class="secao-header" onclick="toggle(this)">
    <span class="secao-titulo">⚙️ SISTEMA</span>
    <span class="secao-arrow">▼</span>
  </div>
  <div class="secao-body">
    <div class="grid">
      <button class="btn" onclick="cmd('espaco no hd')">💾 HD</button>
      <button class="btn" onclick="cmd('uso da memoria')">🧠 RAM</button>
      <button class="btn" onclick="cmd('temperatura hoje')">🌡️ Clima</button>
      <button class="btn" onclick="cmd('screenshot')">📸 Print</button>
      <button class="btn" onclick="cmd('volume alto')">🔊 Vol+</button>
      <button class="btn" onclick="cmd('volume baixo')">🔉 Vol-</button>
      <button class="btn" onclick="cmd('gerenciador')">📊 Tarefas</button>
      <button class="btn" onclick="cmd('bloquear')">🔒 Bloquear</button>
    </div>
  </div>
</div>

<!-- CONTROLE PC -->
<div class="secao">
  <div class="secao-header" onclick="toggle(this)">
    <span class="secao-titulo">🖥️ CONTROLE PC</span>
    <span class="secao-arrow">▼</span>
  </div>
  <div class="secao-body">
    <button class="btn-full btn-red" onclick="confirmar('desligar pc','Desligar o PC?')">🔴 Desligar PC</button>
    <button class="btn-full btn-gold" onclick="confirmar('reiniciar pc','Reiniciar o PC?')">🔄 Reiniciar PC</button>
    <button class="btn-full" onclick="cmd('cancelar desligamento')">✕ Cancelar Desligamento</button>
  </div>
</div>

<!-- VIRTUA -->
<div class="secao">
  <div class="secao-header" onclick="toggle(this)">
    <span class="secao-titulo">🤖 VIRTUA</span>
    <span class="secao-arrow">▼</span>
  </div>
  <div class="secao-body">
    <div class="grid">
      <button class="btn" onclick="cmd('que horas sao')">🕐 Horas</button>
      <button class="btn" onclick="cmd('que dia e hoje')">📅 Data</button>
      <button class="btn" onclick="cmd('me motiva')">⚡ Motiva</button>
      <button class="btn" onclick="cmd('como voce esta')">😊 Status</button>
      <button class="btn" onclick="cmd('quem e voce')">🤖 Quem és</button>
      <button class="btn" onclick="cmd('vamos trabalhar')">💪 Trabalhar</button>
    </div>
  </div>
</div>

<div class="resposta">
  <div class="label">[ RESPOSTA ]</div>
  <div id="resp">—</div>
</div>

<script>
function toggle(header) {
  const arrow = header.querySelector('.secao-arrow');
  const body = header.nextElementSibling;
  arrow.classList.toggle('aberto');
  body.classList.toggle('aberto');
}
function setStatus(txt) { document.getElementById('status').textContent = txt; }
function setResp(txt) { document.getElementById('resp').textContent = txt; }
function cmd(texto) { document.getElementById('cmd').value = texto; enviar(); }
function confirmar(texto, msg) { if(confirm(msg)) cmd(texto); }
function enviar() {
  const texto = document.getElementById('cmd').value.trim();
  if (!texto) return;
  setStatus('⟳ Enviando...');
  fetch('/comando', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({comando: texto})
  })
  .then(r => r.json())
  .then(d => {
    setStatus('✓ Enviado!');
    setResp(d.status || 'Executando...');
    document.getElementById('cmd').value = '';
    setTimeout(() => setStatus('○ Aguardando...'), 2000);
  })
  .catch(() => setStatus('✕ Erro de conexão'));
}
function verAgenda() {
  fetch('/agenda').then(r=>r.json()).then(data => {
    const div = document.getElementById('agenda');
    div.style.display = 'block';
    const hoje = new Date();
    const d = String(hoje.getDate()).padStart(2,'0');
    const m = String(hoje.getMonth()+1).padStart(2,'0');
    const y = hoje.getFullYear();
    const hoje_fmt = d+'/'+m+'/'+y;
    const comp = data.filter(c => c.data === hoje_fmt);
    if (comp.length === 0) {
      div.innerHTML = 'Nenhum compromisso hoje.';
    } else {
      div.innerHTML = comp.map(c =>
        '<div style="margin:4px 0;padding:6px;border-left:2px solid #00FF88">⏰ '+c.hora+' — '+c.descricao+'</div>'
      ).join('');
    }
  });
}
function salvarAgenda() {
  const desc = document.getElementById('ag_desc').value.trim();
  const data_val = document.getElementById('ag_data').value;
  const hora_val = document.getElementById('ag_hora').value;
  if (!desc || !data_val || !hora_val) { alert('Preencha todos os campos!'); return; }
  const parts = data_val.split('-');
  const data_br = parts[2]+'/'+parts[1]+'/'+parts[0];
  fetch('/agendar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({descricao: desc, data: data_br, hora: hora_val})
  }).then(r=>r.json()).then(() => {
    setStatus('✓ Compromisso salvo!');
    document.getElementById('ag_desc').value = '';
    setTimeout(() => setStatus('○ Aguardando...'), 2000);
  });
}
let recognition = null, micAtivo = false;
function toggleMic() {
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    alert('Use o Chrome!'); return;
  }
  if (micAtivo) { recognition.stop(); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = 'pt-BR';
  recognition.interimResults = false;
  recognition.onstart = () => {
    micAtivo = true;
    document.getElementById('micBtn').classList.add('ativo');
    document.getElementById('micBtn').textContent = '🔴 Ouvindo...';
    setStatus('🎤 Ouvindo...');
  };
  recognition.onresult = (e) => {
    document.getElementById('cmd').value = e.results[0][0].transcript;
    enviar();
  };
  recognition.onend = () => {
    micAtivo = false;
    document.getElementById('micBtn').classList.remove('ativo');
    document.getElementById('micBtn').textContent = '🎤 Toque para falar';
    setStatus('○ Aguardando...');
  };
  recognition.start();
}
// ── Salva gasto pendente se offline ─────────────────────────────────────────
function registrarGasto() {
  const desc = document.getElementById('gasto_desc').value.trim();
  const valor = document.getElementById('gasto_valor').value.trim();
  if (!desc || !valor) { alert('Preencha descrição e valor!'); return; }

  const comando = 'acrescente gastos com ' + desc + ' ' + valor + ' no dia de hoje';

  // Tenta enviar online
  fetch('/comando', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({comando: comando})
  })
  .then(r => r.json())
  .then(d => {
    setStatus('✓ Gasto registrado!');
    setTimeout(() => setStatus('○ Aguardando...'), 2000);
  })
  .catch(() => {
    // Offline — salva no celular
    const pendentes = JSON.parse(localStorage.getItem('gastos_pendentes') || '[]');
    pendentes.push({comando: comando, data: new Date().toLocaleString('pt-BR')});
    localStorage.setItem('gastos_pendentes', JSON.stringify(pendentes));
    setStatus('📥 Gasto salvo no celular! (' + pendentes.length + ' pendente(s))');
    setTimeout(() => setStatus('○ Aguardando...'), 3000);
  });

  document.getElementById('gasto_desc').value = '';
  document.getElementById('gasto_valor').value = '';
}

// ── Envia pendentes quando voltar online ────────────────────────────────────
async function enviarPendentes() {
  const pendentes = JSON.parse(localStorage.getItem('gastos_pendentes') || '[]');
  if (!pendentes.length) return;

  let enviados = 0;
  for (const item of pendentes) {
    try {
      fetch('/comando', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({comando: item.comando})
      });
      enviados++;
      await new Promise(r => setTimeout(r, 500));
    } catch(e) {
      break;
    }
  }

  localStorage.setItem('gastos_pendentes', JSON.stringify([]));
  if (enviados > 0) {
    alert('✅ ' + enviados + ' gasto(s) pendente(s) enviado(s)!');
  }
}

// ── Verifica pendentes ao carregar a página ──────────────────────────────────
window.addEventListener('load', () => {
  const pendentes = JSON.parse(localStorage.getItem('gastos_pendentes') || '[]');
  if (pendentes.length > 0) {
    setStatus('📥 ' + pendentes.length + ' gasto(s) pendente(s). Enviando...');
    enviarPendentes();
  }
  registrarPush();
});

// ── Push Notifications ───────────────────────────────────────────────────
async function registrarPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
  try {
    const reg = await navigator.serviceWorker.register('/sw.js');
    const perm = await Notification.requestPermission();
    if (perm !== 'granted') return;
    const keyResp = await fetch('/vapid-public-key');
    const {key} = await keyResp.json();
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: key
    });
    await fetch('/subscribe', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(sub)
    });
  } catch(e) { console.log('Push erro:', e); }
}
</script>
</body>
</html>

"""

# Read icon base64
import base64
icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'virtua_icon.png')

@app.route('/')
def index():
    return Response(HTML, mimetype='text/html')  

@app.route('/icon.png')
def icon():
    import io
    from flask import send_file
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'virtua_icon.png')
    if os.path.exists(icon_path):
        with open(icon_path, 'rb') as f:
            data = f.read()
        return send_file(io.BytesIO(data), mimetype='image/png')
    return "Icon not found", 404

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "VIRTUA",
        "short_name": "VIRTUA",
        "icons": [{"src": "/icon.png", "sizes": "512x512", "type": "image/png"}],
        "start_url": "/",
        "display": "standalone",
        "background_color": "#000010",
        "theme_color": "#00FFFF"
    })

@app.route('/comando', methods=['POST'])
def receber_comando():
    data = request.get_json()
    comando = data.get('comando', '').lower()
    
    if comando:
        id_cmd = str(time.time()) # Cria ID único
        fila_comandos.append([id_cmd, comando]) # Envia lista [ID, Comando]
        
        # Espera a Virtua processar por até 10 segundos
        for _ in range(300):
            if id_cmd in respostas_virtua:
                resposta_final = respostas_virtua.pop(id_cmd)
                return jsonify({'status': resposta_final})
            time.sleep(0.1)
            
        return jsonify({'status': 'Executado (Sem resposta visual)'})
    
    return jsonify({'status': 'Comando vazio'})

@app.route('/agenda')
def ver_agenda():
    return jsonify(carregar_agenda())

@app.route('/agendar', methods=['POST'])
def agendar():
    data = request.get_json()
    agenda = carregar_agenda()
    compromisso = {
        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "descricao": data.get('descricao', ''),
        "data": data.get('data', ''),
        "hora": data.get('hora', ''),
        "notificado": False
    }
    agenda.append(compromisso)
    salvar_agenda_arquivo(agenda)
    fila_comandos.append([str(time.time()), f"confirmar agendamento {data.get('descricao', '')}"])
    return jsonify({'status': 'Agendado!'})

@app.route('/status')
def status():
    return jsonify({'online': True})

# ── Push Notifications ───────────────────────────────────────────────────
@app.route('/vapid-public-key')
def vapid_public_key():
    return jsonify({'key': VAPID_PUBLIC_KEY})

@app.route('/subscribe', methods=['POST'])
def subscribe():
    sub = request.get_json()
    if sub and sub not in subscriptions:
        subscriptions.append(sub)
        salvar_subs(subscriptions)
    return jsonify({'status': 'ok'})

@app.route('/sw.js')
def service_worker():
    sw_content = """
self.addEventListener('push', function(e) {
    const data = e.data ? e.data.json() : {title:'VIRTUA', body:'Notificação'};
    e.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/icon.png',
            badge: '/icon.png',
            vibrate: [200, 100, 200]
        })
    );
});
"""
    return Response(sw_content, mimetype='application/javascript',
                    headers={'Service-Worker-Allowed': '/'})

def enviar_push(titulo, corpo):
    print(f"[PUSH] Tentando enviar para {len(subscriptions)} subscription(s)")
    mortos = []
    for sub in subscriptions:
        try:
            print(f"[PUSH] Enviando para {sub['endpoint'][:50]}...")
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": titulo, "body": corpo}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
            print("[PUSH] Enviado com sucesso!")
        except WebPushException as e:
            print(f"[PUSH] WebPushException: {e}")
            if "410" in str(e) or "404" in str(e):
                mortos.append(sub)
        except Exception as e:
            print(f"[PUSH] Erro: {e}")
    for m in mortos:
        subscriptions.remove(m)

def iniciar_servidor():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def start():
    t = threading.Thread(target=iniciar_servidor, daemon=True)
    t.start()