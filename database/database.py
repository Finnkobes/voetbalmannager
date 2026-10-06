
import sqlite3
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE = BASE_DIR / "database" / "football.db"
PLAYERS_FILE = BASE_DIR / "data" / "players.json"


# =========================
# CLUBS
# =========================

clubs = [
    {
        "naam": "Ajax",
        "stad": "Amsterdam",
        "rating": 82,
        "logo": "ajax.png",
        "budget": 50000000,
        "salariskosten": 1200000,
        "stadioncapaciteit": 55000,
        "inkomsten_per_wedstrijd": 850000
    },
    {
        "naam": "PSV",
        "stad": "Eindhoven",
        "rating": 81,
        "logo": "psv.png",
        "budget": 45000000,
        "salariskosten": 1100000,
        "stadioncapaciteit": 35000,
        "inkomsten_per_wedstrijd": 650000
    },
    {
        "naam": "Feyenoord",
        "stad": "Rotterdam",
        "rating": 80,
        "logo": "feyenoord.png",
        "budget": 40000000,
        "salariskosten": 1000000,
        "stadioncapaciteit": 51000,
        "inkomsten_per_wedstrijd": 800000
    },
    {
        "naam": "FC Twente",
        "stad": "Enschede",
        "rating": 74,
        "logo": "fctwente.png",
        "budget": 20000000,
        "salariskosten": 550000,
        "stadioncapaciteit": 30205,
        "inkomsten_per_wedstrijd": 350000
    },
    {
        "naam": "AZ",
        "stad": "Alkmaar",
        "rating": 73,
        "logo": "az.png",
        "budget": 18000000,
        "salariskosten": 500000,
        "stadioncapaciteit": 19500,
        "inkomsten_per_wedstrijd": 250000
    },
    {
        "naam": "FC Utrecht",
        "stad": "Utrecht",
        "rating": 70,
        "logo": "fcutrecht.png",
        "budget": 15000000,
        "salariskosten": 425000,
        "stadioncapaciteit": 23750,
        "inkomsten_per_wedstrijd": 275000
    },

    # NIEUWE CLUBS
    {
        "naam": "ADO Den Haag",
        "stad": "Den Haag",
        "rating": 68,
        "logo": "ado_den_haag.png",
        "budget": 10000000,
        "salariskosten": 300000,
        "stadioncapaciteit": 15000,
        "inkomsten_per_wedstrijd": 175000
    },
    {
        "naam": "Excelsior Rotterdam",
        "stad": "Rotterdam",
        "rating": 67,
        "logo": "excelsior.png",
        "budget": 8500000,
        "salariskosten": 275000,
        "stadioncapaciteit": 3531,
        "inkomsten_per_wedstrijd": 125000
    },
    {
        "naam": "FC Groningen",
        "stad": "Groningen",
        "rating": 69,
        "logo": "fcgroningen.png",
        "budget": 12000000,
        "salariskosten": 350000,
        "stadioncapaciteit": 22525,
        "inkomsten_per_wedstrijd": 225000
    },
    {
        "naam": "Fortuna Sittard",
        "stad": "Sittard",
        "rating": 66,
        "logo": "fortuna.png",
        "budget": 8000000,
        "salariskosten": 250000,
        "stadioncapaciteit": 12500,
        "inkomsten_per_wedstrijd": 150000
    },
    {
        "naam": "Go Ahead Eagles",
        "stad": "Deventer",
        "rating": 68,
        "logo": "go_ahead_eagles.png",
        "budget": 9500000,
        "salariskosten": 275000,
        "stadioncapaciteit": 10400,
        "inkomsten_per_wedstrijd": 160000
    },
    {
        "naam": "N.E.C. Nijmegen",
        "stad": "Nijmegen",
        "rating": 70,
        "logo": "nec.png",
        "budget": 12000000,
        "salariskosten": 325000,
        "stadioncapaciteit": 12500,
        "inkomsten_per_wedstrijd": 175000
    },
    {
        "naam": "PEC Zwolle",
        "stad": "Zwolle",
        "rating": 65,
        "logo": "pec_zwolle.png",
        "budget": 7500000,
        "salariskosten": 225000,
        "stadioncapaciteit": 14000,
        "inkomsten_per_wedstrijd": 150000
    },
    {
        "naam": "SC Cambuur",
        "stad": "Leeuwarden",
        "rating": 64,
        "logo": "cambuur.png",
        "budget": 7000000,
        "salariskosten": 210000,
        "stadioncapaciteit": 15000,
        "inkomsten_per_wedstrijd": 140000
    },
    {
        "naam": "sc Heerenveen",
        "stad": "Heerenveen",
        "rating": 69,
        "logo": "heerenveen.png",
        "budget": 11000000,
        "salariskosten": 300000,
        "stadioncapaciteit": 26100,
        "inkomsten_per_wedstrijd": 250000
    },
    {
        "naam": "Sparta Rotterdam",
        "stad": "Rotterdam",
        "rating": 70,
        "logo": "sparta.png",
        "budget": 12000000,
        "salariskosten": 325000,
        "stadioncapaciteit": 11026,
        "inkomsten_per_wedstrijd": 180000
    },
    {
        "naam": "Telstar",
        "stad": "Velsen-Zuid",
        "rating": 62,
        "logo": "telstar.png",
        "budget": 5500000,
        "salariskosten": 175000,
        "stadioncapaciteit": 3370,
        "inkomsten_per_wedstrijd": 100000
    },
    {
        "naam": "Willem II",
        "stad": "Tilburg",
        "rating": 67,
        "logo": "willem_ii.png",
        "budget": 9000000,
        "salariskosten": 275000,
        "stadioncapaciteit": 14637,
        "inkomsten_per_wedstrijd": 170000
    }
]


