import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('this.saldo -= valorAposta; this.estado = "FILA";', 'this.saldo -= valorAposta; this.ultimaAposta = valorAposta; this.estado = "FILA";')

if 'ultimaAposta' not in text:
    text = text.replace("estado: 'MENU',", "estado: 'MENU',\n        ultimaAposta: parseFloat(localStorage.getItem('ultima_aposta')) || 0,")

old_history = """// Salvar no histórico
                    this.historicoApostas.unshift({
                        id: this.partidaId,
                        ganhou: ganhou,
                        valor: ganhou ? this.premio : 0.00
                    });"""

new_history = """// Salvar no histórico
                    this.historicoApostas.unshift({
                        id: this.partidaId,
                        ganhou: ganhou,
                        valor: ganhou ? this.premio : (this.ultimaAposta || 0)
                    });"""
text = text.replace(old_history, new_history)

old_watch_saldo = """saldo(newVal) {
            localStorage.setItem('saldo_uno', newVal);
        },"""
new_watch_saldo = """saldo(newVal) {
            localStorage.setItem('saldo_uno', newVal);
        },
        ultimaAposta(newVal) {
            localStorage.setItem('ultima_aposta', newVal);
        },"""
if 'ultimaAposta(newVal)' not in text:
    text = text.replace(old_watch_saldo, new_watch_saldo)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated historic log for losses.')
