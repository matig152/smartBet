import sqlite3
import random
from datetime import datetime, timedelta

DATABASE_NAME = "smartbet.db"

def create_database():
    # Połączenie z bazą danych (jeśli plik nie istnieje, zostanie utworzony)
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    print("Tworzenie tabel w bazie SQLite...")

    # Usunięcie starych tabel (aby zaktualizować schemat)
    cursor.execute("DROP TABLE IF EXISTS matches")
    cursor.execute("DROP TABLE IF EXISTS match_history")
    cursor.execute("DROP TABLE IF EXISTS odds")
    cursor.execute("DROP TABLE IF EXISTS user_flags")
    cursor.execute("DROP TABLE IF EXISTS anomalies")
    cursor.execute("DROP TABLE IF EXISTS user_sessions")

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
        is_live BOOLEAN DEFAULT 0,
        url TEXT
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

    # --- 1. WSTAWIANIE MECZÓW (Wszystkie 19 pozycji) ---
    matches_data = [
        # Liga Polska (9 meczów)
        ("Raków Częstochowa", "Arka Gdynia", 101, 102, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/rakow-arka"),
        ("Cracovia", "Korona Kielce", 103, 104, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/cracovia-korona"),
        ("Pogoń Szczecin", "GKS Katowice", 105, 106, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/pogon-gks"),
        ("Górnik Zabrze", "Radomiak Radom", 107, 108, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/gornik-radomiak"),
        ("Jagiellonia Białystok", "Zagłębie Lubin", 109, 110, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/jagiellonia-zaglebie"),
        ("Lech Poznań", "Wisła Płock", 111, 112, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/lech-wisla"),
        ("Bruk-Bet T.", "Lechia Gdańsk", 113, 114, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/brukbet-lechia"),
        ("Legia Warszawa", "Motor Lublin", 115, 116, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/legia-motor"),
        ("Widzew Łódź", "Piast Gliwice", 117, 118, "Polska", "Piłka nożna", 0, "https://www.betclic.pl/oferta/widzew-piast"),
        
        # Liga Hiszpańska (10 meczów)
        ("Villarreal", "Atl. Madrid", 201, 202, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/villarreal-atletico"),
        ("Alaves", "Rayo Vallecano", 203, 204, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/alaves-rayo"),
        ("Real Madrid", "Ath Bilbao", 205, 206, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/real-bilbao"),
        ("Valencia", "Barcelona", 207, 208, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/valencia-barcelona"),
        ("Betis", "Levante", 209, 210, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/betis-levante"),
        ("Celta Vigo", "Sevilla", 211, 212, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/celta-sevilla"),
        ("Girona", "Elche", 213, 214, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/girona-elche"),
        ("Espanyol", "Real Sociedad", 215, 216, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/espanyol-sociedad"),
        ("Getafe", "Osasuna", 217, 218, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/getafe-osasuna"),
        ("Mallorca", "Oviedo", 219, 220, "Hiszpania", "Piłka nożna", 0, "https://www.betclic.pl/oferta/mallorca-oviedo")
    ]
    cursor.executemany("""
        INSERT INTO matches (home_team_name, away_team_name, home_team_id, away_team_id, league, sport, is_live, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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

    # --- 3. WSTAWIANIE KURSÓW BUKMACHERSKICH (Dla wszystkich 19 meczów x 3 bukmacherów) ---
    odds_data = [
        # ================= LIGA POLSKA =================
        # Mecz 1: Raków Częstochowa vs Arka Gdynia
        (1, "Betclic", 1.28, 6.25, 11.00, "https://www.betclic.pl/oferta/rakow-arka"),
        (1, "STS", 1.25, 6.50, 11.50, "https://www.sts.pl/oferta/rakow-arka"),
        (1, "Fortuna", 1.38, 6.10, 10.50, "https://www.efortuna.pl/oferta/rakow-arka"),

        # Mecz 2: Cracovia vs Korona Kielce
        (2, "Betclic", 2.20, 3.25, 4.30, "https://www.betclic.pl/oferta/cracovia-korona"),
        (2, "STS", 2.15, 3.10, 4.45, "https://www.sts.pl/oferta/cracovia-korona"),
        (2, "Fortuna", 2.25, 2.95, 4.20, "https://www.efortuna.pl/oferta/cracovia-korona"),

        # Mecz 3: Pogoń Szczecin vs GKS Katowice
        (3, "Betclic", 2.50, 4.00, 2.60, "https://www.betclic.pl/oferta/pogon-gks"),
        (3, "STS", 2.40, 4.15, 2.80, "https://www.sts.pl/oferta/pogon-gks"),
        (3, "Fortuna", 2.55, 3.85, 2.50, "https://www.efortuna.pl/oferta/pogon-gks"),

        # Mecz 4: Górnik Zabrze vs Radomiak Radom
        (4, "Betclic", 1.55, 4.80, 8.00, "https://www.betclic.pl/oferta/gornik-radomiak"),
        (4, "STS", 1.42, 4.95, 10.30, "https://www.sts.pl/oferta/gornik-radomiak"),
        (4, "Fortuna", 1.47, 4.65, 7.60, "https://www.efortuna.pl/oferta/gornik-radomiak"),

        # Mecz 5: Jagiellonia Białystok vs Zagłębie Lubin
        (5, "Betclic", 1.63, 5.25, 7.40, "https://www.betclic.pl/oferta/jagiellonia-zaglebie"),
        (5, "STS", 1.39, 5.40, 7.70, "https://www.sts.pl/oferta/jagiellonia-zaglebie"),
        (5, "Fortuna", 1.45, 5.10, 7.10, "https://www.efortuna.pl/oferta/jagiellonia-zaglebie"),

        # Mecz 6: Lech Poznań vs Wisła Płock
        (6, "Betclic", 1.38, 6.25, 7.80, "https://www.betclic.pl/oferta/lech-wisla"),
        (6, "STS", 1.34, 6.50, 8.20, "https://www.sts.pl/oferta/lech-wisla"),
        (6, "Fortuna", 1.41, 5.00, 9.40, "https://www.efortuna.pl/oferta/lech-wisla"),

        # Mecz 7: Bruk-Bet T. vs Lechia Gdańsk
        (7, "Betclic", 4.05, 4.75, 1.80, "https://www.betclic.pl/oferta/brukbet-lechia"),
        (7, "STS", 4.20, 4.90, 2.05, "https://www.sts.pl/oferta/brukbet-lechia"),
        (7, "Fortuna", 3.90, 4.60, 1.83, "https://www.efortuna.pl/oferta/brukbet-lechia"),

        # Mecz 8: Legia Warszawa vs Motor Lublin
        (8, "Betclic", 1.51, 4.90, 8.50, "https://www.betclic.pl/oferta/legia-motor"),
        (8, "STS", 1.47, 5.10, 6.80, "https://www.sts.pl/oferta/legia-motor"),
        (8, "Fortuna", 1.55, 4.75, 6.20, "https://www.efortuna.pl/oferta/legia-motor"),

        # Mecz 9: Widzew Łódź vs Piast Gliwice
        (9, "Betclic", 2.52, 3.45, 3.10, "https://www.betclic.pl/oferta/widzew-piast"),
        (9, "STS", 1.95, 3.55, 5.20, "https://www.sts.pl/oferta/widzew-piast"),
        (9, "Fortuna", 2.60, 3.35, 3.00, "https://www.efortuna.pl/oferta/widzew-piast"),

        # ================= LIGA HISZPAŃSKA =================
        # Mecz 10: Villarreal vs Atl. Madrid
        (10, "Betclic", 2.85, 3.90, 2.60, "https://www.betclic.pl/oferta/villarreal-atletico"),
        (10, "STS", 2.50, 4.05, 2.65, "https://www.sts.pl/oferta/villarreal-atletico"),
        (10, "Fortuna", 2.62, 3.75, 2.52, "https://www.efortuna.pl/oferta/villarreal-atletico"),

        # Mecz 11: Alaves vs Rayo Vallecano
        (11, "Betclic", 2.32, 3.35, 3.80, "https://www.betclic.pl/oferta/alaves-rayo"),
        (11, "STS", 2.25, 3.45, 3.95, "https://www.sts.pl/oferta/alaves-rayo"),
        (11, "Fortuna", 2.38, 3.00, 4.05, "https://www.efortuna.pl/oferta/alaves-rayo"),

        # Mecz 12: Real Madrid vs Ath Bilbao
        (12, "Betclic", 1.54, 4.80, 8.10, "https://www.betclic.pl/oferta/real-bilbao"),
        (12, "STS", 1.50, 4.95, 6.40, "https://www.sts.pl/oferta/real-bilbao"),
        (12, "Fortuna", 1.58, 4.65, 5.85, "https://www.efortuna.pl/oferta/real-bilbao"),

        # Mecz 13: Valencia vs Barcelona
        (13, "Betclic", 3.60, 4.10, 2.20, "https://www.betclic.pl/oferta/valencia-barcelona"),
        (13, "STS", 3.75, 4.25, 1.95, "https://www.sts.pl/oferta/valencia-barcelona"),
        (13, "Fortuna", 3.45, 3.95, 2.05, "https://www.efortuna.pl/oferta/valencia-barcelona"),

        # Mecz 14: Betis vs Levante
        (14, "Betclic", 2.40, 3.50, 3.15, "https://www.betclic.pl/oferta/betis-levante"),
        (14, "STS", 2.12, 3.60, 3.25, "https://www.sts.pl/oferta/betis-levante"),
        (14, "Fortuna", 2.45, 3.40, 3.05, "https://www.efortuna.pl/oferta/betis-levante"),

        # Mecz 15: Celta Vigo vs Sevilla
        (15, "Betclic", 1.92, 3.40, 4.75, "https://www.betclic.pl/oferta/celta-sevilla"),
        (15, "STS", 1.87, 3.50, 4.95, "https://www.sts.pl/oferta/celta-sevilla"),
        (15, "Fortuna", 2.27, 3.30, 4.55, "https://www.efortuna.pl/oferta/celta-sevilla"),

        # Mecz 16: Girona vs Elche
        (16, "Betclic", 1.85, 3.80, 5.40, "https://www.betclic.pl/oferta/girona-elche"),
        (16, "STS", 1.80, 3.95, 4.60, "https://www.sts.pl/oferta/girona-elche"),
        (16, "Fortuna", 1.90, 3.65, 4.20, "https://www.efortuna.pl/oferta/girona-elche"),

        # Mecz 17: Espanyol vs Real Sociedad
        (17, "Betclic", 2.45, 3.55, 3.20, "https://www.betclic.pl/oferta/espanyol-sociedad"),
        (17, "STS", 2.38, 3.65, 3.30, "https://www.espanyol-sociedad"),
        (17, "Fortuna", 2.90, 3.05, 3.10, "https://www.efortuna.pl/oferta/espanyol-sociedad"),

        # Mecz 18: Getafe vs Osasuna
        (18, "Betclic", 3.20, 2.70, 3.20, "https://www.betclic.pl/oferta/getafe-osasuna"),
        (18, "STS", 3.70, 2.75, 3.10, "https://www.sts.pl/oferta/getafe-osasuna"),
        (18, "Fortuna", 3.10, 2.65, 3.30, "https://www.efortuna.pl/oferta/getafe-osasuna"),

        # Mecz 19: Mallorca vs Oviedo
        (19, "Betclic", 1.69, 4.50, 7.20, "https://www.betclic.pl/oferta/mallorca-oviedo"),
        (19, "STS", 1.45, 4.65, 7.60, "https://www.sts.pl/oferta/mallorca-oviedo"),
        (19, "Fortuna", 1.52, 4.35, 6.80, "https://www.efortuna.pl/oferta/mallorca-oviedo")
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