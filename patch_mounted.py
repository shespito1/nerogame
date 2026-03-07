import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Make the game connect to socket straight on load and check if we are in a match
old_mounted = """    mounted() {
        this.addLog("Sistema inicializado. Conectado como: " + this.usuarioId);
        this.carregarGanhadores();
    },"""

new_mounted = """    mounted() {
        this.addLog("Sistema inicializado. Conectado como: " + this.usuarioId);
        this.carregarGanhadores();
        
        // Auto-conectar pra ver se tem jogo rolando:
        this.conectarSocket(() => {
            this.socket.emit("verificarReconexao", {usuarioId: this.usuarioId});
        });
    },"""

content = content.replace(old_mounted, new_mounted)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Mounted auto-connect inject done!")
