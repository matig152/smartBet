import sqlite3
import random
from datetime import datetime, timedelta

DATABASE_NAME = "smartbet.db"

def create_database():
    # Połączenie z bazą danych (jeśli plik nie istnieje, zostanie utworzony)
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    print("Tworzenie tabel w bazie SQLite...")

    # 1. Tabela meczów
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        home_team_name TEXT NOT NULL,
        away_team_name TEXT NOT NULL,
        home_team_id INTEGER,
        away_team_id INTEGER,
        league TEXT NOT NULL,
        sport TEXT NOT NULL,
        is_live BOOLEAN DEFAULT 0
    );
    """)

    # 2. Tabela historii ostatnich meczów (Forma zespołów)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        result TEXT CHECK(result IN ('W', 'D', 'L')),
        date TEXT
    );
    """)

    # 3. Tabela kursów i ofert bukmacherskich
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS odds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER,
        bookmaker_name TEXT NOT NULL,
        win1 REAL,
        draw REAL,
        win2 REAL,
        direct_url TEXT,
        FOREIGN KEY(match_id) REFERENCES matches(id)
    );
    """)

    # 4. Tabela flag użytkownika
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_flags (
        user_id INTEGER DEFAULT 1,
        match_id INTEGER,
        flag_type TEXT CHECK(flag_type IN ('intel', 'potential', 'trash')),
        PRIMARY KEY (user_id, match_id)
    );
    """)

    # 5. Tabela anomalii rynkowych (TOP 10)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anomalies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_name TEXT,
        bookmaker TEXT,
        change_percentage REAL,
        league TEXT,
        sport TEXT,
        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Tabela sesji czasowych użytkownika
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        duration_minutes INTEGER,
        session_date TEXT NOT NULL
    );
    """)

    conn.commit()
    return conn

def populate_sample_data(conn):
    cursor = conn.cursor()
    print("Wstawianie danych testowych...")

    # Czyszczenie starych danych (opcjonalne, przydatne przy re-uruchamianiu)
    cursor.execute("DELETE FROM matches")
    cursor.execute("DELETE FROM match_history")
    cursor.execute("DELETE FROM odds")
    cursor.execute("DELETE FROM user_flags")
    cursor.execute("DELETE FROM anomalies")
    cursor.execute("DELETE FROM user_sessions")

    # --- 1. WSTAWIANIE MECZÓW ---
    matches_data = [
        ("Legia Warszawa", "Lech Poznań", 101, 102, "Ekstraklasa", "Piłka nożna", 1), # mecz na żywo
        ("Real Madryt", "FC Barcelona", 201, 202, "La Liga", "Piłka nożna", 0),
        ("Manchester City", "Arsenal Londyn", 301, 302, "Premier League", "Piłka nożna", 0),
        ("Śląsk Wrocław", "Raków Częstochowa", 103, 104, "Ekstraklasa", "Piłka nożna", 1), # mecz na żywo
        ("Los Angeles Lakers", "Boston Celtics", 401, 402, "NBA", "Koszykówka", 0)
    ]
    cursor.executemany("""
        INSERT INTO matches (home_team_name, away_team_name, home_team_id, away_team_id, league, sport, is_live)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, matches_data)

    # --- 2. WSTAWIANIE HISTORII 5 MECZÓW (Forma drużyn) ---
    # ID zespołów: 101, 102, 201, 202, 301, 302, 103, 104, 401, 402
    team_ids = [101, 102, 201, 202, 301, 302, 103, 104, 401, 402]
    results_pool = ['W', 'W', 'D', 'L', 'W', 'D', 'L', 'W'] # większa szansa na wygraną dla realizmu
    
    today = datetime.now()
    history_data = []
    for team_id in team_ids:
        for i in range(5): # Ostatnie 5 meczów
            match_date = (today - timedelta(days=i*4)).strftime("%Y-%m-%d")
            res = random.choice(results_pool)
            history_data.append((team_id, res, match_date))
            
    cursor.executemany("""
        INSERT INTO match_history (team_id, result, date) VALUES (?, ?, ?)
    """, history_data)

    # --- 3. WSTAWIANIE KURSÓW BUKMACHERSKICH ---
    # Generujemy kilka ofert od różnych bukmacherów dla meczu o ID 1, 2 itd.
    odds_data = [
        # Mecz 1: Legia vs Lech
        (1, "STS", 2.15, 3.25, 3.10, "https://www.sts.pl/oferta/legia-lech"),
        (1, "Fortuna", 2.10, 3.40, 3.05, "https://www.efortuna.pl/oferta/legia-lech"),
        (1, "Betclic", 2.20, 3.20, 3.15, "https://www.betclic.pl/oferta/legia-lech"),
        
        # Mecz 2: Real vs Barcelona
        (2, "Superbet", 1.85, 3.80, 3.60, "https://superbet.pl/real-barca"),
        (2, "STS", 1.90, 3.75, 3.50, "https://www.sts.pl/oferta/real-barca"),
        
        # Mecz 3: City vs Arsenal
        (3, "Fortuna", 2.00, 3.50, 3.30, "https://www.efortuna.pl/city-arsenal"),
        
        # Mecz 5: Lakers vs Celtics
        (5, "Betclic", 1.70, 15.00, 2.15, "https://www.betclic.pl/lakers-celtics")
    ]
    cursor.executemany("""
        INSERT INTO odds (match_id, bookmaker_name, win1, draw, win2, direct_url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, odds_data)

    # --- 4. WSTAWIANIE PRZYKŁADOWYCH FLAG UŻYTKOWNIKA ---
    user_flags_data = [
        (1, 1, 'intel'),     # Użytkownik oznaczył Legia-Lech jako interesujące
        (1, 3, 'potential')  # City-Arsenal jako potencjalny zakład
    ]
    cursor.executemany("""
        INSERT INTO user_flags (user_id, match_id, flag_type) VALUES (?, ?, ?)
    """, user_flags_data)

    # --- 5. WSTAWIANIE ANOMALII RYNKOWYCH (Generujemy TOP 12, aby przetestować scrollbar) ---
    anomalies_data = [
        ("Legia Warszawa vs Lech Poznań", "Betclic", 18.5, "Ekstraklasa", "Piłka nożna"),
        ("Real Madryt vs FC Barcelona", "Superbet", 21.2, "La Liga", "Piłka nożna"),
        ("Manchester City vs Arsenal", "Fortuna", 16.0, "Premier League", "Piłka nożna"),
        ("Lakers vs Celtics", "STS", 15.1, "NBA", "Koszykówka"),
        ("Śląsk Wrocław vs Raków", "STS", 12.4, "Ekstraklasa", "Piłka nożna"),
        ("Polska vs Niemcy", "Betclic", 24.5, "Mecze Towarzyskie", "Piłka nożna"),
        ("Iga Świątek vs Aryna Sabalenka", "Superbet", 19.3, "WTA", "Tenis"),
        ("Hubert Hurkacz vs Novak Djokovic", "Fortuna", 17.2, "ATP", "Tenis"),
        ("GKS Katowice vs Jagiellonia", "STS", 11.2, "Ekstraklasa", "Piłka nożna"),
        ("Liverpool vs Chelsea", "Betclic", 14.8, "Premier League", "Piłka nożna"),
        ("Bayern Monachium vs Dortmund", "Superbet", 15.9, "Bundesliga", "Piłka nożna"),
        ("Juventus vs AC Milan", "Fortuna", 13.1, "Serie A", "Piłka nożna"),
    ]
    cursor.executemany("""
        INSERT INTO anomalies (match_name, bookmaker, change_percentage, league, sport)
        VALUES (?, ?, ?, ?, ?)
    """, anomalies_data)

    # --- 6. GENEROWANIE HISTORII AKTYWNOŚCI (Zegar i wykresy na 365 dni wstecz) ---
    # Wygenerujemy dane dla każdego dnia, aby wykresy w React mogły płynnie skalować się na 30, 90 i 365 dni
    session_data = []
    for day_offset in range(365):
        session_date = (today - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        # Użytkownik spędza losowo od 5 do 60 minut dziennie na szukanie zakładów
        duration = random.randint(5, 60)
        session_data.append((1, duration, session_date))
        
    cursor.executemany("""
        INSERT INTO user_sessions (user_id, duration_minutes, session_date)
        VALUES (?, ?, ?)
    """, session_data)

    conn.commit()
    print("Dane testowe pomyślnie zapisane w bazie danych!")

if __name__ == "__main__":
    connection = create_database()
    try:
        populate_sample_data(connection)
    finally:
        connection.close()
        print(f"Baza danych '{DATABASE_NAME}' jest gotowa do użycia z backendem FastAPI.")