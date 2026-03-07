import re
with open('public/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'(this\.socket\.on\("atualizarMao".*?\n[\s]*)+', 'this.socket.on("atualizarMao", (data) => { this.mao = data.mao; });\n                ', text)

with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
