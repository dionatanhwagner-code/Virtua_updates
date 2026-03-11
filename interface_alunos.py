"""
VIRTUA — Interface PyQt6
Compatível 100% com virtua_main.py
"""
import sys, os, math, time, random, datetime, json, socket, threading
import automacao

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QTextEdit, QLineEdit,
    QCheckBox, QScrollArea, QDialog, QMessageBox, QListWidget
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QObject
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QRadialGradient, QPainterPath, QCursor
)

# ── CONFIG ────────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.environ.get('APPDATA', ''), 'Virtua', 'config.json')

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"nome": "", "claude_key": "", "Groq_Cloud": "", "ngrok_token": "", "cidade": ""}

def salvar_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

# ── TELA DE SETUP ─────────────────────────────────────────────────────────────
def tela_setup():
    app = QApplication.instance() or QApplication(sys.argv)
    dlg = QDialog()
    dlg.setWindowTitle("VIRTUA — Configuração")
    dlg.setFixedSize(500, 660)
    dlg.setStyleSheet("background:#020510;")

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(40, 28, 40, 28)
    lay.setSpacing(6)

    def lbl(txt, cor="#00FFFF", size=11, bold=False):
        l = QLabel(txt)
        l.setFont(QFont("Courier New", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
        l.setStyleSheet(f"color:{cor};background:transparent;")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return l

    def inp(ph, hide=False):
        e = QLineEdit()
        e.setPlaceholderText(ph)
        e.setFont(QFont("Courier New", 10))
        if hide: e.setEchoMode(QLineEdit.EchoMode.Password)
        e.setStyleSheet("QLineEdit{background:#000D1A;color:#00FFFF;"
                        "border:1px solid #003344;border-radius:8px;padding:8px;}")
        return e

    lay.addWidget(lbl("V I R T U A", "#00FFFF", 28, True))
    lay.addWidget(lbl("SISTEMA DE OPERAÇÕES XAUUSD", "#004466", 10))
    lay.addSpacing(8)

    cfg = carregar_config()
    campos = []
    for label, key, ph, hide in [
        ("SEU NOME:",       "nome",        "Ex: Dioni",       False),
        ("SUA CIDADE:",     "cidade",      "Ex: São Paulo",   False),
        ("CLAUDE API KEY:", "claude_key",  "Chave Anthropic", True),
        ("GROQ API KEY:",   "Groq_Cloud",  "Chave Groq",      True),
        ("NGROK TOKEN:",    "ngrok_token", "Seu Token Ngrok", True),
    ]:
        lay.addWidget(lbl(label, "#00AACC", 10, True))
        e = inp(ph, hide)
        e.setText(cfg.get(key, ""))
        lay.addWidget(e)
        campos.append((key, e))

    ip = get_ip_local()
    lay.addSpacing(8)
    lay.addWidget(lbl(f"http://{ip}:5000", "#00FF88", 14, True))
    lay.addWidget(lbl("(PC e Celular no mesmo Wi-Fi)", "#004466", 8))

    resultado = [None]

    def salvar():
        vals = {k: e.text().strip() for k, e in campos}
        if not all(vals.values()):
            QMessageBox.warning(dlg, "Erro", "Preencha todos os campos!")
            return
        salvar_config(vals)
        resultado[0] = vals
        dlg.accept()

    btn = QPushButton("▶  INICIAR VIRTUA")
    btn.setFont(QFont("Courier New", 14, QFont.Weight.Bold))
    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    btn.setStyleSheet("QPushButton{background:#003344;color:#00FFFF;border:none;"
                      "border-radius:24px;padding:14px;}"
                      "QPushButton:hover{background:#005577;}")
    btn.clicked.connect(salvar)
    lay.addSpacing(10)
    lay.addWidget(btn)
    dlg.exec()
    return resultado[0]

# ── ESTADOS ───────────────────────────────────────────────────────────────────
ESTADOS = {
    "waiting":    {"label": "AGUARDANDO  'VIRTUA'", "cor": QColor(0,180,220),  "hex": "#00B4DC", "intens": 0.55},
    "listening":  {"label": "OUVINDO...",            "cor": QColor(0,255,136),  "hex": "#00FF88", "intens": 0.80},
    "processing": {"label": "PROCESSANDO IA...",     "cor": QColor(255,215,0),  "hex": "#FFD700", "intens": 0.65},
    "speaking":   {"label": "VIRTUA FALANDO",        "cor": QColor(0,220,255),  "hex": "#00CCFF", "intens": 1.00},
}

# ── PARTÍCULA ─────────────────────────────────────────────────────────────────
class Part:
    def __init__(self):
        self._ang    = random.uniform(0, math.pi*2)
        self._dist_f = random.uniform(0.10, 1.0)
        self.fase    = random.uniform(0, math.pi*2)
        self.vel     = random.uniform(0.008, 0.028)
        self.r       = random.uniform(2.0, 4.5)
        self.vx = self.vy = 0.0
        self.x = self.y = self.x0 = self.y0 = 0.0
        # Velocidade própria de drift — cada neurônio tem personalidade
        self.drift_x = random.uniform(-0.4, 0.4)
        self.drift_y = random.uniform(-0.4, 0.4)

    def sync(self, cx, cy, raio):
        self.x0 = cx + math.cos(self._ang) * self._dist_f * raio
        self.y0 = cy + math.sin(self._ang) * self._dist_f * raio

    def update(self, tick, intens, explodindo):
        self.fase += self.vel
        if explodindo:
            self.x += self.vx * 6 * intens
            self.y += self.vy * 6 * intens
            self.vx += (self.x0 - self.x) * 0.030
            self.vy += (self.y0 - self.y) * 0.030
            self.vx *= 0.88; self.vy *= 0.88
        else:
            # Movimento orgânico com drift individual — parece vivo
            amp = 1.2 + intens * 2.5
            ox = math.sin(self.fase*1.3 + tick*0.011 + self.drift_x) * amp * 10
            oy = math.cos(self.fase*0.9 + tick*0.008 + self.drift_y) * amp * 8
            self.x = self.x0 + ox
            self.y = self.y0 + oy

# ── CANVAS PRINCIPAL ──────────────────────────────────────────────────────────
class VirtuaCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#020510;")
        self.tick        = 0
        self.estado      = "waiting"
        self.explodindo  = False
        self._expl_t     = 0
        self.speech_txt  = ""
        self.ia_elapsed  = None
        self.log_lines   = []
        self._xauusd     = "—"
        self._ram        = "—"
        self._cpu        = "—"
        self._cidade     = "—"
        self.parts        = [Part() for _ in range(90)]
        self._raio_extra  = 0.0
        self._expl_timer  = 0
        self._cor_atual   = [0.0, 180.0, 220.0]
        self._intens_atual = 0.55  # interpolado suavemente
        QTimer(self, timeout=self._tick, interval=33).start()

    def _tick(self):
        self.tick += 1

        # ── Explosão / expansão ──────────────────────────────────────────────
        if self._expl_timer > 0:
            self._expl_timer -= 1
            self.explodindo = True
        else:
            self.explodindo = False

        # Raio extra: expande rápido ao explodir, retrai lento depois
        if self.explodindo:
            target_extra = 80.0 if self.estado == "speaking" else 45.0
            self._raio_extra += (target_extra - self._raio_extra) * 0.18
        else:
            self._raio_extra += (0.0 - self._raio_extra) * 0.06  # retrai devagar

        # ── Interpolação de cor ──────────────────────────────────────────────
        cor_alvo = ESTADOS[self.estado]["cor"]
        tr, tg, tb = cor_alvo.red(), cor_alvo.green(), cor_alvo.blue()
        spd = 0.07  # velocidade de transição (0=instantâneo, 1=nunca muda)
        self._cor_atual[0] += (tr - self._cor_atual[0]) * spd
        self._cor_atual[1] += (tg - self._cor_atual[1]) * spd
        self._cor_atual[2] += (tb - self._cor_atual[2]) * spd

        # Intensidade interpolada
        self._intens_atual += (ESTADOS[self.estado]["intens"] - self._intens_atual) * spd

        W, H   = self.width(), self.height()
        cx, cy = W//2, int(H*0.46)
        raio   = int(min(W,H)*0.28) + int(self._raio_extra)
        intens = self._intens_atual
        for p in self.parts:
            p.sync(cx, cy, raio)
            p.update(self.tick, intens, self.explodindo)
        self.update()

    def explodir(self, forte=True):
        self._expl_timer = 90 if forte else 45  # ~3s ou ~1.5s de expansão
        f = 3.5 if forte else 1.8
        for p in self.parts:
            p.vx = random.uniform(-f, f)
            p.vy = random.uniform(-f, f)

    def _get_agenda(self):
        try:
            agenda_file = os.path.join(os.environ.get('APPDATA', ''), 'Virtua', 'agenda.json')
            if not os.path.exists(agenda_file): return "LIVRE"
            with open(agenda_file, encoding='utf-8') as f:
                agenda = json.load(f)
            hoje = datetime.datetime.now().strftime("%d/%m/%Y")
            comp = [c for c in agenda if c.get('data') == hoje]
            if not comp: return "LIVRE"
            prox = sorted(comp, key=lambda x: x.get('hora',''))[0]
            return f"{prox['hora']} {prox['descricao'][:12]}"
        except: return "LIVRE"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H   = self.width(), self.height()
        sc     = min(W,H) / 1080
        cx, cy = W//2, int(H*0.46)
        raio   = int(min(W,H)*0.28) + int(self._raio_extra)

        def S(v): return max(1, int(v*sc))
        def F(v): return max(7, int(v*sc))

        cor    = QColor(int(self._cor_atual[0]), int(self._cor_atual[1]), int(self._cor_atual[2]))
        intens = self._intens_atual
        t      = self.tick
        agora  = datetime.datetime.now()

        # Fundo
        painter.fillRect(0, 0, W, H, QColor(2,5,16))
        nebula = QRadialGradient(cx, cy, int(min(W,H)*0.44))
        nebula.setColorAt(0, QColor(0,22,50, int(18*intens+5)))
        nebula.setColorAt(1, QColor(0,0,0,0))
        painter.setBrush(QBrush(nebula)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, W, H)

        # Relógio
        painter.setFont(QFont("Courier New", F(38), QFont.Weight.Bold))
        painter.setPen(QColor(220,240,255,210))
        painter.drawText(QRect(0,S(10),W,S(60)),
            Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignVCenter,
            agora.strftime("%H:%M:%S"))
        painter.setFont(QFont("Courier New", F(10)))
        painter.setPen(QColor(25,70,110,170))
        painter.drawText(QRect(0,S(68),W,S(22)),
            Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignVCenter,
            agora.strftime("%A  %d/%m/%Y").upper())

        # HUD cantos
        pad = S(40); fL = QFont("Arial",F(8)); fV = QFont("Arial",F(14),QFont.Weight.Bold)
        h = agora.hour
        sess = "TÓQUIO" if h<5 else "LONDRES" if h<10 else "NOVA YORK" if h<17 else "FECHADO"

        def hud(items, x, y, direita=False):
            off=0; rw=S(180); rx=x-rw if direita else x
            af=Qt.AlignmentFlag.AlignRight if direita else Qt.AlignmentFlag.AlignLeft
            for lb,val,rgb in items:
                if lb:
                    painter.setFont(fL); painter.setPen(QColor(28,72,112,140))
                    painter.drawText(QRect(rx,y+off,rw,S(17)),af,lb); off+=S(17)
                if val:
                    painter.setFont(fV); painter.setPen(QColor(*rgb,210))
                    painter.drawText(QRect(rx,y+off,rw,S(24)),af,val); off+=S(27)

        hud([("SISTEMA","ONLINE",(0,255,136)),
             ("RAM",self._ram,(0,200,255)),
             ("CPU",self._cpu,(0,200,255))], pad, S(100))
        hud([("XAUUSD",self._xauusd,(255,179,0)),
             ("SESSÃO",sess,(0,200,255))], W-pad, S(100), True)

        # Glow central
        cg = QRadialGradient(cx,cy,int(raio*1.4))
        cg.setColorAt(0, QColor(cor.red(),cor.green(),cor.blue(),int(40*intens+8)))
        cg.setColorAt(0.5, QColor(cor.red()//2,cor.green()//2,cor.blue()//2,int(15*intens)))
        cg.setColorAt(1, QColor(0,0,0,0))
        painter.setBrush(QBrush(cg)); painter.setPen(Qt.PenStyle.NoPen)
        rg=int(raio*1.4); painter.drawEllipse(cx-rg,cy-rg,rg*2,rg*2)

        # Conexões — distância maior = mais neurônios conectados
        dist_max = raio*0.68; pts = self.parts
        for i in range(len(pts)):
            for j in range(i+1,len(pts)):
                dx=pts[i].x-pts[j].x; dy=pts[i].y-pts[j].y
                d=math.sqrt(dx*dx+dy*dy)
                if d<dist_max:
                    fator=1.0-d/dist_max
                    pulso=0.5+0.5*math.sin(t*0.06+pts[i].fase+pts[j].fase*0.5)
                    al=int(fator*fator*180*intens*pulso)
                    if al<4: continue
                    lw=max(0.5,fator*2.0*intens)
                    painter.setPen(QPen(QColor(cor.red(),cor.green(),cor.blue(),al),lw))
                    painter.drawLine(int(pts[i].x),int(pts[i].y),int(pts[j].x),int(pts[j].y))

        # Partículas — neurônios com glow pulsante
        for p in pts:
            pulso=0.5+0.5*math.sin(t*0.10+p.fase)
            al_p=int(200*pulso*intens+80)
            rp=p.r*(1.0+0.5*pulso*intens)
            # Glow externo duplo
            for gi,factor in [(4,0.12),(2.5,0.25)]:
                rg2=int(rp*gi)
                ag=int(al_p*factor)
                if ag>3:
                    pg=QRadialGradient(p.x,p.y,rg2)
                    pg.setColorAt(0,QColor(cor.red(),cor.green(),cor.blue(),ag))
                    pg.setColorAt(1,QColor(0,0,0,0))
                    painter.setBrush(QBrush(pg)); painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(int(p.x-rg2),int(p.y-rg2),rg2*2,rg2*2)
            # Núcleo brilhante
            ri=max(2,int(rp))
            nr=min(255,cor.red()+70); ng=min(255,cor.green()+70); nb=min(255,cor.blue()+70)
            painter.setBrush(QBrush(QColor(nr,ng,nb,al_p)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(p.x-ri),int(p.y-ri),ri*2,ri*2)

        # Nome VIRTUA
        vy = cy + S(8)
        for off,al in [(5,12),(3,28),(1,55),(0,215)]:
            c2 = QColor(cor.red(),cor.green(),cor.blue(),al) if off>0 else QColor(220,240,255,al)
            painter.setFont(QFont("Courier New",F(50),QFont.Weight.Bold))
            painter.setPen(c2)
            painter.drawText(QRect(off,vy-S(28)+off,W,S(65)),
                Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignVCenter,"VIRTUA")

        painter.setFont(QFont("Courier New",F(10)))
        painter.setPen(QColor(35,110,160,150))
        painter.drawText(QRect(0,vy+S(40),W,S(22)),
            Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignVCenter,
            "ASSISTENTE  DE  VOZ  COM  IA")

        # Barra de status
        est=ESTADOS[self.estado]; label=est["label"]
        if self.ia_elapsed and self.estado=="speaking":
            label+=f"  [{self.ia_elapsed}s]"
        pw2,ph2=S(320),S(38); sx=cx-pw2//2; sy=int(H*0.84)
        path=QPainterPath(); path.addRoundedRect(sx,sy,pw2,ph2,ph2//2,ph2//2)
        painter.fillPath(path,QBrush(QColor(cor.red()//6,cor.green()//6,cor.blue()//6,195)))
        pulso2=0.6+0.4*math.sin(t*0.11)
        painter.setPen(QPen(QColor(cor.red(),cor.green(),cor.blue(),int(175*pulso2)),1.5))
        painter.drawPath(path)
        dr=int(S(5)*pulso2)
        painter.setBrush(QBrush(cor)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(sx+S(18)-dr,sy+ph2//2-dr,dr*2,dr*2)
        painter.setFont(QFont("Arial",F(10),QFont.Weight.Bold))
        painter.setPen(QColor(200,230,255,215))
        painter.drawText(QRect(sx+S(34),sy,pw2-S(34),ph2),
            Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft,label)

        if self.speech_txt:
            txt=self.speech_txt[:80]+("..." if len(self.speech_txt)>80 else "")
            painter.setFont(QFont("Arial",F(8)))
            painter.setPen(QColor(35,90,150,165))
            painter.drawText(QRect(S(50),sy+ph2+S(6),W-S(100),S(28)),
                Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop,txt)

        # Log
        painter.setFont(QFont("Courier New",F(8)))
        log_y=int(H*0.62)
        for i,line in enumerate(self.log_lines[-5:]):
            al2=60 if i<4 else 115
            painter.setPen(QColor(25,110,165,al2))
            painter.drawText(QRect(S(16),log_y+i*S(17),S(240),S(17)),
                Qt.AlignmentFlag.AlignLeft,line[:32])

        # HUD inferior
        agenda = self._get_agenda()
        hud([("MEMÓRIA",f"{len(self.log_lines)} LOGS",(0,180,255)),
             ("AGENDA", agenda, (0,220,180))], pad, H-S(110))
        hud([("NGROK","ATIVO",(0,255,136)),
             ("CLAUDE AI","HAIKU 4.5",(136,136,255)),
             ("CIDADE", self._cidade, (180,180,255))], W-pad, H-S(110), True)
        
     

        painter.end()

# ── PAINEL LATERAL ────────────────────────────────────────────────────────────
class PainelWidget(QFrame):
    cmd_signal = pyqtSignal(str)
    cfg_signal = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config    = config
        self.nome      = config.get("nome","Usuário")
        self.mic_ativo = True
        self.setStyleSheet("QFrame{background:rgba(3,9,21,248);"
                           "border-left:1px solid rgba(0,85,125,85);}")
        self._build()

    def _build(self):
        lay=QVBoxLayout(self); lay.setContentsMargins(10,18,10,10); lay.setSpacing(5)

        def lbl(txt,cor="#FFF",size=12,bold=False):
            l=QLabel(txt)
            l.setFont(QFont("Courier New",size,QFont.Weight.Bold if bold else QFont.Weight.Normal))
            l.setStyleSheet(f"color:{cor};background:transparent;")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter); return l

        def sep():
            f=QFrame(); f.setFrameShape(QFrame.Shape.HLine)
            f.setStyleSheet("color:#081828;background:#081828;"); f.setFixedHeight(1); return f

        def btn2(txt,bg,fg,cmd):
            b=QPushButton(txt)
            b.setFont(QFont("Courier New",9,QFont.Weight.Bold))
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setStyleSheet(f"QPushButton{{background:{bg};color:{fg};"
                            f"border:none;border-radius:6px;padding:8px;}}"
                            f"QPushButton:hover{{background:{bg}BB;}}")
            b.clicked.connect(lambda:self.cmd_signal.emit(cmd)); return b

        lay.addWidget(lbl("[ VIRTUA ]","#FFFFFF",13,True))
        lay.addWidget(lbl("PAINEL DE CONTROLO","#1a3a5a",8))
        lay.addWidget(sep())
        lay.addWidget(lbl("● MICROFONE","#00AACC",9,True))

        self.btn_mic=QPushButton("🎤  MICROFONE ATIVO")
        self.btn_mic.setFont(QFont("Courier New",9,QFont.Weight.Bold))
        self.btn_mic.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._estilo_mic(True)
        self.btn_mic.clicked.connect(self._toggle_mic)
        lay.addWidget(self.btn_mic)

        lay.addWidget(sep())
        lay.addWidget(lbl("● ATALHOS RÁPIDOS","#00AACC",9,True))

        def row(t1,bg1,fg1,c1,t2,bg2,fg2,c2):
            f=QFrame(); f.setStyleSheet("background:transparent;")
            h=QHBoxLayout(f); h.setContentsMargins(0,0,0,0); h.setSpacing(4)
            h.addWidget(btn2(t1,bg1,fg1,c1)); h.addWidget(btn2(t2,bg2,fg2,c2)); return f

        lay.addWidget(row("💬 WhatsApp","#002a1a","#00FF88","whatsapp",
                          "🔍 Google","#001a33","#00AAFF","pesquisar no google"))
        lay.addWidget(row("▶ YouTube","#1a0000","#FF5555","youtube",
                          "💸 Gastos","#1a1100","#FFB300","gastos"))
        lay.addWidget(row("🕐 Horas","#001122","#00CCFF","que horas são",
                          "📅 Agenda","#001a22","#00DDAA","agenda de hoje"))

        lay.addWidget(sep())
        lay.addWidget(lbl("● CHAT CLAUDE AI","#00AACC",9,True))

        self.chat=QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setFont(QFont("Courier New",8))
        self.chat.setStyleSheet("QTextEdit{background:#010d1a;color:#88CCFF;"
                                "border:none;border-radius:4px;}")
        self.chat.setFixedHeight(155); lay.addWidget(self.chat)

        fi=QFrame(); fi.setStyleSheet("background:#010d1a;border-radius:4px;")
        hi=QHBoxLayout(fi); hi.setContentsMargins(6,2,6,2)
        self.inp=QLineEdit()
        self.inp.setPlaceholderText("Digite um comando...")
        self.inp.setFont(QFont("Courier New",9))
        self.inp.setStyleSheet("QLineEdit{background:transparent;color:#00CCFF;border:none;}")
        self.inp.returnPressed.connect(self._enviar)
        bs=QPushButton("►")
        bs.setFont(QFont("Courier New",10,QFont.Weight.Bold))
        bs.setStyleSheet("QPushButton{background:#002233;color:#00CCFF;border:none;"
                         "border-radius:4px;padding:4px 8px;}"
                         "QPushButton:hover{background:#003344;}")
        bs.clicked.connect(self._enviar)
        hi.addWidget(self.inp); hi.addWidget(bs); lay.addWidget(fi)

        lay.addWidget(sep())
        bcfg=QPushButton("⚙️  Configurações")
        bcfg.setFont(QFont("Courier New",9,QFont.Weight.Bold))
        bcfg.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        bcfg.setStyleSheet("QPushButton{background:#0a0a20;color:#8888FF;"
                           "border:none;border-radius:6px;padding:8px;}"
                           "QPushButton:hover{background:#111130;}")
        bcfg.clicked.connect(self.cfg_signal.emit)
        lay.addWidget(bcfg)
        lay.addWidget(lbl(f"📱  http://{get_ip_local()}:5000","#00FF88",8))
        lay.addStretch()
        self.adicionar_chat("Virtua",f"Olá {self.nome}! Como posso ajudar?")

    def _estilo_mic(self,ativo):
        if ativo:
            self.btn_mic.setText("🎤  MICROFONE ATIVO")
            self.btn_mic.setStyleSheet("QPushButton{background:#003322;color:#00FF88;"
                                       "border:none;border-radius:6px;padding:9px;}")
        else:
            self.btn_mic.setText("🔇  MICROFONE MUDO")
            self.btn_mic.setStyleSheet("QPushButton{background:#1a0000;color:#FF4444;"
                                       "border:none;border-radius:6px;padding:9px;}")

    def _toggle_mic(self):
        self.mic_ativo=not self.mic_ativo
        self._estilo_mic(self.mic_ativo)

    def _enviar(self):
        txt=self.inp.text().strip()
        if not txt: return
        self.inp.clear()
        self.adicionar_chat(self.nome,txt)
        self.cmd_signal.emit(txt)

    def adicionar_chat(self,autor,texto):
        now=datetime.datetime.now().strftime("%H:%M")
        if autor==self.nome:   cor,linha="#88CCFF",f"[{now}] {self.nome}: {texto}"
        elif autor=="Virtua":  cor,linha="#00FF88",f"[{now}] Virtua: {texto}"
        else:                  cor,linha="#FF8888",f"[!] {texto}"
        self.chat.setTextColor(QColor(cor)); self.chat.append(linha)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

# ── JANELA PRINCIPAL ──────────────────────────────────────────────────────────
class VirtuaWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config=config
        self.setWindowTitle("VIRTUA")
        self._fullscreen=True
        self._painel_aberto=False
        self._anim=None
        self._pw=310

        self.canvas=VirtuaCanvas(self)
        self.canvas._cidade = config.get("cidade", "—").upper()
        self.setCentralWidget(self.canvas)

        # Label flutuante de speech — sempre visível sobre o canvas
        self.speech_label = QLabel("", self)
        self.speech_label.setWordWrap(True)
        self.speech_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speech_label.setFont(QFont("Arial", 11))
        self.speech_label.setStyleSheet(
            "QLabel{color:#AADDFF;background:rgba(0,10,30,160);"
            "border-radius:8px;padding:8px 14px;}")
        self.speech_label.hide()

        self.painel=PainelWidget(config,self)
        self.painel.setGeometry(9999,0,self._pw,self.height())
        self.painel.cmd_signal.connect(self._on_cmd)
        self.painel.cfg_signal.connect(self.abrir_configuracoes)

        self.btn_menu=QPushButton("≡",self)
        self.btn_menu.setFont(QFont("Arial",18,QFont.Weight.Bold))
        self.btn_menu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_menu.setStyleSheet("QPushButton{background:rgba(5,8,32,175);color:#3388CC;"
                                    "border:none;padding:10px 14px;border-radius:6px;}"
                                    "QPushButton:hover{background:rgba(10,16,48,205);}")
        self.btn_menu.clicked.connect(self._toggle_painel)

        self._btns=[]
        # Ordem visual da esquerda p/ direita: ─  ⛶  ✕
        # Mas posicionamos da direita p/ esquerda: i=0 é o ✕ (mais à direita)
        for txt,cor,cmd in [("✕","#FF5555",self.close),
                             ("□","#CCDDFF",self._toggle_fs),
                             ("─","#CCDDFF",self.showMinimized)]:
            b=QPushButton(txt,self)
            b.setFont(QFont("Arial",13,QFont.Weight.Bold))
            b.setFixedSize(36,28)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setStyleSheet(f"QPushButton{{background:rgba(10,10,30,200);color:{cor};"
                            f"border:none;}}"
                            f"QPushButton:hover{{background:rgba(40,40,80,220);}}")
            b.clicked.connect(cmd); self._btns.append(b)

        self._iniciar_sys_loop()
        self._iniciar_mt5_loop()
        self.showFullScreen()
        self._posicionar_botoes()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        W,H=self.width(),self.height()
        if self._painel_aberto: self.painel.setGeometry(W-self._pw,0,self._pw,H)
        else: self.painel.setGeometry(W,0,self._pw,H)
        self._posicionar_botoes()
        sw=min(W-80,600); sh=60
        self.speech_label.setGeometry((W-sw)//2, int(H*0.74), sw, sh)

    def _posicionar_botoes(self):
        W,H=self.width(),self.height()
        self.btn_menu.move(W-52, H//2-25)
        # Botões topo direita: ✕ mais à direita, depois □, depois ─
        for i,b in enumerate(self._btns):
            b.move(W - 36 - i*36, 0)

    def _toggle_fs(self):
        if self.isFullScreen():
            self._fullscreen = False
            self.showNormal()
            QTimer.singleShot(100, lambda: self.resize(1280, 720))
        else:
            self._fullscreen = True
            self.showFullScreen()

    def _toggle_painel(self):
        self._painel_aberto=not self._painel_aberto
        W,H=self.width(),self.height(); pw=self._pw
        if self._anim: self._anim.stop()
        self._anim=QPropertyAnimation(self.painel,b"geometry")
        self._anim.setDuration(260); self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if self._painel_aberto:
            self._anim.setStartValue(QRect(W,0,pw,H)); self._anim.setEndValue(QRect(W-pw,0,pw,H))
        else:
            self._anim.setStartValue(QRect(W-pw,0,pw,H)); self._anim.setEndValue(QRect(W,0,pw,H))
        self._anim.start()

    def _on_cmd(self,cmd):
        try:
            import servidor as srv
            srv.fila_comandos.append([str(time.time()),cmd])
        except: pass
        self.add_log(f"► {cmd[:22]}")

    def _iniciar_sys_loop(self):
        def loop():
            while True:
                try:
                    import psutil
                    self.canvas._ram=f"{psutil.virtual_memory().percent:.0f}%"
                    self.canvas._cpu=f"{psutil.cpu_percent(interval=1):.0f}%"
                except: time.sleep(1)
                time.sleep(4)
        threading.Thread(target=loop,daemon=True).start()

    def _iniciar_mt5_loop(self):
        def loop():
            while True:
                try:
                    import MetaTrader5 as mt5
                    if mt5.initialize():
                        tick=mt5.symbol_info_tick("XAUUSD")
                        if tick and tick.bid>0: self.canvas._xauusd=f"{tick.bid:.2f}"
                        mt5.shutdown()
                except: pass
                time.sleep(10)
        threading.Thread(target=loop,daemon=True).start()

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_F11: self._toggle_fs()
        elif event.key()==Qt.Key.Key_Escape and self.isFullScreen(): self._toggle_fs()

    # ── Configurações ─────────────────────────────────────────────────────────
    def abrir_configuracoes(self):
        if hasattr(self,'_cfg_win') and self._cfg_win and self._cfg_win.isVisible():
            self._cfg_win.raise_(); return

        win=QDialog(self); win.setWindowTitle("VIRTUA — Configurações")
        screen = QApplication.primaryScreen().availableGeometry()
        h = min(820, screen.height() - 60)
        win.setFixedSize(520, h)
        self._cfg_win=win

        scroll=QScrollArea(win); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{background:#000010;border:none;}")
        scroll.setGeometry(0, 0, 520, h)
        inner=QWidget(); scroll.setWidget(inner)
        lay=QVBoxLayout(inner); lay.setContentsMargins(20,20,20,20); lay.setSpacing(4)

        cyan="#00FFFF"; dark="#000D1A"; green="#00FF88"

        def lbl2(txt,cor="#00AACC",size=9,bold=False):
            l=QLabel(txt)
            l.setFont(QFont("Courier New",size,QFont.Weight.Bold if bold else QFont.Weight.Normal))
            l.setStyleSheet(f"color:{cor};background:transparent;"); return l

        def entry2(val="",hide=False):
            e=QLineEdit(); e.setText(val)
            if hide: e.setEchoMode(QLineEdit.EchoMode.Password)
            e.setFont(QFont("Courier New",10))
            e.setStyleSheet(f"QLineEdit{{background:{dark};color:{cyan};"
                            f"border:1px solid #001a2a;border-radius:4px;padding:5px;}}"); return e

        def sep2():
            f=QFrame(); f.setFrameShape(QFrame.Shape.HLine)
            f.setStyleSheet("color:#001a2a;background:#001a2a;"); f.setFixedHeight(1); return f

        lay.addWidget(lbl2("[ CONFIGURAÇÕES ]","#FFFFFF",16,True))
        lay.addWidget(lbl2("VIRTUA ASSISTANT","#003344",9))
        lay.addSpacing(8)

        cfg=carregar_config()

        lay.addWidget(lbl2("● IDENTIDADE",cyan,10,True)); lay.addWidget(sep2())
        lay.addWidget(lbl2("Seu nome:")); e_nome=entry2(cfg.get("nome","")); lay.addWidget(e_nome)
        lay.addWidget(lbl2("Sua cidade:")); e_cidade=entry2(cfg.get("cidade","")); lay.addWidget(e_cidade)
        lay.addWidget(lbl2("Claude API Key:")); e_claude=entry2(cfg.get("claude_key",""),True); lay.addWidget(e_claude)
        lay.addWidget(lbl2("Groq API Key:")); e_groq=entry2(cfg.get("Groq_Cloud",""),True); lay.addWidget(e_groq)

        lay.addSpacing(8); lay.addWidget(lbl2("● NGROK",cyan,10,True)); lay.addWidget(sep2())
        lay.addWidget(lbl2("Ngrok Token:")); e_ngrok=entry2(cfg.get("ngrok_token",""),True); lay.addWidget(e_ngrok)

        lay.addSpacing(8); lay.addWidget(lbl2("● MICROFONE",cyan,10,True)); lay.addWidget(sep2())
        lay.addWidget(lbl2("Sensibilidade (energy threshold — padrão: 100):"))
        e_mic=entry2(str(cfg.get("mic_threshold",100))); lay.addWidget(e_mic)

        lay.addSpacing(8); lay.addWidget(lbl2("● ALERTAS DE OURO (MT5)",cyan,10,True)); lay.addWidget(sep2())
        lay.addWidget(lbl2("Variação mínima em dólares para alertar (padrão: 10):"))
        e_ouro=entry2(str(cfg.get("ouro_alerta",10))); lay.addWidget(e_ouro)

        lay.addSpacing(8); lay.addWidget(lbl2("● BRIEFING DIÁRIO",cyan,10,True)); lay.addWidget(sep2())
        cidade = cfg.get("cidade", "sua cidade")
        opcoes=[("Agenda do dia","briefing_agenda"),(f"Clima de {cidade}","briefing_clima"),
                ("Preço do ouro","briefing_ouro"),("Trading de ontem","briefing_trading"),
                ("Frase motivacional","briefing_motivacao")]
        chks={}
        for label,key in opcoes:
            cb=QCheckBox(label); cb.setChecked(cfg.get(key,True))
            cb.setStyleSheet(f"QCheckBox{{color:#00AACC;background:transparent;font-family:Courier New;font-size:9pt;}}"
                             f"QCheckBox::indicator{{background:#001a2a;border:1px solid #003344;}}")
            lay.addWidget(cb); chks[key]=cb

        lay.addSpacing(8); lay.addWidget(lbl2("● BACKUP",cyan,10,True)); lay.addWidget(sep2())
        lay.addWidget(lbl2("Pasta de backup:"))
        e_backup=entry2(cfg.get("backup_pasta","")); lay.addWidget(e_backup)

        
        # ── Automação Residencial ──
        lay.addSpacing(8); lay.addWidget(lbl2("● AUTOMAÇÃO RESIDENCIAL",cyan,10,True)); lay.addWidget(sep2())
        lay.addWidget(lbl2("Dispositivos cadastrados:"))

        lista_disp = QListWidget()
        lista_disp.setStyleSheet(f"background:#000820;color:{cyan};font-family:Courier New;font-size:9pt;border:1px solid {cyan};")
        lista_disp.setMaximumHeight(120)

        def atualizar_lista_disp():
            lista_disp.clear()
            for d in automacao.carregar_dispositivos():
                status = "✓" if d.get("incluir_no_tudo", True) else "✗"
                lista_disp.addItem(f"{status} {d['nome']} ({d['tipo']} / {d['marca']})")

        atualizar_lista_disp()
        lay.addWidget(lista_disp)

        lay.addSpacing(4)
        lay.addWidget(lbl2("Nome (ex: luz do quarto):"))
        e_disp_nome = entry2(""); lay.addWidget(e_disp_nome)

        lay.addWidget(lbl2("Tipo (lampada/tomada/ar/ir/samsung):"))
        e_disp_tipo = entry2(""); lay.addWidget(e_disp_tipo)

        lay.addWidget(lbl2("Marca (tuya/samsung):"))
        e_disp_marca = entry2(""); lay.addWidget(e_disp_marca)

        lay.addWidget(lbl2("Device ID:"))
        e_disp_id = entry2(""); lay.addWidget(e_disp_id)

        lay.addWidget(lbl2("IP local:"))
        e_disp_ip = entry2(""); lay.addWidget(e_disp_ip)

        lay.addWidget(lbl2("Local Key (Tuya):"))
        e_disp_key = entry2("", True); lay.addWidget(e_disp_key)

        chk_tudo = QCheckBox("Incluir no 'liga tudo' / 'desliga tudo'")
        chk_tudo.setChecked(True)
        chk_tudo.setStyleSheet(f"color:{cyan};font-family:Courier New;font-size:9pt;background:transparent;")
        lay.addWidget(chk_tudo)

        def adicionar_disp():
            nome = e_disp_nome.text().strip()
            tipo = e_disp_tipo.text().strip()
            marca = e_disp_marca.text().strip()
            did = e_disp_id.text().strip()
            ip = e_disp_ip.text().strip()
            key = e_disp_key.text().strip()
            if not nome or not tipo or not marca or not did:
                msg_lbl.setText("Preencha nome, tipo, marca e Device ID!")
                return
            automacao.adicionar_dispositivo(nome, tipo, marca, did, ip, key, {}, chk_tudo.isChecked())
            atualizar_lista_disp()
            e_disp_nome.clear(); e_disp_tipo.clear(); e_disp_marca.clear()
            e_disp_id.clear(); e_disp_ip.clear(); e_disp_key.clear()

        def remover_disp():
            item_sel = lista_disp.currentItem()
            if item_sel:
                nome = item_sel.text().split(" ")[1]
                automacao.remover_dispositivo(nome)
                atualizar_lista_disp()

        btn_add = QPushButton("＋  ADICIONAR DISPOSITIVO")
        btn_add.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        btn_add.setStyleSheet(f"background:#003322;color:{green};border:1px solid {green};padding:6px;")
        btn_add.clicked.connect(adicionar_disp)
        lay.addWidget(btn_add)

        btn_rem = QPushButton("－  REMOVER SELECIONADO")
        btn_rem.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        btn_rem.setStyleSheet(f"background:#330000;color:#FF4444;border:1px solid #FF4444;padding:6px;")
        btn_rem.clicked.connect(remover_disp)
        lay.addWidget(btn_rem)

        msg_lbl=QLabel(""); msg_lbl.setStyleSheet(f"color:{green};background:transparent;font-family:Courier New;font-size:9pt;")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def salvar_cfg():
            try:
                novo={
                    "nome":e_nome.text().strip(),
                    "cidade":e_cidade.text().strip(),
                    "claude_key":e_claude.text().strip(),
                    "Groq_Cloud":e_groq.text().strip(),
                    "ngrok_token":e_ngrok.text().strip(),
                    "mic_threshold":int(e_mic.text().strip() or 100),
                    "ouro_alerta":float(e_ouro.text().strip() or 10),
                    "backup_pasta":e_backup.text().strip(),
                }
                for key,cb in chks.items(): novo[key]=cb.isChecked()
                salvar_config(novo)
                msg_lbl.setText("✓ Configurações salvas! Reinicia a Virtua para aplicar.")
                QTimer.singleShot(3000,win.close)
            except Exception as e:
                msg_lbl.setText(f"Erro: {e}")

        btn_s=QPushButton("▶  SALVAR CONFIGURAÇÕES")
        btn_s.setFont(QFont("Courier New",12,QFont.Weight.Bold))
        btn_s.setStyleSheet(f"QPushButton{{background:#003344;color:{cyan};border:none;"
                            f"border-radius:8px;padding:10px 20px;}}"
                            f"QPushButton:hover{{background:#005577;}}")
        btn_s.clicked.connect(salvar_cfg)
        lay.addSpacing(10); lay.addWidget(btn_s); lay.addWidget(msg_lbl)
        win.show()

    # ── API pública ───────────────────────────────────────────────────────────
    def add_log(self,text):
        now=datetime.datetime.now().strftime("%H:%M")
        self.canvas.log_lines.append(f"{now} {text[:28]}")
        if len(self.canvas.log_lines)>20: self.canvas.log_lines.pop(0)

    def set_speaking(self,text="",ia_elapsed=None):
        ant=self.canvas.estado
        self.canvas.estado="speaking"
        self.canvas.speech_txt=text if text else ""
        self.canvas.ia_elapsed=ia_elapsed
        if ant!="speaking": self.canvas.explodir(forte=True)
        if text:
            self.speech_label.setText(f'🔊  {text}')
            self.speech_label.show()
            self.speech_label.raise_()
        self.add_log(f"▸ {text[:26]}")

    def set_listening(self):
        ant=self.canvas.estado
        self.canvas.estado="listening"
        self.canvas.speech_txt=""
        self.canvas.ia_elapsed=None
        self.speech_label.setText("🎤  Ouvindo...")
        self.speech_label.show(); self.speech_label.raise_()
        if ant!="listening": self.canvas.explodir(forte=False)
        self.add_log("Ouvindo...")

    def set_waiting(self):
        self.canvas.estado="waiting"
        self.canvas.speech_txt=""
        self.canvas.ia_elapsed=None
        self.speech_label.hide()

    def set_processing(self):
        self.canvas.estado="processing"
        self.canvas.speech_txt=""
        self.speech_label.setText("⚙️  Processando IA...")
        self.speech_label.show(); self.speech_label.raise_()
        self.add_log("Consultando IA...")

    def set_recognized(self,text):
        self.canvas.speech_txt=text
        self.speech_label.setText(f'💬  {text}')
        self.speech_label.show(); self.speech_label.raise_()
        self.add_log(f"≫ {text[:26]}")

    def adicionar_chat(self,autor,texto):
        self.painel.adicionar_chat(autor,texto)

    @property
    def mic_ativo(self): return self.painel.mic_ativo
    @mic_ativo.setter
    def mic_ativo(self,v): self.painel.mic_ativo=v

# ── BRIDGE THREAD-SAFE ────────────────────────────────────────────────────────
class _Bridge(QObject):
    """
    Signals emitidos de qualquer thread, executados sempre na main thread do Qt.
    Esta é a única forma correta de comunicar threads com a UI no PyQt6.
    """
    sig_speaking    = pyqtSignal(str, object)
    sig_listening   = pyqtSignal()
    sig_waiting     = pyqtSignal()
    sig_processing  = pyqtSignal()
    sig_recognized  = pyqtSignal(str)
    sig_chat        = pyqtSignal(str, str)
    sig_log         = pyqtSignal(str)
    sig_destroy     = pyqtSignal()
    sig_iconify     = pyqtSignal()
    sig_configs     = pyqtSignal()
    sig_after       = pyqtSignal(int)   # ms — a func é guardada numa fila

    def __init__(self):
        super().__init__()
        self._after_queue = []
        self.sig_after.connect(self._run_after)

    @pyqtSlot(int)
    def _run_after(self, ms):
        if self._after_queue:
            func = self._after_queue.pop(0)
            QTimer.singleShot(ms, func)

    def schedule(self, ms, func):
        self._after_queue.append(func)
        self.sig_after.emit(ms)

# ── CLASSE VirtuaInterface (API COMPATÍVEL COM virtua_main.py) ────────────────
class VirtuaInterface:
    """
    Wrapper compatível 100% com virtua_main.py.
    Usa _Bridge com signals Qt para comunicação thread-safe.
    """
    def __init__(self, config):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._win = VirtuaWindow(config)
        self._bridge = _Bridge()

        # Conectar signals → slots na main thread
        self._bridge.sig_speaking.connect(self._win.set_speaking)
        self._bridge.sig_listening.connect(self._win.set_listening)
        self._bridge.sig_waiting.connect(self._win.set_waiting)
        self._bridge.sig_processing.connect(self._win.set_processing)
        self._bridge.sig_recognized.connect(self._win.set_recognized)
        self._bridge.sig_chat.connect(self._win.adicionar_chat)
        self._bridge.sig_log.connect(self._win.add_log)
        self._bridge.sig_destroy.connect(lambda: (self._win.close(), self._app.quit()))
        self._bridge.sig_iconify.connect(self._win.showMinimized)
        self._bridge.sig_configs.connect(self._win.abrir_configuracoes)

        self.root = _RootCompat(self._bridge)
        self.chat_area = True

    # ── API pública — pode ser chamada de qualquer thread ────────────────────
    def set_speaking(self, text="", ia_elapsed=None):
        self._bridge.sig_speaking.emit(text, ia_elapsed)

    def set_listening(self):
        self._bridge.sig_listening.emit()

    def set_waiting(self):
        self._bridge.sig_waiting.emit()

    def set_processing(self):
        self._bridge.sig_processing.emit()

    def set_recognized(self, text):
        self._bridge.sig_recognized.emit(text)

    def adicionar_chat(self, autor, texto):
        self._bridge.sig_chat.emit(autor, texto)

    def add_log(self, text):
        self._bridge.sig_log.emit(text)

    def abrir_configuracoes(self):
        self._bridge.sig_configs.emit()

    @property
    def mic_ativo(self): return self._win.mic_ativo
    @mic_ativo.setter
    def mic_ativo(self, v): self._win.mic_ativo = v

    def run(self):
        self._app.exec()

# ── ROOT COMPAT ───────────────────────────────────────────────────────────────
class _RootCompat:
    """
    Emula ui.root do tkinter. Usa bridge para thread-safety.
    """
    def __init__(self, bridge):
        self._bridge = bridge

    def after(self, ms, func):
        self._bridge.schedule(ms, func)

    def destroy(self):
        self._bridge.sig_destroy.emit()

    def iconify(self):
        self._bridge.sig_iconify.emit()

# ── STANDALONE TEST ───────────────────────────────────────────────────────────
if __name__=="__main__":
    app=QApplication(sys.argv)
    cfg=carregar_config()
    if not cfg.get("nome"): cfg={"nome":"Dioni","claude_key":"test","Groq_Cloud":"test","ngrok_token":"test","cidade":""}
    ui=VirtuaInterface(cfg)

    estados=["waiting","listening","processing","speaking"]
    i=[0]
    def ciclo():
        e=estados[i[0]%4]
        if e=="speaking":    ui.set_speaking("Testando nova interface PyQt6!",1.2)
        elif e=="listening": ui.set_listening()
        elif e=="processing":ui.set_processing()
        else:                ui.set_waiting()
        i[0]+=1
        QTimer.singleShot(3000,ciclo)
    ciclo()
    ui.run()