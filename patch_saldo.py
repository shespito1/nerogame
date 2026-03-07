import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Troca o inicio do saldo:
# saldo: 10.00, -> saldo: parseFloat(localStorage.getItem('saldo_uno')) || 10.00,
content = re.sub(r'saldo:\s*10\.00\s*,', "saldo: parseFloat(localStorage.getItem('saldo_uno')) || 10.00,", content)

# 2. Adiciona um "watch" no Vue.js para salvar o saldo no localStorage SEMPRE que ele mudar (soma ou dedução da aposta/vitoria)
watching_code = """    watch: {
        saldo(newVal) {
            localStorage.setItem('saldo_uno', newVal);
        }
    },
    methods: {"""

if 'watch: {' not in content:
    content = content.replace('methods: {', watching_code)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch aplicado com sucesso!")
