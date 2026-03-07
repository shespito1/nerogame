import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update fimDeJogo listener to insert history
old_fim_jogo = """                this.socket.on("fimDeJogo", (data) => {
                    this.addLog(`🏆 Vencedor: ${data.vencedor}`); this.vencedor = data.vencedor; this.premio = data.premio_total; this.estado = "FIM"; this.partidaId = null;
                    if(data.vencedor === this.usuarioId) this.saldo += this.premio;
                });"""

new_fim_jogo = """                this.socket.on("fimDeJogo", (data) => {
                    this.addLog(`🏆 Vencedor: ${data.vencedor}`); this.vencedor = data.vencedor; this.premio = data.premio_total; this.estado = "FIM"; 
                    
                    const ganhou = (data.vencedor === this.usuarioId);
                    if(ganhou) this.saldo += this.premio;
                    
                    // Salvar no histórico
                    this.historicoApostas.unshift({
                        id: this.partidaId,
                        ganhou: ganhou,
                        valor: ganhou ? this.premio : 0.00
                    });

                    this.partidaId = null;
                });"""
content = content.replace(old_fim_jogo, new_fim_jogo)

# 2. Add some visual polish to the profile menu
old_avatar = """<img :src="`https://api.dicebear.com/7.x/adventurer/svg?seed=${avatarSeed}`" """
new_avatar = """<div v-if="estado === 'MENU'" style="position: absolute; top: 15px; right: 20px; z-index: 10000; text-align: right;">
        <img :src="`https://api.dicebear.com/7.x/adventurer/svg?seed=${avatarSeed}`" """
content = content.replace(old_avatar, new_avatar)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Game Over logic tracking history added!")
