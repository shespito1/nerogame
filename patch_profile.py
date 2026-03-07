import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the orange banner
banner_pattern = r'<div v-if="partidaId" @click="voltarPartidaForeground".*?</div>'
content = re.sub(banner_pattern, '', content, flags=re.DOTALL)

# 2. Add profile menu and its logic in Vue
profile_html = """
    <!-- Top Right Profile -->
    <div style="position: absolute; top: 15px; right: 20px; z-index: 10000; text-align: right;">
        <img :src="`https://api.dicebear.com/7.x/adventurer/svg?seed=${avatarSeed}`" 
             @click="menuPerfilAberto = !menuPerfilAberto"
             style="width: 50px; height: 50px; border-radius: 50%; border: 3px solid #fbd38d; cursor: pointer; background: #2d3748; box-shadow: 0 4px 6px rgba(0,0,0,0.5);" />
        
        <div v-if="menuPerfilAberto" style="background: rgba(45, 55, 72, 0.95); border: 2px solid #4a5568; border-radius: 10px; padding: 10px; margin-top: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.8); width: 220px;backdrop-filter: blur(5px);">
            <div @click="abrirAbaPerfil('perfil')" style="padding: 10px; color: white; cursor: pointer; border-bottom: 1px solid #4a5568; font-weight: bold; text-align: left;" onmouseover="this.style.background='#4a5568'" onmouseout="this.style.background='transparent'">👤 Perfil</div>
            <div @click="abrirAbaPerfil('sacar')" style="padding: 10px; color: #68d391; cursor: pointer; border-bottom: 1px solid #4a5568; font-weight: bold; text-align: left;" onmouseover="this.style.background='#4a5568'" onmouseout="this.style.background='transparent'">💸 Sacar</div>
            <div @click="abrirAbaPerfil('depositar')" style="padding: 10px; color: #fbd38d; cursor: pointer; border-bottom: 1px solid #4a5568; font-weight: bold; text-align: left;" onmouseover="this.style.background='#4a5568'" onmouseout="this.style.background='transparent'">💰 Depositar</div>
            <div @click="abrirAbaPerfil('historico')" style="padding: 10px; color: white; cursor: pointer; font-weight: bold; text-align: left;" onmouseover="this.style.background='#4a5568'" onmouseout="this.style.background='transparent'">📜 Histórico de Apostas</div>
        </div>
    </div>

    <!-- Modals para ações do Perfil -->
    <div v-if="abaPerfilAtiva" class="modal-cor" style="z-index: 10001; background: rgba(0,0,0,0.8);">
        <div class="modal-cor-content" style="background: #1a202c; border: 2px solid #4a5568; color: white; width: 400px; max-height:80vh; overflow-y:auto; position:relative;">
            <button @click="abaPerfilAtiva = null" style="position: absolute; top: 10px; right: 10px; background: #e53e3e; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;">X</button>
            
            <h2 v-if="abaPerfilAtiva === 'perfil'">👤 Seu Perfil</h2>
            <div v-if="abaPerfilAtiva === 'perfil'">
                <p><strong>Usuário:</strong> {{ usuarioId }}</p>
                <p><strong>Saldo Atual:</strong> R$ {{ saldo.toFixed(2).replace('.', ',') }}</p>
            </div>

            <h2 v-if="abaPerfilAtiva === 'sacar'">💸 Sacar</h2>
            <div v-if="abaPerfilAtiva === 'sacar'">
                <p>Nesta versão o saque em breve estará disponível.</p>
            </div>

            <h2 v-if="abaPerfilAtiva === 'depositar'">💰 Depositar</h2>
            <div v-if="abaPerfilAtiva === 'depositar'">
                <p>Depósitos em breve estarão disponíveis.</p>
            </div>

            <h2 v-if="abaPerfilAtiva === 'historico'">📜 Histórico</h2>
            <div v-if="abaPerfilAtiva === 'historico'">
                <div v-if="partidaId" style="background: #dd6b20; padding:10px; border-radius: 10px; margin-bottom: 15px; cursor:pointer;" @click="voltarPartidaForeground">
                    <p style="margin:0; font-weight:bold;">🔥 Partida Em Progresso ({{ partidaId }})</p>
                    <p style="margin:5px 0 0 0; font-size:12px;">Clique para voltar a mesa</p>
                </div>
                
                <p v-if="historicoApostas.length === 0 && !partidaId" style="color: #a0aec0;">Nenhuma aposta ainda.</p>
                
                <div v-for="h in historicoApostas" :key="h.id" style="background: #2d3748; padding: 10px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid;" :style="{ borderLeftColor: h.ganhou ? '#48bb78' : '#e53e3e' }">
                    <p style="margin:0; font-weight:bold; font-size:14px;">Partida: {{ h.id }}</p>
                    <p style="margin:5px 0 0 0; font-size:14px;" :style="{color: h.ganhou ? '#48bb78' : '#e53e3e'}">
                        {{ h.ganhou ? 'Ganhou (+' + h.valor.toFixed(2) + ')' : 'Perdeu (-' + h.valor.toFixed(2) + ')' }}
                    </p>
                </div>
            </div>
        </div>
    </div>
"""

# Insert right after <div id="app">
content = content.replace('<div id="app">', '<div id="app">\n' + profile_html)

# Now, we need to inject the Vue data fields
old_data = "estado: 'MENU',"
new_data = """estado: 'MENU',
        menuPerfilAberto: false,
        abaPerfilAtiva: null,
        avatarSeed: localStorage.getItem('avatar_seed') || Math.random().toString(36).substring(7),
        historicoApostas: JSON.parse(localStorage.getItem('historico_apostas')) || [],"""
content = content.replace(old_data, new_data)

# Inject watch logic for avatarSeed and historicoApostas
watch_patch = """        saldo(newVal) {
            localStorage.setItem('saldo_uno', newVal);
        },
        historicoApostas: {
            handler(newVal) {
                localStorage.setItem('historico_apostas', JSON.stringify(newVal));
            },
            deep: true
        },"""
content = content.replace("saldo(newVal) {\n            localStorage.setItem('saldo_uno', newVal);\n        },", watch_patch)

# Add method to open tab
methods_patch = """methods: {
        abrirAbaPerfil(aba) {
            this.abaPerfilAtiva = aba;
            this.menuPerfilAberto = false;
        },"""
content = content.replace("methods: {", methods_patch)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("HTML and Vue logic for Profile + Dropdown + Modal added!")
