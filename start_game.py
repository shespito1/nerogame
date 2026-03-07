import subprocess
import time
import re
import os
import sys

def run_command(command, shell=True, capture_output=True):
    print(f"Executando: {command}")
    stdout = subprocess.PIPE if capture_output else None
    stderr = subprocess.PIPE if capture_output else None
    return subprocess.Popen(command, shell=shell, stdout=stdout, stderr=stderr, text=True)

def update_backend_url(new_url):
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substitui a URL do backend no index.html
    updated_content = re.sub(
        r"const BACKEND_URL = '.*?';",
        f"const BACKEND_URL = '{new_url}';",
        content
    )
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    print(f"✅ index.html atualizado com a nova URL: {new_url}")

def github_push():
    print("🚀 Enviando atualização para o GitHub...")
    subprocess.run("git add index.html", shell=True)
    subprocess.run('git commit -m "Auto-update backend tunnel URL"', shell=True)
    subprocess.run("git push origin main", shell=True)
    print("✅ GitHub Pages atualizado!")

def main():
    print("🎮 Iniciando Sistema Automatizado NeroCoin...")
    
    # 1. Iniciar o Servidor Backend (FastAPI) em background
    # Não capturamos o output aqui para evitar que o processo trave quando o buffer do pipe encher
    backend_proc = run_command([sys.executable, "main.py"], capture_output=False)
    
    # 2. Iniciar o Túnel (LocalTunnel)
    print("🌐 Abrindo túnel público...")
    # npx localtunnel --port 8000
    tunnel_proc = subprocess.Popen("npx localtunnel --port 8000", shell=True, stdout=subprocess.PIPE, text=True)
    
    url = None
    if tunnel_proc.stdout:
        for line in tunnel_proc.stdout:
            print(line, end="")
            if "your url is:" in line:
                url = line.split("is:")[1].strip()
                break
            
    if not url:
        print("❌ Erro ao obter URL do túnel.")
        backend_proc.terminate()
        tunnel_proc.terminate()
        return

    # 3. Atualizar o frontend e mandar pro GitHub
    update_backend_url(url)
    github_push()
    
    print(f"\n✨ TUDO PRONTO! ✨")
    print(f"Site: https://shespito1.github.io/nerogame/")
    print(f"Backend (Local): http://localhost:8000")
    print(f"Backend (Público): {url}")
    print("\nAVISO: Mantenha esta janela aberta para o servidor continuar funcionando.")
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Encerrando servidor...")
        backend_proc.terminate()
        tunnel_proc.terminate()

if __name__ == "__main__":
    main()
