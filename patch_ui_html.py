import re

profile_html = """
    <!-- Top Right Profile -->
    <div style="position: absolute; top: 15px; right: 20px; z-index: 10000; text-align: right;">
        <img :src="`https://api.dicebear.com/7.x/adventurer/svg?seed=${avatarSeed}`" 
             @click="menuPerfilAberto = !menuPerfilAberto"
             style="width: 50px; height: 50px; border-radius: 50%; border: 3px solid #fbd38d; cursor: pointer; background: #2d3748; box-shadow: 0 4px 6px rgba(0,0,0,0.5);" />
        
        <div v-show="menuPerfilAberto" style="position: absolute; right: 0; background: rgba(45, 55, 72, 0.95); border: 2px solid #4a5568; border-radius: 10px; padding: 10px; margin-top: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.8); width: 220px; backdrop-filter: blur(5px);">
            <div @click="abrirAbaPerfil('perfil')" style="padding: 10px; color: white; cursor: pointer; border-bottom: 1px solid #4a5568; font-weight: bold; text-align: left;">👤 Perfil</div>
            <div @click="abrirAbaPerfil('sacar')" style="padding: 10px; color: #68d391; cursor: pointer; border-bottom: 1px solid #4a5568; font-weight: bold; text-align: left;">💸 Sacar</div>
            <div @click="abrirAbaPerfil('depositar')" style="padding: 10px; color: #fbd38d; cursor: pointer; border-bottom: 1px solid #4a5568; font-weight: bold; text-align: left;">💰 Depositar</div>
            <div @click="abrirAbaPerfil('historico')" style="padding: 10px; color: white; cursor: pointer; font-weight: bold; text-align: left;">📜 Histórico de Apostas</div>
        </div>
    </div>

    <!-- Modals para ações do Perfil (separado do menu, ocupa tela) -->
    <div v-if="abaPerfilAtiva" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:10001; display:flex; justify-content:center; align-items:center;">
        <div style="background: #1a202c; border: 2px solid #4a5568; color: white; width: 400px; padding: 20px; border-radius: 15px; position:relative; box-shadow: 0 10px 30px rgba(0,0,0,0.8);">
            <button @click="abaPerfilAtiva = null" style="position: absolute; top: 10px; right: 10px; background: #e53e3e; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-weight:bold;">X</button>
            
            <h2 v-if="abaPerfilAtiva === 'perfil'" style="font-family: 'Rowdies', cursive; margin-top:0;">👤 Seu Perfil</h2>
            <div v-if="abaPerfilAtiva === 'perfil'" style="font-size: 16px;">
                <p><strong>Usuário:</strong> {{ usuarioId }}</p>
                <p><strong>Saldo Atual:</strong> R$ {{ saldo.toFixed(2).replace('.', ',') }}</p>
                <div style="display:flex; justify-content:center; margin-top: 15px;">
                    <img :src="`https://api.dicebear.com/7.x/adventurer/svg?seed=${avatarSeed}`" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #fbd38d;" />
                </div>
            </div>

            <h2 v-if="abaPerfilAtiva === 'sacar'" style="font-family: 'Rowdies', cursive; margin-top:0; color:#68d391;">💸 Sacar Fundos</h2>
            <div v-if="abaPerfilAtiva === 'sacar'" style="font-size: 16px; color:#cbd5e0;">
                <p>Nesta versão o saque em breve estará disponível.</p>
            </div>

            <h2 v-if="abaPerfilAtiva === 'depositar'" style="font-family: 'Rowdies', cursive; margin-top:0; color:#fbd38d;">💰 Depositar</h2>
            <div v-if="abaPerfilAtiva === 'depositar'" style="font-size: 16px; color:#cbd5e0;">
                <p>Depósitos em breve estarão disponíveis.</p>
            </div>

            <h2 v-if="abaPerfilAtiva === 'historico'" style="font-family: 'Rowdies', cursive; margin-top:0;">📜 Histórico de Apostas</h2>
            <div v-if="abaPerfilAtiva === 'historico'" style="max-height: 50vh; overflow-y:auto;">
                
                <div v-if="partidaId" style="background: linear-gradient(135deg, #dd6b20, #e53e3e); padding:10px; border-radius: 10px; margin-bottom: 15px; cursor:pointer; border: 2px solid #fbd38d; box-shadow: 0 4px 15px rgba(221,107,32,0.4);" @click="abaPerfilAtiva=null; voltarPartidaForeground()">
                    <p style="margin:0; font-weight:bold; color: white; font-family: 'Rowdies', cursive;">🔥 Partida Em Progresso</p>
                    <p style="margin:5px 0 0 0; font-size:12px; color: #ffeebc;">Clique para voltar à mesa agora!</p>
                </div>
                
                <p v-if="historicoApostas.length === 0 && !partidaId" style="color: #a0aec0; text-align:center; padding: 20px 0;">Nenhuma aposta ainda.</p>
                
                <div v-for="h in historicoApostas" :key="h.id" style="background: #2d3748; padding: 10px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid;" :style="{ borderLeftColor: h.ganhou ? '#48bb78' : '#e53e3e' }">
                    <p style="margin:0; font-weight:bold; font-size:14px; word-break: break-all;">Partida: {{ h.id }}</p>
                    <p style="margin:5px 0 0 0; font-size:14px; font-weight: bold;" :style="{color: h.ganhou ? '#48bb78' : '#e53e3e'}">
                        {{ h.ganhou ? 'Venceu (+R$ ' + h.valor.toFixed(2) + ')' : 'Perdeu (R$ ' + h.valor.toFixed(2) + ')' }}
                    </p>
                </div>
            </div>
            
        </div>
    </div>
"""

with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# I will find "<div id="app" class="container">" and append this there
if 'dicebear' not in text.lower():
    text = re.sub(r'(<div id="app"[^>]*>)', r'\1\n' + profile_html, text, count=1)
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Injected HTML properly.")
else:
    print("Already injected.")
