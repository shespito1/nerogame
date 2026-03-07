import os

content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Nero Game - Uno Betting</title>
    <script src="https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.js"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;700;800&family=Rowdies:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Baloo 2', display, sans-serif; 
            background: radial-gradient(circle at center, #1b533a 0%, #0d2e1c 100%); 
            color: white; margin: 0; padding: 0; min-height: 100vh;
        }
        .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
        
        h1 { 
            text-align: center; color: #f1c40f; font-family: 'Rowdies', cursive; 
            text-shadow: 2px 2px 0 #000; margin-bottom: 20px; font-size: 32px;
            border-bottom: 2px solid rgba(255,255,255,0.1); padding-bottom: 15px;
        }
        
        .stats { 
            display: flex; justify-content: space-around; font-size: 20px; font-weight: bold; 
            color: #63b3ed; margin-bottom: 20px; text-transform: uppercase;
            background: rgba(0,0,0,0.35); padding: 15px 25px; border-radius: 12px; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.05);
        }
        
        .log { 
            background: rgba(0,0,0,0.5); padding: 15px; height: 120px; overflow-y: scroll; 
            border-radius: 8px; font-family: 'Consolas', monospace; font-size: 13px; color: #4ade80; 
            border: 1px solid rgba(255,255,255,0.05); text-align: left;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
        }
        
        .card-menu { 
            background: rgba(20, 30, 25, 0.6); padding: 30px; border-radius: 16px; 
            text-align: center; margin-bottom: 20px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.05);
            backdrop-filter: blur(8px);
        }
        
        button { 
            background: linear-gradient(135deg, #f6d365 0%, #ffb347 100%); color: #744210; border: none; padding: 15px 35px; font-size: 20px; border-radius: 50px; 
            cursor: pointer; font-weight: 800; font-family: 'Baloo 2', cursive; transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); 
            box-shadow: 0 4px 15px rgba(0,0,0,0.2); text-transform: uppercase; margin-top: 15px;
        }
        button:hover { transform: scale(1.05) translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.3); }
        button:disabled { filter: grayscale(1); cursor: auto !important; }
        
        .mesa-container { display: flex; justify-content: space-around; align-items: stretch; margin: 20px 0; gap: 20px; width: 100%; }
        
        .oponentes { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; align-items: center; flex: 1; max-width: 45%; }
        .oponente { 
            display: inline-flex; flex-direction: column; align-items: center; justify-content: center;
            width: 100px; padding: 10px; background: rgba(0,0,0,0.5); margin: 5px; border-radius: 12px; font-size: 14px; border: 2px solid transparent; transition: 0.3s; position: relative;
        }
        .oponente span { color: white !important; }
        .oponente-nome { font-weight: bold; margin-bottom: 5px; color: #e2e8f0; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; width: 100%;}
        .oponente-cartas { background: #4a5568; color: white; padding: 4px 10px; border-radius: 20px; font-size: 16px; font-weight: bold; border: 1px solid rgba(255,255,255,0.2); margin-top: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); }
        .oponente-ativo { border: 2px solid #fbd38d !important; box-shadow: 0 0 20px rgba(251, 211, 141, 0.4); background: rgba(251, 211, 141, 0.15) !important; transform: translateY(-5px); }
        
        .mesa { background: rgba(0,0,0,0.3); padding: 25px; border-radius: 16px; text-align: center; flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; border: 1px solid rgba(255,255,255,0.05); }
        
        .mao-container { margin-top: 20px; text-align: center; padding: 25px; border-radius: 16px; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); }
        .meu-turno { border: 2px dashed #48bb78; background: rgba(72, 187, 120, 0.15); box-shadow: 0 0 20px rgba(72,187,120,0.2); }
        .mao { display: flex; gap: 5px; justify-content: center; flex-wrap: wrap; margin-top: 15px; }
        
        /* 🎨 MELHORIAS DOS GRÁFICOS DAS CARTAS */
        .carta { 
            position: relative; display: inline-flex; justify-content: center; align-items: center; 
            width: 80px; height: 120px; border-radius: 10px; margin: 4px; font-size: 40px; font-weight: 700; font-family: 'Rowdies', cursive;
            color: white; cursor: pointer; user-select: none; border: 5px solid white; text-align: center; 
            text-shadow: 3px 3px 0px rgba(0,0,0,0.6); box-shadow: 3px 6px 15px rgba(0,0,0,0.5), inset 0 0 0 4px rgba(0,0,0,0.15); 
            transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); background-color: #333; overflow: hidden; line-height: normal; z-index: 10;
        }
        
        /* Centro Oval do UNO */
        .carta::before {
            content: ""; position: absolute; top: -15%; left: -15%; right: -15%; bottom: -15%; background: rgba(255,255,255,0.2); border-radius: 50%;
            transform: rotate(-30deg) scale(0.85); z-index: 0; pointer-events: none;
            border: 2px solid rgba(255,255,255,0.5);
        }
        
        /* Small Mini-Values in the corners */
        .carta::after {
            content: attr(data-valor); position: absolute; top: 3px; left: 6px; font-size: 16px; text-shadow: 1px 1px 0px rgba(0,0,0,0.5);
            font-family: 'Rowdies', cursive; z-index: 2; pointer-events: none; line-height: 1;
        }
        .carta .bottom-corner {
            content: attr(data-valor); position: absolute; bottom: 3px; right: 6px; font-size: 16px; text-shadow: 1px 1px 0px rgba(0,0,0,0.5);
            font-family: 'Rowdies', cursive; z-index: 2; pointer-events: none; line-height: 1; transform: rotate(180deg);
        }

        .carta span { position: relative; z-index: 1; pointer-events: none; }
        
        .carta:hover { transform: translateY(-25px) scale(1.15) rotate(-3deg); z-index: 30; box-shadow: 8px 18px 30px rgba(0,0,0,0.7); }
        .carta-mesa { transform: scale(1.6) rotate(5deg); pointer-events: none; box-shadow: 0 12px 35px rgba(0,0,0,0.7); margin: 25px auto; }
        .carta-mesa:hover { transform: scale(1.6) rotate(5deg); }
        
        /* CORES REALISTAS */
        .Vermelho { background: linear-gradient(135deg, #ff5555 0%, #cc0000 100%); }
        .Azul { background: linear-gradient(135deg, #5555ff 0%, #0000cc 100%); }
        .Verde { background: linear-gradient(135deg, #55ff55 0%, #00aa00 100%); }
        .Amarelo { background: linear-gradient(135deg, #ffff55 0%, #d4aa00 100%); color: white; }
        .Amarelo span, .Amarelo::after, .Amarelo .bottom-corner { text-shadow: 2px 2px 0px rgba(0,0,0,0.4); }
        .Curinga { background: conic-gradient(from 45deg, #ff5555 0% 25%, #5555ff 25% 50%, #55ff55 50% 75%, #ffff55 75% 100%); }
        .Curinga::before { background: rgba(0,0,0,0.6); border: 2px solid rgba(255,255,255,0.2); }
        
        @keyframes drawCard { 0% { opacity: 0; transform: translateY(80px) scale(0.5) rotate(15deg); } 100% { opacity: 1; transform: translateY(0) scale(1) rotate(0deg); } }
        .carta-animada { animation: drawCard 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; }
        
        .loader { border: 8px solid rgba(255,255,255,0.1); border-top: 8px solid #48bb78; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        /* Modal Curinga - ESCOLHER COR */
        .modal-cor { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); display: flex; justify-content: center; align-items: center; z-index: 1000; backdrop-filter: blur(5px); }
        .modal-cor-content { background: #2d3748; padding: 40px; border-radius: 16px; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.5); border: 2px solid rgba(255,255,255,0.1); }
        .modal-cor-content h3 { color: white; margin-top: 0; margin-bottom: 25px; font-size: 28px; }
        .cor-btn { width: 80px; height: 80px; border-radius: 50%; border: 5px solid rgba(255,255,255,0.8); cursor: pointer; transition: 0.2s; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        .cor-btn:hover { transform: scale(1.2); border-color: white; box-shadow: 0 10px 25px rgba(0,0,0,0.6); }
    </style>
</head>
<body>
<div id="app" class="container">
    <h1>🃏 Nero Uno - Apostas (R$ 1,00)</h1>
    <div class="stats"><div>👤 Olá, {{ usuarioId }}</div><div>💰 Saldo: R$ {{ saldo.toFixed(2) }}</div></div>
    
    <div class="card-menu" v-if="estado === 'MENU'">
        <h2>Pronto para jogar?</h2>
        <p style="color: #a0aec0; font-size: 18px;">Custo de entrada: R$ 1,00. O vencedor leva R$ 3,80!</p>
        <button @click="pagarEEntrarNaFila">🎮 JOGAR R$ 1,00</button>
    </div>

    <div class="card-menu" v-if="estado === 'FILA'">
        <h2>⏳ Aguardando jogadores...</h2>
        <p style="color: #63b3ed; font-size: 18px;">A partida iniciará automaticamente assim que 4 jogadores entrarem.</p>
        <div class="loader"></div>
    </div>

    <div class="card-menu" v-if="estado === 'JOGO'" style="background: transparent; box-shadow: none; border: none; padding: 0;">
        <div class="mesa-container">
            <div class="oponentes">
                <div v-for="op in getOponentes()" :key="op.id" class="oponente" :class="{ 'oponente-ativo': op.id === turnoAtual }">
                    <span class="oponente-nome">🤖 {{ op.id }}</span>
                    <span class="oponente-cartas">🃏 {{ op.cartas }}</span>
                    <span v-if="op.id === turnoAtual" style="position:absolute; right: -20px; top: -10px; font-size: 24px; animation: drawCard 0.5s infinite alternate;">👈</span>
                </div>
            </div>
            <div class="mesa">
                <p style="color: #a0aec0; margin-top: 0; font-weight: bold; font-size: 16px; text-transform: uppercase;">A Mesa</p>
                <div v-if="cartaMesa" class="carta carta-mesa" :class="cartaMesa.cor" :data-valor="cartaMesa.valor">
                    <span>{{ cartaMesa.valor }}</span>
                    <div class="bottom-corner">{{ cartaMesa.valor }}</div>
                </div>
            </div>
        </div>

        <div class="mao-container" :class="{ 'meu-turno': usuarioId === turnoAtual }">
            <h3 v-if="usuarioId === turnoAtual" style="margin: 0 0 10px 0; color: #48bb78; font-size: 24px;">✨ É A SUA VEZ! ✨</h3>
            <p v-else style="color: #a0aec0; margin-bottom: 5px; font-size: 16px; text-transform: uppercase; font-weight: bold;">Aguarde a sua vez...</p>
            <button v-if="usuarioId === turnoAtual" @click="comprarCarta" style="margin-bottom: 15px; background: #e53e3e; padding: 12px 25px; font-size: 16px; width: auto; display: inline-block;">🤷‍♂️ Nenhuma carta serve? Comprar e Passar Vez</button>
            <p style="color: #a0aec0; margin-bottom: 5px; font-size: 16px; text-transform: uppercase;">Suas Cartas (Clique para jogar)</p>
            <div class="mao">
                <div v-for="(carta, index) in mao" :key="index" class="carta carta-animada" :class="carta.cor" :data-valor="carta.valor" @click="jogarCarta(index)">
                    <span>{{ carta.valor }}</span>
                    <div class="bottom-corner">{{ carta.valor }}</div>
                </div>
            </div>
        </div>
    </div>

    <div v-if="escolhendoCor" class="modal-cor">
        <div class="modal-cor-content">
            <h3>🎨 Escolha a Cor Curinga!</h3>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button class="cor-btn Vermelho" @click="enviarCor('Vermelho')"></button>
                <button class="cor-btn Azul" @click="enviarCor('Azul')"></button>
                <button class="cor-btn Verde" @click="enviarCor('Verde')"></button>
                <button class="cor-btn Amarelo" @click="enviarCor('Amarelo')"></button>
            </div>
        </div>
    </div>

    <div class="card-menu" v-if="estado === 'FIM'">
        <h2 style="color: #f1c40f; font-size: 36px;">🏆 Fim de Jogo!</h2>
        <h1 style="color: #48bb78; font-size: 40px; margin: 10px 0;">Vencedor: {{ vencedor }}</h1>
        <p style="font-size: 20px;">Prêmio de <b>R$ {{ premio.toFixed(2) }}</b> creditado!</p>
        <button @click="estado = 'MENU'; mao = []">🕹️ Jogar Novamente</button>
    </div>

    <h3 style="margin-bottom: 5px; margin-top: 30px; font-size: 14px; text-transform: uppercase; color: #a0aec0; text-align: center;">Logs do Jogo</h3>
    <div class="log" ref="logContainer">
        <div v-for="l in logs">{{ l }}</div>
    </div>
</div>

<script>
const params = new URLSearchParams(window.location.search);
const userIdUrl = params.get('user') || 'user1'; 
new Vue({
    el: "#app",
    data: { 
        usuarioId: userIdUrl, 
        saldo: 10.00, 
        estado: 'MENU', 
        socket: null, 
        partidaId: null, 
        cartaMesa: null, 
        mao: [], 
        oponentes: [], 
        turnoAtual: "", 
        logs: [], 
        vencedor: "", 
        premio: 0, 
        esperandoResposta: false, 
        ultimaCartaTentada: null, 
        escolhendoCor: false, 
        cartaCuringaIndex: null 
    },
    mounted() { this.addLog("Sistema inicializado. Conectado como: " + this.usuarioId); },
    methods: {
        getOponentes() { return this.oponentes.filter(op => op.id !== this.usuarioId); },
        addLog(msg) {
            const time = new Date().toLocaleTimeString();
            this.logs.push(`[${time}] ${msg}`);
            this.$nextTick(() => { if(this.$refs.logContainer) this.$refs.logContainer.scrollTop = this.$refs.logContainer.scrollHeight; });
        },
        conectarSocket(callback) {
            if(!this.socket) {
                this.addLog("Conectando ao servidor...");
                this.socket = io("http://localhost:8000");
                this.socket.on("connect", () => { this.addLog("✅ Conectado com sucesso!"); if(callback) callback(); });
                this.socket.on("partidaIniciada", (data) => {
                    this.addLog("🔥 A PARTIDA COMEÇOU!"); this.estado = "JOGO"; this.partidaId = data.partidaId;
                    this.mao = data.suaMao; this.cartaMesa = data.cartaMesa; this.turnoAtual = data.turnoAtual; this.oponentes = data.oponentes;
                });
                this.socket.on("jogadaAceita", (data) => {
                    this.esperandoResposta = false; this.addLog(`⭐ ${data.jogador} jogou: ${data.carta.valor}`);
                    this.cartaMesa = data.carta; this.turnoAtual = data.proximoTurno; this.oponentes = data.oponentes || this.oponentes;
                });
                this.socket.on("jogadaInvalida", (data) => {
                    this.esperandoResposta = false; alert("Atenção: " + data.mensagem); this.addLog("❌ Jogada Inválida: " + data.mensagem);
                    if (this.ultimaCartaTentada) { this.mao.splice(this.ultimaCartaTentada.index, 0, this.ultimaCartaTentada.carta); this.ultimaCartaTentada = null; }
                });
                this.socket.on("suaNovaCarta", (data) => { this.esperandoResposta = false; this.mao.push(data.carta); this.addLog(`🎴 Você comprou um ${data.carta.valor}`); });
                this.socket.on("mensagem_jogo", (data) => { this.addLog(data.msg); });
                this.socket.on("fimDeJogo", (data) => {
                    this.addLog(`🏆 Vencedor: ${data.vencedor}`); this.vencedor = data.vencedor; this.premio = data.premio_total; this.estado = "FIM"; this.partidaId = null;
                    if(data.vencedor === this.usuarioId) this.saldo += this.premio;
                });
                this.socket.on("connect_error", (err) => { this.addLog("❌ Erro de conexão com servidor!"); });
            } else { if(callback) callback(); }
        },
        pagarEEntrarNaFila() {
            if(this.saldo < 1.00) { alert("Você não tem R$ 1,00 de saldo!"); return; }
            this.saldo -= 1.00; this.estado = "FILA";
            this.conectarSocket(() => { this.addLog("💳 Pagamento confirmado. Entrando na fila..."); this.socket.emit("entrarFila", { usuarioId: this.usuarioId }); });
        },
        jogarCarta(index) {
            if(!this.socket) return;
            if(this.turnoAtual !== this.usuarioId) { this.addLog("⏳ Aguarde o servidor processar sua vez..."); return; }
            const carta = this.mao[index];
            if (carta.cor === 'Curinga') { 
                this.escolhendoCor = true; 
                this.cartaCuringaIndex = index; 
                return; 
            }
            this.esperandoResposta = true; this.addLog("Enviando jogada..."); 
            this.socket.emit('jogarCarta', { partidaId: this.partidaId, cartaIndex: index });
            const c = this.mao[index]; this.mao.splice(index, 1); this.ultimaCartaTentada = { index, carta: c };
            setTimeout(() => { if(this.esperandoResposta) { this.esperandoResposta = false; this.addLog("⚠️ Timeout."); if(this.ultimaCartaTentada) { this.mao.splice(this.ultimaCartaTentada.index, 0, this.ultimaCartaTentada.carta); this.ultimaCartaTentada = null; } } }, 5000);
        },
        enviarCor(corEscolhida) {
            this.escolhendoCor = false; this.esperandoResposta = true; const index = this.cartaCuringaIndex;
            this.addLog("Enviando jogada Curinga com cor " + corEscolhida + "..."); 
            this.socket.emit('jogarCarta', { partidaId: this.partidaId, cartaIndex: index, corEscolhida: corEscolhida });
            const c = this.mao[index]; this.mao.splice(index, 1); this.ultimaCartaTentada = { index, carta: c }; this.cartaCuringaIndex = null;
            setTimeout(() => { if(this.esperandoResposta) { this.esperandoResposta = false; this.addLog("⚠️ Timeout."); if(this.ultimaCartaTentada) { this.mao.splice(this.ultimaCartaTentada.index, 0, this.ultimaCartaTentada.carta); this.ultimaCartaTentada = null; } } }, 5000);
        },
        comprarCarta() {
            if(!this.socket) return; if(this.turnoAtual !== this.usuarioId) return; if(this.esperandoResposta) return;
            this.esperandoResposta = true; this.addLog("Comprando carta e passando a vez..."); this.socket.emit('comprarCartaAqui', { partidaId: this.partidaId });
            setTimeout(() => { if(this.esperandoResposta) { this.esperandoResposta = false; this.addLog("⚠️ Timeout."); } }, 5000);
        }
    }
});
</script>
</body>
</html>"""

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated Index")
