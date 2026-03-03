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
    
    # Tabela de Jogadores (Farm)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        wallet_address TEXT PRIMARY KEY,
        game_username TEXT,
        nero_balance REAL DEFAULT 0.0,
        energy INTEGER DEFAULT 100
    )
    """)
    
    # Tabela de Fazendeiros (Trabalhadores/Miners) que pertencem a um jogador
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farmers (
        farmer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        wallet_address TEXT,
        farmer_name TEXT,
        farming_power REAL DEFAULT 1.0, 
        last_harvest_time TIMESTAMP,
        is_working BOOLEAN DEFAULT 0,
        FOREIGN KEY(wallet_address) REFERENCES players(wallet_address)
    )
    """)
    
    conn.commit()
    conn.close()