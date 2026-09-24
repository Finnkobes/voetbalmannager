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


# =========================
# DATABASE VERBINDING
# =========================

def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# =========================
# CLUBS
# =========================

def get_clubs():
    connection = get_connection()

    clubs = connection.execute("""
        SELECT id, naam, stad, rating, logo, budget
        FROM clubs
        ORDER BY rating DESC
    """).fetchall()

    connection.close()

    return clubs


# =========================
# SPELERS
# =========================

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


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# CLUB KIEZEN
# =========================

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
        SELECT id, naam, stad, rating, logo, budget
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
        "rating": club["rating"],
        "logo": club["logo"],
        "budget": club["budget"]
    }

    return render_template(
        "dashboard.html",
        club=session["club"]
    )


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():
    club = session.get("club")

    return render_template(
        "dashboard.html",
        club=club
    )


# =========================
# SELECTIE
# =========================

@app.route("/selection")
def selection():
    club = session.get("club")

    if club is None:
        return render_template(
            "dashboard.html",
            club=None
        )

    positie_filter = request.args.get("positie", "alle")
    sorteer = request.args.get("sorteer", "rating_desc")

    connection = get_connection()

    query = """
    SELECT
        id,
        naam,
        positie,
        leeftijd,
        marktwaarde,
        rating,
        salaris,
        contractduur
    FROM players
    WHERE club_id = ?
"""
    parameters = [club["id"]]

    if positie_filter != "alle":
        query += " AND positie = ?"
        parameters.append(positie_filter)

    if sorteer == "rating_desc":
        query += " ORDER BY rating DESC"

    elif sorteer == "rating_asc":
        query += " ORDER BY rating ASC"

    elif sorteer == "waarde_desc":
        query += " ORDER BY marktwaarde DESC"

    elif sorteer == "waarde_asc":
        query += " ORDER BY marktwaarde ASC"

    elif sorteer == "leeftijd_asc":
        query += " ORDER BY leeftijd ASC"

    elif sorteer == "leeftijd_desc":
        query += " ORDER BY leeftijd DESC"

    spelers = connection.execute(
        query,
        parameters
    ).fetchall()

    connection.close()

    return render_template(
        "selection.html",
        club=club,
        players=spelers,
        positie_filter=positie_filter,
        sorteer=sorteer
    )


# =========================
# STATISTIEKEN
# =========================

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


# =========================
# TRANSFERMARKT
# =========================

@app.route("/transfers")
def transfers():
    club = session.get("club")

    if club is None:
        return render_template(
            "dashboard.html",
            club=None
        )

    connection = get_connection()

    spelers = connection.execute("""
        SELECT
            players.id,
            players.naam,
            players.positie,
            players.leeftijd,
            players.marktwaarde,
            players.rating,
            clubs.naam AS club_naam,
            clubs.logo AS club_logo
        FROM players
        JOIN clubs ON players.club_id = clubs.id
        WHERE players.club_id != ?
        ORDER BY RANDOM()
        LIMIT 9
    """, (club["id"],)).fetchall()

    connection.close()

    return render_template(
        "transfers.html",
        club=club,
        players=spelers
    )


# =========================
# SPELER BEKIJKEN
# =========================

@app.route("/player/<int:player_id>")
def player_detail(player_id):
    club = session.get("club")

    if club is None:
        return render_template(
            "dashboard.html",
            club=None
        )

    connection = get_connection()

    player = connection.execute("""
        SELECT
            players.id,
            players.naam,
            players.positie,
            players.leeftijd,
            players.marktwaarde,
            players.rating,
            clubs.naam AS club_naam,
            clubs.logo AS club_logo
        FROM players
        JOIN clubs ON players.club_id = clubs.id
        WHERE players.id = ?
    """, (player_id,)).fetchone()

    connection.close()

    if player is None:
        return "Speler niet gevonden", 404

    return render_template(
        "player.html",
        club=club,
        player=player
    )


# =========================
# TACTIEKEN
# =========================

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


# =========================
# OPSTELLING
# =========================

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


# =========================
# BROWSER AUTOMATISCH OPENEN
# =========================

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")


# =========================
# START FLASK
# =========================

if __name__ == "__main__":
    Timer(1, open_browser).start()

    app.run(
        debug=True,
        use_reloader=False
    )