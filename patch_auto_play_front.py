# -*- coding: utf-8 -*-
import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('cartaCuringaIndex: null\n      },', 'cartaCuringaIndex: null,\n          autoPlay: false\n      },')
text = text.replace('cartaCuringaIndex: null\n        },', 'cartaCuringaIndex: null,\n          autoPlay: false\n        },')

ui_html = '''        <div v-if="estado === \'JOGO\'" class="auto-play-toggle" style="position: absolute; bottom: 20px; right: 20px; background: rgba(0,0,0,0.6); padding: 5px 10px; border-radius: 20px; z-index: 1000; border: 1px solid #4a5568;">
            <label style="color: #63b3ed; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" v-model="autoPlay" style="width: 18px; height: 18px; cursor: pointer;" />
                BOT AUTO
            </label>
        </div>'''

text = text.replace('</div>\n    <div class="log-container" ref="logContainer">', ui_html + '\n    </div>\n    <div class="log-container" ref="logContainer">')

watcher_logic = '''        turnoAtual(newVal) {
            if (this.timerInterval) clearInterval(this.timerInterval);
            if (newVal === this.usuarioId) {
                this.tempoRestante = 14;
                this.timerInterval = setInterval(() => {
                    if (this.tempoRestante > 0) this.tempoRestante--;
                }, 1000);
                if (this.autoPlay && !this.esperandoResposta) {
                    setTimeout(() => { this.tentarJogadaAutomatica(); }, 800);
                }
            }
        },
        autoPlay(newVal) {
            if(newVal && this.turnoAtual === this.usuarioId && !this.esperandoResposta) {
                this.tentarJogadaAutomatica();
            }
        }'''

if 'autoPlay(newVal)' not in text:
    text = re.sub(r'turnoAtual\(newVal\) \{.*?\}\s*\}', watcher_logic, text, flags=re.DOTALL)

methods_logic = '''    methods: {
        tentarJogadaAutomatica() {
            if(this.turnoAtual !== this.usuarioId || this.esperandoResposta) return;
            this.esperandoResposta = true;
            this.addLog("🤖 Jogando no automatico...");
            this.socket.emit("forcarAutoPlay", { partidaId: this.partidaId });
        },'''

if 'tentarJogadaAutomatica' not in text:
    text = text.replace('methods: {', methods_logic)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
