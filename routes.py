from fastapi import APIRouter, HTTPException
from database import get_db
from pydantic import BaseModel
import sqlite3

router = APIRouter()

class LoginRequest(BaseModel):
    wallet_address: str

@router.post("/api/login")
async def login_game(request: LoginRequest):
    """
    Função de login web3. 
    Se a carteira não existir, o servidor cria a conta do zero e te dá um Fazendeiro grátis de Boas Vindas!
    """
    conn = get_db()
    cursor = conn.cursor()
    
    wallet = request.wallet_address.lower()
    
    cursor.execute("SELECT * FROM players WHERE wallet_address = ?", (wallet,))
    player = cursor.fetchone()
    
    if not player:
        # Cria novo jogador
        cursor.execute("INSERT INTO players (wallet_address, game_username) VALUES (?, ?)", (wallet, f"Farm_{wallet[:6]}"))
        # Dá o primeiro fazendeiro pra ele
        cursor.execute("INSERT INTO farmers (wallet_address, farmer_name, farming_power) VALUES (?, ?, ?)", (wallet, "Jão Trabaiadô", 1.5))
        conn.commit()
        
        cursor.execute("SELECT * FROM players WHERE wallet_address = ?", (wallet,))
        player = cursor.fetchone()
        
    # Pega todos os fazendeiros dessa carteira pra mandar pro site desenhar
    cursor.execute("SELECT farmer_id, farmer_name, farming_power, is_working, last_harvest_time FROM farmers WHERE wallet_address = ?", (wallet,))
    farmers = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "success": True,
        "player_data": dict(player),
        "farmers": farmers
    }