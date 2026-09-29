import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database" / "football.db"

connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row

# Eerste wedstrijd ophalen
wedstrijd = connection.execute("""
    SELECT
        id,
        home_club_id,
        away_club_id,
        gespeeld,
        home_score,
        away_score
    FROM matches
    ORDER BY speelronde ASC, id ASC
    LIMIT 1
""").fetchone()

if wedstrijd is None:
    print("Geen wedstrijd gevonden.")
else:

    print(
        f"Eerste wedstrijd: ID {wedstrijd['id']} "
        f"({wedstrijd['home_score']} - {wedstrijd['away_score']})"
    )

    # Eerste wedstrijd resetten
    connection.execute("""
        UPDATE matches
        SET
            home_score = 0,
            away_score = 0,
            gespeeld = 0
        WHERE id = ?
    """, (wedstrijd["id"],))

    # Competitiestatistieken van beide clubs terug naar 0.
    # Dit is bedoeld voor onze eerste testwedstrijd.
    connection.execute("""
        UPDATE competition
        SET
            gespeeld = 0,
            gewonnen = 0,
            gelijk = 0,
            verloren = 0,
            doelpunten_voor = 0,
            doelpunten_tegen = 0,
            punten = 0
        WHERE club_id IN (?, ?)
    """, (
        wedstrijd["home_club_id"],
        wedstrijd["away_club_id"]
    ))

    connection.commit()

    print("Eerste wedstrijd is succesvol gereset.")
    print("Score: 0 - 0")
    print("Status: nog niet gespeeld")

connection.close()