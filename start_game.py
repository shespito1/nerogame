import subprocess
import time
import re
import os
import sys

def update_backend_url(new_url):
    if not os.path.exists('index.html'):
        print("❌ index.html não encontrado.")
        return
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    updated_content = re.sub(
        r'const BACKEND_URL = ["\'].*?["\'];',
        f'const BACKEND_URL = "{new_url}";',
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

def get_tunnel_url():
    """Tenta localtunnel primeiro, depois serveo.net."""
    
    # Skipping localtunnel; using serveo.net fallback only
    print("🔄 Usando serveo.net como fallback (sem localtunnel)")
    
    # --- Tentativa 1: serveo.net (agora primário) ---
    proc_sv = subprocess.Popen(
        "ssh -o StrictHostKeyChecking=no -R 80:127.0.0.1:8000 serveo.net",
        shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    
    result_sv = []
    import threading
    def read_lines_sv():
        if proc_sv.stdout:
            for line in proc_sv.stdout:
                print(f"  [serveo] {line}", end="")
                m = re.search(r'(https://[a-zA-Z0-9-]+\.serveousercontent\.com)', line)
                if m and not result_sv:
                    result_sv.append(m.group(1))
    
    t_sv = threading.Thread(target=read_lines_sv, daemon=True)
    t_sv.start()
    
    for _ in range(15):
        if result_sv:
            # Convert to plain HTTP to avoid Chrome's invalid‑cert warning
            url = result_sv[0].replace('https://', 'http://')
            return url, proc_sv
        time.sleep(1)
    
    proc_sv.terminate()
    return None, None

def main():
    print("🎮 Iniciando Sistema Automatizado NeroCoin...")
    
    # 1. Abrir túnel PRIMEIRO (antes do backend, para não ter conflito de reload)
    url, tunnel_proc = get_tunnel_url()
    
    if not url:
        print("❌ Erro fatal: nenhum túnel disponível.")
        return
    
    print(f"✅ Túnel ativo: {url}")
    
    # 2. Atualizar frontend e push para GitHub
    update_backend_url(url)
    github_push()
    
    # 3. Iniciar o Servidor Backend (FastAPI) por ÚLTIMO
    print("🚀 Iniciando servidor backend...")
    backend_proc = subprocess.Popen(
        [sys.executable, "main.py"],
        shell=False
    )
    
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
        if tunnel_proc:
            tunnel_proc.terminate()

if __name__ == "__main__":
    main()
