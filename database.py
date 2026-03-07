import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "game.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # Tabela de Bots
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_email TEXT,
        nome TEXT,
        saldo REAL DEFAULT 10.0,
        stop_loss REAL DEFAULT 5.0,
        stop_win REAL DEFAULT 20.0,
        valor_aposta REAL DEFAULT 1.0,
        status TEXT DEFAULT 'Parado'
    )
    """)
    
    # Tabela de Jogadores (Farm)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        email TEXT PRIMARY KEY,
        password TEXT,
        game_username TEXT,
        nero_balance REAL DEFAULT 0.0,
        energy INTEGER DEFAULT 100
    )
    """)

    # Tabela de Fazendeiros (Trabalhadores/Miners) que pertencem a um jogador
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farmers (
        farmer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        farmer_name TEXT,
        farming_power REAL DEFAULT 1.0,
        last_harvest_time TIMESTAMP,
        is_working BOOLEAN DEFAULT 0,
        FOREIGN KEY(email) REFERENCES players(email)
    )
    """)

    # Tabela de Inventário de Itens/Moedas do Jogador
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        item_name TEXT,
        quantity REAL DEFAULT 0.0,
        FOREIGN KEY(email) REFERENCES players(email),
        UNIQUE(email, item_name)
    )
    """)

    # --- TABELAS PARA O SISTEMA DE UNO/APOSTAS ---

    # Tabela usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        senha TEXT,
        saldo REAL DEFAULT 0.0
    )
    """)

    # Tabela partidas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status TEXT DEFAULT 'Aguardando', -- Aguardando, Em curso, Finalizada
        valor_aposta REAL,
        taxa_retida REAL DEFAULT 0.0
    )
    """)

    # Tabela transacoes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        valor REAL,
        tipo TEXT, -- Aposta, Premio
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)

    conn.commit()
    conn.close()