# =========================
# DATABASE VERBINDING
# =========================

def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# =========================
# DATABASE AANMAKEN
# =========================

def create_database():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naam TEXT NOT NULL,
            stad TEXT NOT NULL,
            rating INTEGER NOT NULL,
            logo TEXT NOT NULL,
            budget INTEGER NOT NULL,
            salariskosten INTEGER NOT NULL,
            stadioncapaciteit INTEGER NOT NULL,
            inkomsten_per_wedstrijd INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER NOT NULL,
            naam TEXT NOT NULL,
            positie TEXT NOT NULL,
            leeftijd INTEGER NOT NULL,
            marktwaarde INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            salaris INTEGER NOT NULL,
            contractduur INTEGER NOT NULL,
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        home_club_id INTEGER NOT NULL,
        away_club_id INTEGER NOT NULL,
        home_score INTEGER NOT NULL DEFAULT 0,
        away_score INTEGER NOT NULL DEFAULT 0,
        gespeeld INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (home_club_id) REFERENCES clubs(id),
        FOREIGN KEY (away_club_id) REFERENCES clubs(id)
    )
""")

    connection.commit()
    connection.close()


# =========================
# DATABASE VULLEN
# =========================

def fill_database():

    connection = get_connection()
    cursor = connection.cursor()

    # =========================
    # OUDE GEGEVENS VERWIJDEREN
    # =========================

    cursor.execute("DELETE FROM players")
    cursor.execute("DELETE FROM matches")

    # Competition-tabel bestaat mogelijk nog niet
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS competition (
            club_id INTEGER PRIMARY KEY,
            gespeeld INTEGER NOT NULL DEFAULT 0,
            gewonnen INTEGER NOT NULL DEFAULT 0,
            gelijk INTEGER NOT NULL DEFAULT 0,
            verloren INTEGER NOT NULL DEFAULT 0,
            doelpunten_voor INTEGER NOT NULL DEFAULT 0,
            doelpunten_tegen INTEGER NOT NULL DEFAULT 0,
            punten INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        )
    """)

    cursor.execute("DELETE FROM competition")

    # Oude clubs verwijderen
    cursor.execute("DELETE FROM clubs")

    # =========================
    # CLUBS TOEVOEGEN
    # =========================

    for club in clubs:

        cursor.execute("""
            INSERT INTO clubs (
                naam,
                stad,
                rating,
                logo,
                budget,
                salariskosten,
                stadioncapaciteit,
                inkomsten_per_wedstrijd
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            club["naam"],
            club["stad"],
            club["rating"],
            club["logo"],
            club["budget"],
            club["salariskosten"],
            club["stadioncapaciteit"],
            club["inkomsten_per_wedstrijd"]
        ))

    # =========================
    # ALLE CLUBS IN COMPETITION
    # =========================

    cursor.execute("""
        SELECT id
        FROM clubs
        ORDER BY id
    """)

    alle_clubs = cursor.fetchall()

    for club in alle_clubs:

        cursor.execute("""
            INSERT INTO competition (
                club_id,
                gespeeld,
                gewonnen,
                gelijk,
                verloren,
                doelpunten_voor,
                doelpunten_tegen,
                punten
            )
            VALUES (?, 0, 0, 0, 0, 0, 0, 0)
        """, (
            club["id"],
        ))

    # =========================
    # SPELERS UIT JSON LADEN
    # =========================

    with open(PLAYERS_FILE, "r", encoding="utf-8") as bestand:
        players_per_club = json.load(bestand)

    # =========================
    # SPELERS TOEVOEGEN
    # =========================

    for club_naam, spelers in players_per_club.items():

        cursor.execute(
            "SELECT id FROM clubs WHERE naam = ?",
            (club_naam,)
        )

        club = cursor.fetchone()

        if club is None:
            print(f"Club niet gevonden: {club_naam}")
            continue

        club_id = club["id"]

        for speler in spelers:

            marktwaarde = speler["marktwaarde"]
            rating = speler["rating"]

            salaris = round(
                (marktwaarde * 0.04) + (rating * 1000)
            )

            contractduur = 3

            cursor.execute("""
                INSERT INTO players (
                    club_id,
                    naam,
                    positie,
                    leeftijd,
                    marktwaarde,
                    rating,
                    salaris,
                    contractduur
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                club_id,
                speler["naam"],
                speler["positie"],
                speler["leeftijd"],
                marktwaarde,
                rating,
                salaris,
                contractduur
            ))

    connection.commit()
    connection.close()

    print("18 clubs en spelers succesvol toegevoegd!")


# =========================
# START DATABASE
# =========================

if __name__ == "__main__":

    create_database()
    fill_database()

    print("Database is klaar!")

