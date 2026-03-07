import re

with open('public/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Since 'watch: {' already exists, the previous patch failed silently over it.
# We will inject the saldo watcher right after 'watch: {'

replacement = """watch: {
        saldo(newVal) {
            localStorage.setItem('saldo_uno', newVal);
        },"""

content = re.sub(r'watch:\s*\{', replacement, content, count=1)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch saldo in watch applied!")