with open("public/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
new_code = "let serverUrl = window.location.protocol === 'file:' ? 'http://localhost:8000' : window.location.origin;\n                this.socket = io(serverUrl);"
text = re.sub(r'this\.socket\s*=\s*io\(.*?\);', new_code, text)

with open("public/index.html", "w", encoding="utf-8") as f:
    f.write(text)
