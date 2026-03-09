import json
import os
import re
import subprocess
import sys
import time
import urllib.request


def update_backend_url(new_url):
    if not os.path.exists("index.html"):
        print("index.html nao encontrado.")
        return

    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()

    updated_content = re.sub(
        r'const BACKEND_URL = ["\'].*?["\'];',
        f'const BACKEND_URL = "{new_url}";',
        content,
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"index.html atualizado com a nova URL: {new_url}")


def github_push():
    print("Enviando atualizacao para o GitHub...")
    subprocess.run("git add index.html", shell=True)
    subprocess.run('git commit -m "Auto-update backend tunnel URL"', shell=True)
    subprocess.run("git push origin main", shell=True)
    print("GitHub Pages atualizado!")


def _capture_tunnel_url(proc, pattern, label, timeout_seconds):
    result = []
    import threading

    def read_lines():
        if proc.stdout:
            for line in proc.stdout:
                print(f"  [{label}] {line}", end="")
                match = re.search(pattern, line)
                if match and not result:
                    result.append(match.group(1))

    thread = threading.Thread(target=read_lines, daemon=True)
    thread.start()

    for _ in range(timeout_seconds):
        if result:
            return result[0]
        time.sleep(1)

    proc.terminate()
    return None


def _capture_ngrok_url(proc, timeout_seconds):
    for _ in range(timeout_seconds):
        if proc.poll() is not None:
            return None
        try:
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as response:
                data = json.load(response)
            for tunnel in data.get("tunnels", []):
                public_url = tunnel.get("public_url", "")
                if public_url.startswith("https://"):
                    return public_url
        except Exception:
            pass
        time.sleep(1)

    proc.terminate()
    return None


def get_tunnel_url():
    """Tenta ngrok primeiro, depois localtunnel e por fim serveo.net."""
    print("Tentando ngrok...")
    proc_ngrok = subprocess.Popen(
        "ngrok http 8000 --log stdout",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    url_ngrok = _capture_ngrok_url(proc_ngrok, 15)
    if url_ngrok:
        return url_ngrok, proc_ngrok

    print("ngrok falhou, tentando localtunnel...")
    proc_lt = subprocess.Popen(
        "lt --port 8000",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    url_lt = _capture_tunnel_url(
        proc_lt,
        r"(https://[a-zA-Z0-9-]+\.loca\.lt)",
        "lt",
        20,
    )
    if url_lt:
        return url_lt, proc_lt

    print("localtunnel falhou, tentando serveo.net...")
    proc_sv = subprocess.Popen(
        "ssh -o StrictHostKeyChecking=no -R 80:127.0.0.1:8000 serveo.net",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    url_sv = _capture_tunnel_url(
        proc_sv,
        r"(https://[a-zA-Z0-9-]+\.serveousercontent\.com)",
        "serveo",
        15,
    )
    if url_sv:
        return url_sv, proc_sv

    return None, None


def main():
    print("Iniciando Sistema Automatizado NeroCoin...")

    url, tunnel_proc = get_tunnel_url()
    if not url:
        print("Erro fatal: nenhum tunel disponivel.")
        return

    print(f"Tunel ativo: {url}")
    update_backend_url(url)
    github_push()

    print("Iniciando servidor backend...")
    backend_proc = subprocess.Popen([sys.executable, "main.py"], shell=False)

    print("\nTUDO PRONTO!")
    print("Site: https://shespito1.github.io/nerogame/")
    print("Backend (Local): http://localhost:8000")
    print(f"Backend (Publico): {url}")
    print("\nMantenha esta janela aberta para o servidor continuar funcionando.")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nEncerrando servidor e tunel...")
        backend_proc.terminate()
        if tunnel_proc:
            tunnel_proc.terminate()


if __name__ == "__main__":
    main()
