import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATABASE = (
    BASE_DIR
    / "database"
    / "football.db"
)


def reset_database():

    if not DATABASE.exists():

        print("Database niet gevonden:")
        print(DATABASE)

        return


    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()


    # =========================
    # STATISTIEK TABELLEN
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            player_id INTEGER NOT NULL,
            maand TEXT NOT NULL,
            wedstrijden INTEGER NOT NULL DEFAULT 0,
            doelpunten INTEGER NOT NULL DEFAULT 0,
            motm INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, maand)
        )
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_awards (
            match_id INTEGER PRIMARY KEY,
            player_id INTEGER,
            player_name TEXT,
            club_id INTEGER,
            club_name TEXT,
            datum TEXT
        )
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            datum TEXT,
            spreker TEXT,
            rol TEXT,
            club_name TEXT,
            tekst TEXT
        )
    """)


    # =========================
    # WEDSTRIJDEN RESETTEN
    # =========================
    cursor.execute("""
        DELETE FROM matches
    """)

    # =========================
    # COMPETITIE RESETTEN
    # =========================

    cursor.execute("""
        UPDATE competition
        SET
            gespeeld = 0,
            gewonnen = 0,
            gelijk = 0,
            verloren = 0,
            doelpunten_voor = 0,
            doelpunten_tegen = 0,
            punten = 0
    """)


    # =========================
    # STATISTIEKEN WISSEN
    # =========================

    cursor.execute("""
        DELETE FROM player_stats
    """)


    cursor.execute("""
        DELETE FROM match_awards
    """)


    cursor.execute("""
        DELETE FROM interviews
    """)


    connection.commit()
    connection.close()


    print()
    print("==============================")
    print("      CLUBMASTER RESET")
    print("==============================")
    print("Wedstrijden: niet gespeeld")
    print("Scores: 0 - 0")
    print("Competitie: gereset")
    print("Topscorers: gewist")
    print("MOTM: gewist")
    print("Interviews: gewist")
    print("==============================")
    print()


if __name__ == "__main__":
    reset_database()