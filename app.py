from flask import Flask, render_template, session
import json
import webbrowser
from threading import Timer
from pathlib import Path

app = Flask(__name__)

# Session sleutel
app.secret_key = "clubmaster-development-key"

# Projectmap bepalen
BASE_DIR = Path(__file__).resolve().parent

# Spelers laden
PLAYERS_FILE = BASE_DIR / "data" / "players.json"

with open(PLAYERS_FILE, "r", encoding="utf-8") as bestand:
    players_per_club = json.load(bestand)


# Clubs
clubs = [
    {
        "naam": "Ajax",
        "stad": "Amsterdam",
        "rating": 82
    },
    {
        "naam": "PSV",
        "stad": "Eindhoven",
        "rating": 81
    },
    {
        "naam": "Feyenoord",
        "stad": "Rotterdam",
        "rating": 80
    },
    {
        "naam": "FC Twente",
        "stad": "Enschede",
        "rating": 74
    },
    {
        "naam": "AZ",
        "stad": "Alkmaar",
        "rating": 73
    },
    {
        "naam": "FC Utrecht",
        "stad": "Utrecht",
        "rating": 70
    }
]


# -------------------------
# HOME
# -------------------------

@app.route("/")
def home():
    return render_template("index.html")


# -------------------------
# CLUB KIEZEN
# -------------------------

@app.route("/clubs")
def clubs_page():
    return render_template(
        "clubs.html",
        clubs=clubs
    )


@app.route("/choose/<club_name>")
def choose_club(club_name):

    # Zoek de gekozen club
    gekozen_club = None

    for club in clubs:
        if club["naam"] == club_name:
            gekozen_club = club
            break

    # Bestaat de club niet?
    if gekozen_club is None:
        return "Club niet gevonden", 404

    # Oude club volledig vervangen
    session.clear()

    # Nieuwe club opslaan
    session["club"] = gekozen_club

    return render_template(
        "dashboard.html",
        club=gekozen_club
    )


# -------------------------
# DASHBOARD
# -------------------------

@app.route("/dashboard")
def dashboard():

    club = session.get("club")

    return render_template(
        "dashboard.html",
        club=club
    )


# -------------------------
# SELECTIE
# -------------------------

@app.route("/selection")
def selection():

    club = session.get("club")

    # Als er geen club gekozen is
    if club is None:
        return render_template(
            "dashboard.html",
            club=None
        )

    # Spelers van de gekozen club ophalen
    spelers = players_per_club.get(
        club["naam"],
        []
    )

    return render_template(
        "selection.html",
        club=club,
        players=spelers
    )


# -------------------------
# BROWSER AUTOMATISCH OPENEN
# -------------------------

def open_browser():
    webbrowser.open_new(
        "http://127.0.0.1:5000"
    )


# -------------------------
# START
# -------------------------

if __name__ == "__main__":
    Timer(1, open_browser).start()

    app.run(
        debug=True,
        use_reloader=False
    )