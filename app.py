
from flask import Flask, render_template, session, request
import sqlite3
import webbrowser
from threading import Timer
from pathlib import Path

app = Flask(__name__)

# Session sleutel
app.secret_key = "clubmaster-development-key"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database" / "football.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def get_clubs():
    connection = get_connection()

    clubs = connection.execute("""
        SELECT id, naam, stad, rating
        FROM clubs
        ORDER BY rating DESC
    """).fetchall()

    connection.close()

    return clubs


def get_players_for_club(club_id):
    connection = get_connection()

    players = connection.execute("""
        SELECT id, naam, positie, leeftijd, marktwaarde, rating
        FROM players
        WHERE club_id = ?
        ORDER BY rating DESC
    """, (club_id,)).fetchall()

    connection.close()

    return players


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/clubs")
def clubs_page():
    clubs = get_clubs()

    return render_template(
        "clubs.html",
        clubs=clubs
    )


@app.route("/choose/<club_name>")
def choose_club(club_name):
    connection = get_connection()

    club = connection.execute("""
        SELECT id, naam, stad, rating
        FROM clubs
        WHERE naam = ?
    """, (club_name,)).fetchone()

    connection.close()

    if club is None:
        return "Club niet gevonden", 404

    session.clear()

    session["club"] = {
        "id": club["id"],
        "naam": club["naam"],
        "stad": club["stad"],
        "rating": club["rating"]
    }

    return render_template(
        "dashboard.html",
        club=session["club"]
    )


@app.route("/dashboard")
def dashboard():
    club = session.get("club")

    return render_template(
        "dashboard.html",
        club=club
    )



@app.route("/selection")
def selection():
    club = session.get("club")

    if club is None:
        return render_template(
            "dashboard.html",
            club=None
        )
@app.route("/statistics")
def statistics():
    club = session.get("club")

    if club is None:
        return render_template(
            "dashboard.html",
            club=None
        )

    connection = get_connection()

    spelers = connection.execute("""
        SELECT naam, positie, leeftijd, marktwaarde, rating
        FROM players
        WHERE club_id = ?
        ORDER BY rating DESC
    """, (club["id"],)).fetchall()

    totaal_spelers = len(spelers)

    gemiddelde_rating = round(
        sum(player["rating"] for player in spelers) / totaal_spelers,
        1
    ) if totaal_spelers > 0 else 0

    totale_waarde = sum(
        player["marktwaarde"] for player in spelers
    )

    hoogste_rating = spelers[0] if spelers else None

    connection.close()

    return render_template(
        "statistics.html",
        club=club,
        players=spelers,
        totaal_spelers=totaal_spelers,
        gemiddelde_rating=gemiddelde_rating,
        totale_waarde=totale_waarde,
        hoogste_rating=hoogste_rating
    )
    

@app.route("/tactics")
def tactics():
    club = session.get("club")

    if club is None:
        return render_template(
            "dashboard.html",
            club=None
        )

    spelers = get_players_for_club(club["id"])

    formaties = [
        "4-3-3",
        "4-4-2",
        "4-2-3-1",
        "3-5-2"
    ]

    return render_template(
        "tactics.html",
        club=club,
        players=spelers,
        formations=formaties
    )


@app.route("/lineup")
def lineup():
    club = session.get("club")

    if club is None:
        return render_template(
            "dashboard.html",
            club=None
        )

    spelers = get_players_for_club(club["id"])

    return render_template(
        "lineup.html",
        club=club,
        players=spelers
    )


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")


if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)

