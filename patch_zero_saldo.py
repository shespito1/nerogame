import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_saldo = "saldo: parseFloat(localStorage.getItem('saldo_uno')) || 10.00,"
new_saldo = "saldo: localStorage.getItem('saldo_uno') !== null ? parseFloat(localStorage.getItem('saldo_uno')) : 10.00,"

# Revert previous logic just in case it was modified partially
content = content.replace(old_saldo, new_saldo)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied for zero saldo")
