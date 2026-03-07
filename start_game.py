import subprocess
import time
import re
import os
import sys

def run_command(command, shell=True, capture_output=True):
    if isinstance(command, list) and shell:
        command = subprocess.list2cmdline(command)
    print(f"Executando: {command}")
    stdout = subprocess.PIPE if capture_output else None
    stderr = subprocess.PIPE if capture_output else None
    return subprocess.Popen(command, shell=shell, stdout=stdout, stderr=stderr, text=True)

def update_backend_url(new_url):
    if not os.path.exists('index.html'):
        print("❌ index.html não encontrado.")
        return
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
    backend_proc = run_command([sys.executable, "main.py"], capture_output=False)
    
    # 2. Iniciar o Túnel (serveo.net)
    print("🌐 Abrindo túnel público seguro (serveo.net)...")
    if os.path.exists("serveo.log"):
        os.remove("serveo.log")
        
    tunnel_proc = subprocess.Popen("ssh -o StrictHostKeyChecking=no -R 80:127.0.0.1:8000 serveo.net > serveo.log 2>&1", shell=True)
    
    url = None
    for _ in range(20):
        if os.path.exists("serveo.log"):
            with open("serveo.log", "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Serveo usually gives: Forwarding HTTP traffic from https://[subdomain].serveousercontent.com
                match = re.search(r'(https://[a-zA-Z0-9-]+\.serveousercontent\.com)', content)
                if match:
                    url = match.group(1)
                    break
        time.sleep(1)
            
    if not url:
        print("❌ Erro ao obter URL do túnel serveo.")
        # Fallback to localhost.run if serveo fails
        print("🔄 Tentando localhost.run como alternativa...")
        tunnel_proc = subprocess.Popen("ssh -o StrictHostKeyChecking=no -R 80:127.0.0.1:8000 nokey@localhost.run > tunnel.log 2>&1", shell=True)
        for _ in range(15):
             if os.path.exists("tunnel.log"):
                with open("tunnel.log", "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    match = re.search(r'(https://[a-zA-Z0-9-]+\.lhr\.life)', content)
                    if match:
                        url = match.group(1)
                        break
             time.sleep(1)

    if not url:
        print("❌ Erro fatal: nenhum túnel disponível.")
        backend_proc.terminate()
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
        print("\n🛑 Encerrando servidor e túnel...")
        backend_proc.terminate()
        tunnel_proc.terminate()

if __name__ == "__main__":
    main()
