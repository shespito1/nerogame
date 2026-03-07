import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add "Minimizar" button below AUTO JOGAR
old_auto_play = """        <label style="color: #63b3ed; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">
            <input type="checkbox" v-model="autoPlay" style="width: 18px; height: 18px; cursor: pointer;" />
            AUTO JOGAR
        </label>
    </div>"""

new_auto_play = """        <label style="color: #63b3ed; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">
            <input type="checkbox" v-model="autoPlay" style="width: 18px; height: 18px; cursor: pointer;" />
            AUTO JOGAR
        </label>
        <button @click="minimizarPartida" style="margin-top: 10px; width: 100%; padding: 6px; background: #e53e3e; color: white; border: none; border-radius: 6px; font-size: 11px; cursor: pointer; font-weight: bold; text-transform: uppercase;" onmouseover="this.style.background='#c53030'" onmouseout="this.style.background='#e53e3e'">
            Sair (Deixar Bot)
        </button>
    </div>"""

content = content.replace(old_auto_play, new_auto_play)

# 2. Add "Partida Background Banner" in MENU
old_menu = """    <div class="card-menu" v-if="estado === 'MENU'">
        <h2>🌟 Escolha seu Desafio</h2>"""

new_menu = """    <div class="card-menu" v-if="estado === 'MENU'">
        
        <div v-if="partidaId" @click="voltarPartidaForeground" style="margin-bottom: 20px; background: linear-gradient(135deg, #dd6b20, #e53e3e); padding: 15px; border-radius: 15px; cursor: pointer; box-shadow: 0 4px 15px rgba(221,107,32,0.4); border: 2px solid #fbd38d;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1.0)'">
            <h3 style="margin: 0 0 5px 0; color: white; font-size: 18px; font-family: 'Rowdies', cursive;">🔥 PARTIDA EM 2º PLANO! 🔥</h3>
            <p style="margin: 0; color: #ffeebc; font-size: 14px;">Seu Bot assumiu as cartas. Clique aqui para voltar à mesa!</p>
        </div>

        <h2>🌟 Escolha seu Desafio</h2>"""

content = content.replace(old_menu, new_menu)

# 3. Add the javascript methods
old_methods = """methods: {"""
new_methods = """methods: {
        minimizarPartida() {
            this.estado = 'MENU';
            this.addLog("Você saiu da visão da mesa. O Servidor ativou o Bot!");
            this.socket.emit("deixarPartidaEmBackground", { usuarioId: this.usuarioId });
        },
        voltarPartidaForeground() {
            this.estado = 'JOGO';
            this.addLog("Você retomou o controle da mesa!");
            this.socket.emit("verificarReconexao", { usuarioId: this.usuarioId });
        },"""

content = content.replace(old_methods, new_methods)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Frontend visualization for background match applied!")
