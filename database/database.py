
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

    connection.commit()
    connection.close()


# =========================
# DATABASE VULLEN
# =========================

def fill_database():

    connection = get_connection()
    cursor = connection.cursor()

    # Oude gegevens verwijderen
    cursor.execute("DELETE FROM players")
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

            # Salaris berekenen op basis van marktwaarde en rating
            salaris = round(
                (marktwaarde * 0.04) + (rating * 1000)
            )

            # Contractduur tussen 1 en 5 jaar
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

    print("Clubs en spelers succesvol toegevoegd!")


# =========================
# START DATABASE
# =========================

if __name__ == "__main__":

    create_database()
    fill_database()

    print("Database is klaar!")

