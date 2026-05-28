from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="SmartBet Analytics API",
    description="Interaktywny serwer API dla systemu wykrywania anomalii bukmacherskich",
    version="1.0.0"
)

# Zezwolenie na komunikację z aplikacją React (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W środowisku produkcyjnym zmień na konkretny adres URL Reacta, np. ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE = "smartbet.db"

def get_db():
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# --- MODELE PYDANTIC ---
class FlagUpdate(BaseModel):
    match_id: int
    flag_type: str  # 'intel', 'potential', 'trash'

class TimeLog(BaseModel):
    user_id: int
    duration_minutes: int
    session_date: str

# --- ENDPOINTY API ---

@app.get("/")
def read_root():
    """Endpoint powitalny informujący o statusie serwera"""
    return {
        "status": "online", 
        "message": "Witamy w SmartBet Analytics API. Przejdź do /docs, aby otworzyć interaktywną dokumentację Swagger UI."
    }

@app.get("/api/matches")
def get_all_matches(db: sqlite3.Connection = Depends(get_db)):
    """Pobiera mecze wraz z aktualnymi kursami, historią ostatnich 5 spotkań oraz przypisanymi flagami"""
    cursor = db.cursor()
    
    # Dostosowane do nazw kolumn z wygenerowanego wcześniej skryptu bazy danych
    cursor.execute("SELECT id, home_team_name AS home, away_team_name AS away, home_team_id, away_team_id, league, sport, is_live FROM matches")
    matches = [dict(row) for row in cursor.fetchall()]
    
    for match in matches:
        # Pobieranie historii ostatnich 5 spotkań dla gospodarzy
        cursor.execute("SELECT result FROM match_history WHERE team_id = ? ORDER BY date DESC LIMIT 5", (match['home_team_id'],))
        match['last5_home'] = [r['result'] for r in cursor.fetchall()]
        
        # Pobieranie historii ostatnich 5 spotkań dla gości
        cursor.execute("SELECT result FROM match_history WHERE team_id = ? ORDER BY date DESC LIMIT 5", (match['away_team_id'],))
        match['last5_away'] = [r['result'] for r in cursor.fetchall()]
        
        # Pobieranie kursów bukmacherskich oraz przypisanie domyślnego zestawu jako 'current_odds'
        cursor.execute("SELECT bookmaker_name, win1, draw, win2, direct_url FROM odds WHERE match_id = ?", (match['id'],))
        odds_list = [dict(r) for r in cursor.fetchall()]
        
        if odds_list:
            # Mapowanie na ustrukturyzowany format oczekiwany przez komponent React
            match['bookmaker'] = odds_list[0]['bookmaker_name']
            match['current_odds'] = {
                "win1": odds_list[0]['win1'],
                "draw": odds_list[0]['draw'],
                "win2": odds_list[0]['win2']
            }
            match['url'] = odds_list[0]['direct_url']
        else:
            match['bookmaker'] = "Brak danych"
            match['current_odds'] = {"win1": 1.0, "draw": 1.0, "win2": 1.0}
            match['url'] = "#"

        # Pobieranie flagi przypisanej przez zalogowanego użytkownika (domyślnie user_id=1)
        cursor.execute("SELECT flag_type FROM user_flags WHERE match_id = ? AND user_id = 1", (match['id'],))
        flag_row = cursor.fetchone()
        match['flag'] = flag_row['flag_type'] if flag_row else "all"
        
    return matches

@app.post("/api/flags")
def update_match_flag(data: FlagUpdate, db: sqlite3.Connection = Depends(get_db)):
    """Dodaje lub aktualizuje flagę użytkownika przy wybranym kursie (intel, potential, trash)"""
    if data.flag_type not in ['intel', 'potential', 'trash', 'all']:
        raise HTTPException(status_code=400, detail="Nieprawidłowy typ flagi. Dozwolone: 'intel', 'potential', 'trash', 'all'")
        
    cursor = db.cursor()
    try:
        if data.flag_type == 'all':
            # Jeśli użytkownik resetuje flagę, usuwamy wpis z bazy
            cursor.execute("DELETE FROM user_flags WHERE match_id = ? AND user_id = 1", (data.match_id,))
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO user_flags (user_id, match_id, flag_type) VALUES (1, ?, ?)",
                (data.match_id, data.flag_type)
            )
        db.commit()
        return {"status": "success", "message": f"Flaga została zaktualizowana na: {data.flag_type}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/anomalies")
def get_top_anomalies(sport: Optional[str] = None, league: Optional[str] = None, limit: int = 10, db: sqlite3.Connection = Depends(get_db)):
    """Zwraca listę anomalii rynkowych posortowanych malejąco według procentowej odchyłki kursu"""
    cursor = db.cursor()
    query = "SELECT id, match_name AS match, bookmaker, change_percentage || '%' AS change, league, sport FROM anomalies WHERE 1=1"
    params = []
    
    if sport and sport != "All":
        query += " AND sport = ?"
        params.append(sport)
    if league and league != "All":
        query += " AND league = ?"
        params.append(league)
        
    query += " ORDER BY change_percentage DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

@app.get("/api/user/time-stats")
def get_user_time_stats(days: int = 30, db: sqlite3.Connection = Depends(get_db)):
    """Pobiera zsumowane czasy aktywności użytkownika z podziałem na dni dla zadanego okresu (np. 30, 90, 365)"""
    cursor = db.cursor()
    cursor.execute("""
        SELECT session_date AS day, SUM(duration_minutes) AS minutes 
        FROM user_sessions 
        WHERE user_id = 1 
        GROUP BY session_date 
        ORDER BY session_date DESC 
        LIMIT ?
    """, (days,))
    # Odwracamy wyniki, aby wykres liniowy we frontendzie układał się chronologicznie od lewej do prawej
    return list(reversed([dict(row) for row in cursor.fetchall()]))

@app.post("/api/user/time-log")
def log_user_time(data: TimeLog, db: sqlite3.Connection = Depends(get_db)):
    """Rejestruje czas spędzony przez użytkownika podczas bieżącej sesji"""
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO user_sessions (user_id, duration_minutes, session_date) VALUES (?, ?, ?)",
            (data.user_id, data.duration_minutes, data.session_date)
        )
        db.commit()
        return {"status": "success", "message": "Czas sesji został pomyślnie zapisany"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- BLOK URUCHOMIENIOWY SERWERA ---
if __name__ == "__main__":
    print("Uruchamianie serwera SmartBet Analytics...")
    print("Interaktywna dokumentacja dostępna pod adresem: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)")
    print("Dokumentacja alternatywna (ReDoc): [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)")
    
    # Uruchomienie uvicorna bezpośrednio ze skryptu
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)