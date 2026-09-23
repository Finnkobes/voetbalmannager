
import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "database" / "football.db"
PLAYERS_FILE = BASE_DIR / "data" / "players.json"


clubs = [
    {"naam": "Ajax", "stad": "Amsterdam", "rating": 82},
    {"naam": "PSV", "stad": "Eindhoven", "rating": 81},
    {"naam": "Feyenoord", "stad": "Rotterdam", "rating": 80},
    {"naam": "FC Twente", "stad": "Enschede", "rating": 74},
    {"naam": "AZ", "stad": "Alkmaar", "rating": 73},
    {"naam": "FC Utrecht", "stad": "Utrecht", "rating": 70}
]


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            naam TEXT NOT NULL,
            stad TEXT NOT NULL,
            rating INTEGER NOT NULL
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
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        )
    """)

    connection.commit()
    connection.close()


def fill_database():
    connection = get_connection()
    cursor = connection.cursor()

    # Oude gegevens verwijderen zodat er geen dubbele spelers komen
    cursor.execute("DELETE FROM players")
    cursor.execute("DELETE FROM clubs")

    # Clubs toevoegen
    for club in clubs:
        cursor.execute("""
            INSERT INTO clubs (naam, stad, rating)
            VALUES (?, ?, ?)
        """, (
            club["naam"],
            club["stad"],
            club["rating"]
        ))

    # Spelers uit JSON laden
    with open(PLAYERS_FILE, "r", encoding="utf-8") as bestand:
        players_per_club = json.load(bestand)

    # Spelers toevoegen
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
            cursor.execute("""
                INSERT INTO players
                (club_id, naam, positie, leeftijd, marktwaarde, rating)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                club_id,
                speler["naam"],
                speler["positie"],
                speler["leeftijd"],
                speler["marktwaarde"],
                speler["rating"]
            ))

    connection.commit()
    connection.close()

    print("Clubs en spelers succesvol toegevoegd!")


if __name__ == "__main__":
    create_database()
    fill_database()
    print("Database is klaar!")

