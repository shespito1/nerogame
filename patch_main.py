import re
with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'uvicorn.run' not in text:
    text = text + "\n    uvicorn.run(main_app, host='0.0.0.0', port=8000)\n"
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(text)

with open('public/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('io("http://localhost:8000")', 'io(window.location.origin)')
html = html.replace("io('http://localhost:8000')", "io(window.location.origin)")
html = html.replace("io();", "io(window.location.origin);")
html = html.replace('this.socket = io()', 'this.socket = io(window.location.origin)')


with open('public/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
