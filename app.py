try:
    from flask import (  # type: ignore[reportMissingImports]
        Flask,
        render_template,
        session,
        request,
        redirect,
        url_for,
        jsonify,
    )
except ImportError as exc:
    raise RuntimeError(
        "Flask is required to run this application. Install dependencies first."
    ) from exc


import sqlite3
import webbrowser
import random
import time
import math

from threading import Timer
from pathlib import Path
from datetime import datetime, date, timedelta


app = Flask(__name__)

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
# COMPETITIE DATABASE
# =========================

def create_competition_table():
    connection = get_connection()

    connection.execute("""
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

    clubs = connection.execute("""
        SELECT id
        FROM clubs
    """).fetchall()

    for club in clubs:
        connection.execute("""
            INSERT OR IGNORE INTO competition (club_id)
            VALUES (?)
        """, (club["id"],))

    connection.commit()
    connection.close()


# =========================
# CLUBS
# =========================

def get_clubs():
    connection = get_connection()

    clubs = connection.execute("""
        SELECT
            id,
            naam,
            stad,
            rating,
            logo,
            budget
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
        ORDER BY rating DESC
    """, (club_id,)).fetchall()

    connection.close()

    return players


# =========================
# WEDSTRIJD BESCHIKBAARHEID
# =========================

def get_eerste_wedstrijddatum():
    connection = get_connection()

    wedstrijd = connection.execute("""
        SELECT datum
        FROM matches
        ORDER BY speelronde ASC, id ASC
        LIMIT 1
    """).fetchone()

    connection.close()

    if wedstrijd is None:
        return None

    return wedstrijd["datum"]


def wedstrijd_beschikbaar(datum):
    if not datum:
        return False

    # TEST:
    # De eerste speeldag mag direct gespeeld worden.
    eerste_datum = get_eerste_wedstrijddatum()

    if datum == eerste_datum:
        return True

    nu = datetime.now()

    wedstrijd_datum = datetime.strptime(
        datum,
        "%Y-%m-%d"
    )

    wedstrijd_datum = wedstrijd_datum.replace(
        hour=19,
        minute=0,
        second=0,
        microsecond=0
    )

    return nu >= wedstrijd_datum


# =========================
# MATCHES DATABASE
# =========================

def create_matches_table():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_club_id INTEGER NOT NULL,
            away_club_id INTEGER NOT NULL,
            home_score INTEGER NOT NULL DEFAULT 0,
            away_score INTEGER NOT NULL DEFAULT 0,
            gespeeld INTEGER NOT NULL DEFAULT 0,
            speelronde INTEGER NOT NULL DEFAULT 1,
            datum TEXT,
            FOREIGN KEY (home_club_id) REFERENCES clubs(id),
            FOREIGN KEY (away_club_id) REFERENCES clubs(id)
        )
    """)

    columns = connection.execute("""
        PRAGMA table_info(matches)
    """).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    if "speelronde" not in column_names:
        connection.execute("""
            ALTER TABLE matches
            ADD COLUMN speelronde INTEGER NOT NULL DEFAULT 1
        """)

    if "datum" not in column_names:
        connection.execute("""
            ALTER TABLE matches
            ADD COLUMN datum TEXT
        """)

    connection.commit()
    connection.close()


# =========================
# WEDSTRIJDEN GENEREREN
# =========================

def generate_matches():

    connection = get_connection()

    clubs = connection.execute("""
        SELECT id
        FROM clubs
        ORDER BY id
    """).fetchall()

    if len(clubs) < 2:
        connection.close()
        return

    bestaande = connection.execute("""
        SELECT COUNT(*) AS aantal
        FROM matches
    """).fetchone()["aantal"]

    gespeelde = connection.execute("""
        SELECT COUNT(*) AS aantal
        FROM matches
        WHERE gespeeld = 1
    """).fetchone()["aantal"]

    if bestaande > 0 and gespeelde == 0:

        connection.execute("""
            DELETE FROM matches
        """)

        connection.commit()

    elif bestaande > 0:

        connection.close()
        return

    club_ids = [
        club["id"]
        for club in clubs
    ]

    # Bij een oneven aantal clubs
    # krijgt één club een vrije ronde.
    if len(club_ids) % 2 != 0:
        club_ids.append(None)

    aantal_clubs = len(club_ids)

    aantal_rondes = (
        aantal_clubs - 1
    )

    helft = (
        aantal_clubs // 2
    )

    startdatum = date.today()

    # Eerstvolgende zaterdag.
    while startdatum.weekday() != 5:
        startdatum += timedelta(
            days=1
        )

    eerste_helft = []

    volgorde = club_ids[:]

    for ronde in range(
        1,
        aantal_rondes + 1
    ):

        wedstrijden_ronde = []

        for i in range(helft):

            thuis = volgorde[i]

            uit = volgorde[
                aantal_clubs - 1 - i
            ]

            if thuis is None or uit is None:
                continue

            if ronde % 2 == 0:
                thuis, uit = uit, thuis

            wedstrijden_ronde.append(
                (thuis, uit)
            )

        eerste_helft.append(
            wedstrijden_ronde
        )

        volgorde = (
            [volgorde[0]]
            + [volgorde[-1]]
            + volgorde[1:-1]
        )

    tweede_helft = []

    for wedstrijden in eerste_helft:

        return_wedstrijden = []

        for thuis, uit in wedstrijden:

            return_wedstrijden.append(
                (uit, thuis)
            )

        tweede_helft.append(
            return_wedstrijden
        )

    alle_rondes = (
        eerste_helft
        +
        tweede_helft
    )

    for index, wedstrijden in enumerate(
        alle_rondes
    ):

        speelronde = index + 1

        datum = (
            startdatum
            +
            timedelta(weeks=index)
        )

        for thuis, uit in wedstrijden:

            connection.execute("""
                INSERT INTO matches (
                    home_club_id,
                    away_club_id,
                    home_score,
                    away_score,
                    gespeeld,
                    speelronde,
                    datum
                )
                VALUES (?, ?, 0, 0, 0, ?, ?)
            """, (
                thuis,
                uit,
                speelronde,
                datum.isoformat()
            ))

    connection.commit()
    connection.close()


# =========================
# OUDE WEDSTRIJD SCORE
# =========================

def bereken_wedstrijdscore(
    home_rating,
    away_rating
):

    thuissterkte = (
        home_rating + 3
    )

    uitsterkte = away_rating

    totaal = (
        thuissterkte
        +
        uitsterkte
    )

    if totaal <= 0:
        totaal = 1

    thuis_kans = (
        thuissterkte / totaal
    )

    home_score = random.choices(
        [0, 1, 2, 3, 4],
        weights=[
            18,
            35,
            30,
            13,
            4
        ]
    )[0]

    away_score = random.choices(
        [0, 1, 2, 3, 4],
        weights=[
            22,
            36,
            27,
            11,
            4
        ]
    )[0]

    verschil = (
        home_rating
        -
        away_rating
    )

    if verschil > 5:

        if random.random() < 0.35:
            home_score += 1

    elif verschil < -5:

        if random.random() < 0.35:
            away_score += 1

    if random.random() < (
        thuis_kans * 0.20
    ):
        home_score += 1

    home_score = min(
        home_score,
        6
    )

    away_score = min(
        away_score,
        6
    )

    return (
        home_score,
        away_score
    )


# =========================
# COMPETITIE BIJWERKEN
# =========================

def update_competition(
    home_club_id,
    away_club_id,
    home_score,
    away_score
):

    connection = get_connection()

    if home_score > away_score:

        home_result = "gewonnen"
        away_result = "verloren"

        home_points = 3
        away_points = 0

    elif home_score < away_score:

        home_result = "verloren"
        away_result = "gewonnen"

        home_points = 0
        away_points = 3

    else:

        home_result = "gelijk"
        away_result = "gelijk"

        home_points = 1
        away_points = 1

    connection.execute("""
        UPDATE competition
        SET
            gespeeld = gespeeld + 1,
            gewonnen = gewonnen + ?,
            gelijk = gelijk + ?,
            verloren = verloren + ?,
            doelpunten_voor =
                doelpunten_voor + ?,
            doelpunten_tegen =
                doelpunten_tegen + ?,
            punten =
                punten + ?
        WHERE club_id = ?
    """, (
        1 if home_result == "gewonnen" else 0,
        1 if home_result == "gelijk" else 0,
        1 if home_result == "verloren" else 0,
        home_score,
        away_score,
        home_points,
        home_club_id
    ))

    connection.execute("""
        UPDATE competition
        SET
            gespeeld = gespeeld + 1,
            gewonnen = gewonnen + ?,
            gelijk = gelijk + ?,
            verloren = verloren + ?,
            doelpunten_voor =
                doelpunten_voor + ?,
            doelpunten_tegen =
                doelpunten_tegen + ?,
            punten =
                punten + ?
        WHERE club_id = ?
    """, (
        1 if away_result == "gewonnen" else 0,
        1 if away_result == "gelijk" else 0,
        1 if away_result == "verloren" else 0,
        away_score,
        home_score,
        away_points,
        away_club_id
    ))

    connection.commit()
    connection.close()


# =========================
# LIVE WEDSTRIJD HELPERS
# =========================

def kies_live_speler(
    spelers,
    voorkeur=None
):

    if not spelers:

        return {
            "naam": "Onbekende speler",
            "positie": ""
        }

    if voorkeur == "keeper":

        kandidaten = [
            speler
            for speler in spelers
            if speler["positie"] in [
                "K",
                "GK",
                "Keeper",
                "Doelman"
            ]
        ]

    elif voorkeur == "verdediging":

        kandidaten = [
            speler
            for speler in spelers
            if speler["positie"] in [
                "V",
                "VD",
                "Verdediger",
                "Verdediging"
            ]
        ]

    elif voorkeur == "middenveld":

        kandidaten = [
            speler
            for speler in spelers
            if speler["positie"] in [
                "M",
                "MV",
                "Middenveld",
                "Middenvelder"
            ]
        ]

    elif voorkeur == "aanval":

        kandidaten = [
            speler
            for speler in spelers
            if speler["positie"] in [
                "A",
                "AV",
                "Aanvaller",
                "Spits"
            ]
        ]

    else:

        kandidaten = spelers

    if not kandidaten:
        kandidaten = spelers

    return random.choice(
        kandidaten
    )


def poisson_getal(
    gemiddelde
):

    gemiddelde = max(
        0.1,
        min(gemiddelde, 4.5)
    )

    grens = math.exp(
        -gemiddelde
    )

    product = 1.0
    aantal = 0

    while product > grens:

        aantal += 1

        product *= random.random()

    return max(
        0,
        aantal - 1
    )


def live_minuut_voor_secondes(
    at
):

    # 15 sec = eerste helft
    # 5 sec = rust
    # 15 sec = tweede helft

    EERSTE_HELFT = 15
    RUST = 5
    TWEEDE_HELFT_START = (
        EERSTE_HELFT + RUST
    )

    if at < EERSTE_HELFT:

        minuut = int(
            (
                at
                /
                EERSTE_HELFT
            )
            *
            45
        ) + 1

    elif at < TWEEDE_HELFT_START:

        minuut = 45

    else:

        tweede_helft_at = (
            at
            -
            TWEEDE_HELFT_START
        )

        minuut = (
            46
            +
            int(
                (
                    tweede_helft_at
                    /
                    15
                )
                *
                44
            )
        )

    return max(
        1,
        min(
            minuut,
            90
        )
    )


def maak_unieke_event_tijd(
    bestaande_tijden,
    tweede_helft=False
):

    # Eerste helft:
    # 0.8 t/m 14.0

    # Tweede helft:
    # 20.8 t/m 34.0

    if tweede_helft:

        minimum = 20.8
        maximum = 34.0

    else:

        minimum = 0.8
        maximum = 14.0

    for _ in range(200):

        tijd = round(
            random.uniform(
                minimum,
                maximum
            ),
            1
        )

        if all(
            abs(
                tijd - bestaand
            ) >= 1.2
            for bestaand in bestaande_tijden
        ):
            return tijd

    return round(
        random.uniform(
            minimum,
            maximum
        ),
        1
    )


def genereer_live_events(
    home_players,
    away_players,
    home_name,
    away_name,
    home_rating,
    away_rating
):

    events = []

    gebruikte_tijden = []

    kaarten_spelers = set()


    def voeg_event(
        type_,
        team,
        speler,
        titel,
        tekst,
        tweede_helft=None
    ):

        if tweede_helft is None:

            tweede_helft = (
                random.random()
                <
                0.48
            )

        tijd = maak_unieke_event_tijd(
            gebruikte_tijden,
            tweede_helft
        )

        gebruikte_tijden.append(
            tijd
        )

        events.append({

            "at":
                tijd,

            "minute":
                live_minuut_voor_secondes(
                    tijd
                ),

            "type":
                type_,

            "team":
                team,

            "player":
                speler["naam"],

            "title":
                titel,

            "text":
                tekst
        })


    # =========================
    # GOALS
    # =========================

    home_expected_goals = (
        1.00
        +
        (
            (
                home_rating
                -
                away_rating
            )
            *
            0.035
        )
    )

    away_expected_goals = (
        0.90
        +
        (
            (
                away_rating
                -
                home_rating
            )
            *
            0.035
        )
    )

    home_goals = min(
        poisson_getal(
            home_expected_goals
        ),
        4
    )

    away_goals = min(
        poisson_getal(
            away_expected_goals
        ),
        4
    )

    # Niet té vaak 0-0
    if (
        home_goals == 0
        and
        away_goals == 0
    ):

        if random.random() < 0.45:

            if random.random() < 0.5:
                home_goals = 1
            else:
                away_goals = 1


    for _ in range(home_goals):

        speler = kies_live_speler(
            home_players,
            "aanval"
        )

        voeg_event(
            "goal",
            "home",
            speler,
            f"GOAL! {home_name}",
            (
                f"{speler['naam']} "
                f"maakt er een doelpunt van."
            )
        )


    for _ in range(away_goals):

        speler = kies_live_speler(
            away_players,
            "aanval"
        )

        voeg_event(
            "goal",
            "away",
            speler,
            f"GOAL! {away_name}",
            (
                f"{speler['naam']} "
                f"maakt er een doelpunt van."
            )
        )


    # =========================
    # AANVALLEN
    # =========================

    for _ in range(5):

        team_home = (
            random.random()
            <
            (
                home_rating
                /
                (
                    home_rating
                    +
                    away_rating
                )
            )
        )

        if team_home:

            speler = kies_live_speler(
                home_players,
                "middenveld"
            )

            voeg_event(
                "attack",
                "home",
                speler,
                f"{home_name} valt aan",
                (
                    f"{speler['naam']} "
                    f"zet druk richting het doel."
                )
            )

        else:

            speler = kies_live_speler(
                away_players,
                "middenveld"
            )

            voeg_event(
                "attack",
                "away",
                speler,
                f"{away_name} valt aan",
                (
                    f"{speler['naam']} "
                    f"zoekt ruimte richting het doel."
                )
            )


    # =========================
    # KANSEN
    # =========================

    for _ in range(2):

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_players,
                "aanval"
            )

            voeg_event(
                "chance",
                "home",
                speler,
                f"Grote kans voor {home_name}",
                (
                    f"{speler['naam']} "
                    f"komt gevaarlijk voor het doel."
                )
            )

        else:

            speler = kies_live_speler(
                away_players,
                "aanval"
            )

            voeg_event(
                "chance",
                "away",
                speler,
                f"Grote kans voor {away_name}",
                (
                    f"{speler['naam']} "
                    f"komt gevaarlijk voor het doel."
                )
            )


    # =========================
    # SCHOTEN
    # =========================

    for _ in range(2):

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_players,
                "aanval"
            )

            voeg_event(
                "shot",
                "home",
                speler,
                f"Schot van {home_name}",
                (
                    f"{speler['naam']} "
                    f"haalt uit."
                )
            )

        else:

            speler = kies_live_speler(
                away_players,
                "aanval"
            )

            voeg_event(
                "shot",
                "away",
                speler,
                f"Schot van {away_name}",
                (
                    f"{speler['naam']} "
                    f"haalt uit."
                )
            )


    # =========================
    # CORNERS
    # =========================

    for _ in range(2):

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_players
            )

            voeg_event(
                "corner",
                "home",
                speler,
                f"Corner voor {home_name}",
                (
                    f"{speler['naam']} "
                    f"neemt de corner."
                )
            )

        else:

            speler = kies_live_speler(
                away_players
            )

            voeg_event(
                "corner",
                "away",
                speler,
                f"Corner voor {away_name}",
                (
                    f"{speler['naam']} "
                    f"neemt de corner."
                )
            )


    # =========================
    # REDDING
    # =========================

    if random.random() < 0.8:

        if random.random() < 0.5:

            keeper = kies_live_speler(
                home_players,
                "keeper"
            )

            schutter = kies_live_speler(
                away_players,
                "aanval"
            )

            voeg_event(
                "save",
                "home",
                keeper,
                f"Sterke redding van {home_name}",
                (
                    f"{keeper['naam']} "
                    f"stopt het schot van "
                    f"{schutter['naam']}."
                )
            )

        else:

            keeper = kies_live_speler(
                away_players,
                "keeper"
            )

            schutter = kies_live_speler(
                home_players,
                "aanval"
            )

            voeg_event(
                "save",
                "away",
                keeper,
                f"Sterke redding van {away_name}",
                (
                    f"{keeper['naam']} "
                    f"stopt het schot van "
                    f"{schutter['naam']}."
                )
            )


    # =========================
    # KAARTEN
    # =========================

    aantal_kaarten = random.randint(
        1,
        3
    )

    kaart_pogingen = 0

    while (
        len(kaarten_spelers)
        <
        aantal_kaarten
        and
        kaart_pogingen
        <
        50
    ):

        kaart_pogingen += 1

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_players,
                "verdediging"
            )

            team = "home"

        else:

            speler = kies_live_speler(
                away_players,
                "verdediging"
            )

            team = "away"


        speler_key = (
            team,
            speler["naam"]
        )

        if speler_key in kaarten_spelers:
            continue

        kaarten_spelers.add(
            speler_key
        )


        if random.random() < 0.12:

            kaart_type = "red"

            titel = (
                "Rode kaart"
            )

            tekst = (
                f"{speler['naam']} "
                f"krijgt rood en moet "
                f"het veld verlaten."
            )

        else:

            kaart_type = "yellow"

            titel = (
                "Gele kaart"
            )

            tekst = (
                f"{speler['naam']} "
                f"krijgt geel na een "
                f"overtreding."
            )


        voeg_event(
            kaart_type,
            team,
            speler,
            titel,
            tekst
        )


    # =========================
    # WISSELS
    # =========================

    for team, spelers, teamnaam in [
        (
            "home",
            home_players,
            home_name
        ),
        (
            "away",
            away_players,
            away_name
        )
    ]:

        if len(spelers) >= 4:

            veldspelers = [
                speler
                for speler in spelers
                if speler["positie"]
                not in [
                    "K",
                    "GK",
                    "Keeper",
                    "Doelman"
                ]
            ]

            if len(veldspelers) >= 2:

                eruit, erin = random.sample(
                    veldspelers,
                    2
                )

                voeg_event(
                    "substitution",
                    team,
                    erin,
                    f"Wissel {teamnaam}",
                    (
                        f"{erin['naam']} "
                        f"komt erin voor "
                        f"{eruit['naam']}."
                    ),
                    tweede_helft=True
                )


    # =========================
    # BLESSURE
    # =========================

    if random.random() < 0.35:

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_players
            )

            voeg_event(
                "injury",
                "home",
                speler,
                f"Blessure bij {home_name}",
                (
                    f"{speler['naam']} "
                    f"heeft verzorging nodig."
                )
            )

        else:

            speler = kies_live_speler(
                away_players
            )

            voeg_event(
                "injury",
                "away",
                speler,
                f"Blessure bij {away_name}",
                (
                    f"{speler['naam']} "
                    f"heeft verzorging nodig."
                )
            )


    # =========================
    # BUITENSPEL
    # =========================

    if random.random() < 0.55:

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_players,
                "aanval"
            )

            voeg_event(
                "offside",
                "home",
                speler,
                "Buitenspel",
                (
                    f"{speler['naam']} "
                    f"staat buitenspel."
                )
            )

        else:

            speler = kies_live_speler(
                away_players,
                "aanval"
            )

            voeg_event(
                "offside",
                "away",
                speler,
                "Buitenspel",
                (
                    f"{speler['naam']} "
                    f"staat buitenspel."
                )
            )


    # =========================
    # EVENTS SORTEREN
    # =========================

    events.sort(
        key=lambda event: event["at"]
    )

    return events


# =========================
# HOME
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


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


@app.route(
    "/choose/<club_name>"
)
def choose_club(
    club_name
):

    connection = get_connection()

    club = connection.execute("""
        SELECT
            id,
            naam,
            stad,
            rating,
            logo,
            budget
        FROM clubs
        WHERE naam = ?
    """, (
        club_name,
    )).fetchone()

    connection.close()

    if club is None:
        return "Club niet gevonden", 404

    session.clear()

    session["club"] = {
        "id":
            club["id"],

        "naam":
            club["naam"],

        "stad":
            club["stad"],

        "rating":
            club["rating"],

        "logo":
            club["logo"],

        "budget":
            club["budget"]
    }

    return redirect(
        url_for("dashboard")
    )


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    club = session.get(
        "club"
    )

    if club is None:

        return render_template(
            "dashboard.html",
            club=None
        )

    connection = get_connection()

    standings = connection.execute("""
        SELECT
            clubs.id,
            clubs.naam,
            competition.gespeeld,
            competition.gewonnen,
            competition.gelijk,
            competition.verloren,
            competition.doelpunten_voor,
            competition.doelpunten_tegen,
            (
                competition.doelpunten_voor
                -
                competition.doelpunten_tegen
            ) AS doelsaldo,
            competition.punten
        FROM competition
        JOIN clubs
            ON competition.club_id = clubs.id
        ORDER BY
            competition.punten DESC,
            doelsaldo DESC,
            competition.doelpunten_voor DESC,
            clubs.naam ASC
    """).fetchall()

    eigen_team = next(
        (
            team
            for team in standings
            if team["id"] == club["id"]
        ),
        None
    )

    positie = next(
        (
            index + 1
            for index, team in enumerate(
                standings
            )
            if team["id"] == club["id"]
        ),
        "-"
    )

    connection.close()

    return render_template(
        "dashboard.html",
        club=club,
        competitie=eigen_team,
        positie=positie
    )


# =========================
# SELECTIE
# =========================

@app.route("/selection")
def selection():

    club = session.get(
        "club"
    )

    if club is None:

        return render_template(
            "dashboard.html",
            club=None
        )

    positie_filter = request.args.get(
        "positie",
        "alle"
    )

    sorteer = request.args.get(
        "sorteer",
        "rating_desc"
    )

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

    parameters = [
        club["id"]
    ]

    if positie_filter != "alle":

        query += """
            AND positie = ?
        """

        parameters.append(
            positie_filter
        )

    if sorteer == "rating_desc":

        query += """
            ORDER BY rating DESC
        """

    elif sorteer == "rating_asc":

        query += """
            ORDER BY rating ASC
        """

    elif sorteer == "waarde_desc":

        query += """
            ORDER BY marktwaarde DESC
        """

    elif sorteer == "waarde_asc":

        query += """
            ORDER BY marktwaarde ASC
        """

    elif sorteer == "leeftijd_asc":

        query += """
            ORDER BY leeftijd ASC
        """

    elif sorteer == "leeftijd_desc":

        query += """
            ORDER BY leeftijd DESC
        """

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

    club = session.get(
        "club"
    )

    if club is None:

        return render_template(
            "dashboard.html",
            club=None
        )

    connection = get_connection()

    spelers = connection.execute("""
        SELECT
            naam,
            positie,
            leeftijd,
            marktwaarde,
            rating
        FROM players
        WHERE club_id = ?
        ORDER BY rating DESC
    """, (
        club["id"],
    )).fetchall()

    totaal_spelers = len(
        spelers
    )

    gemiddelde_rating = (
        round(
            sum(
                player["rating"]
                for player in spelers
            )
            /
            totaal_spelers,
            1
        )
        if totaal_spelers > 0
        else 0
    )

    totale_waarde = sum(
        player["marktwaarde"]
        for player in spelers
    )

    hoogste_rating = (
        spelers[0]
        if spelers
        else None
    )

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
# COMPETITIE
# =========================

@app.route("/competition")
def competition():

    club = session.get(
        "club"
    )

    if club is None:

        return render_template(
            "dashboard.html",
            club=None
        )

    connection = get_connection()

    standings = connection.execute("""
        SELECT
            clubs.id,
            clubs.naam,
            clubs.logo,
            clubs.rating,
            competition.gespeeld,
            competition.gewonnen,
            competition.gelijk,
            competition.verloren,
            competition.doelpunten_voor,
            competition.doelpunten_tegen,
            (
                competition.doelpunten_voor
                -
                competition.doelpunten_tegen
            ) AS doelsaldo,
            competition.punten
        FROM competition
        JOIN clubs
            ON competition.club_id = clubs.id
        ORDER BY
            competition.punten DESC,
            doelsaldo DESC,
            competition.doelpunten_voor DESC,
            clubs.naam ASC
    """).fetchall()

    connection.close()

    return render_template(
        "competition.html",
        club=club,
        standings=standings
    )


# =========================
# WEDSTRIJDEN
# =========================

@app.route("/matches")
def matches():

    club = session.get(
        "club"
    )

    if club is None:

        return render_template(
            "dashboard.html",
            club=None
        )

    connection = get_connection()

    matches = connection.execute("""
        SELECT
            matches.id,
            home.naam AS home_naam,
            home.logo AS home_logo,
            away.naam AS away_naam,
            away.logo AS away_logo,
            matches.home_score,
            matches.away_score,
            matches.gespeeld,
            matches.speelronde,
            matches.datum
        FROM matches
        JOIN clubs AS home
            ON matches.home_club_id = home.id
        JOIN clubs AS away
            ON matches.away_club_id = away.id
        ORDER BY
            matches.speelronde,
            matches.id
    """).fetchall()

    connection.close()

    wedstrijden = []

    for match in matches:

        wedstrijd = dict(
            match
        )

        wedstrijd["beschikbaar"] = (
            wedstrijd_beschikbaar(
                wedstrijd["datum"]
            )
        )

        wedstrijden.append(
            wedstrijd
        )

    return render_template(
        "matches.html",
        club=club,
        matches=wedstrijden
    )


# =========================
# LIVE WEDSTRIJD STARTEN
# =========================

@app.route(
    "/play_match/<int:match_id>"
)
def play_match(
    match_id
):

    club = session.get(
        "club"
    )

    if club is None:

        return redirect(
            url_for("clubs_page")
        )

    connection = get_connection()

    match = connection.execute("""
        SELECT
            matches.id,
            matches.home_club_id,
            matches.away_club_id,
            matches.home_score,
            matches.away_score,
            matches.gespeeld,
            matches.speelronde,
            matches.datum,

            home.naam AS home_naam,
            home.logo AS home_logo,
            home.rating AS home_rating,

            away.naam AS away_naam,
            away.logo AS away_logo,
            away.rating AS away_rating

        FROM matches

        JOIN clubs AS home
            ON matches.home_club_id = home.id

        JOIN clubs AS away
            ON matches.away_club_id = away.id

        WHERE matches.id = ?
    """, (
        match_id,
    )).fetchone()

    if match is None:

        connection.close()

        return "Wedstrijd niet gevonden", 404

    if match["gespeeld"]:

        connection.close()

        return redirect(
            url_for("matches")
        )

    if not wedstrijd_beschikbaar(
        match["datum"]
    ):

        connection.close()

        return redirect(
            url_for("matches")
        )

    if club["id"] not in [
        match["home_club_id"],
        match["away_club_id"]
    ]:

        connection.close()

        return redirect(
            url_for("matches")
        )

    connection.close()


    # =========================
    # BESTAANDE LIVE WEDSTRIJD
    # =========================

    bestaande_live = session.get(
        "live_match"
    )


    if (
        bestaande_live is None
        or
        bestaande_live.get(
            "match_id"
        ) != match_id
    ):

        home_players = (
            get_players_for_club(
                match["home_club_id"]
            )
        )

        away_players = (
            get_players_for_club(
                match["away_club_id"]
            )
        )


        events = genereer_live_events(
            home_players,
            away_players,
            match["home_naam"],
            match["away_naam"],
            match["home_rating"],
            match["away_rating"]
        )


        bestaande_live = {

            "match_id":
                match_id,

            "started_at":
                time.time(),

            "home": {

                "name":
                    match["home_naam"],

                "logo":
                    match["home_logo"],

                "rating":
                    match["home_rating"]
            },

            "away": {

                "name":
                    match["away_naam"],

                "logo":
                    match["away_logo"],

                "rating":
                    match["away_rating"]
            },

            "events":
                events
        }


        session["live_match"] = (
            bestaande_live
        )


    return render_template(
        "live_match.html",
        club=club,
        live_match=bestaande_live
    )


# =========================
# LIVE WEDSTRIJD OPSLAAN
# =========================

@app.route(
    "/play_match/<int:match_id>/finish",
    methods=["POST"]
)
def finish_played_match(
    match_id
):

    live_match = session.get(
        "live_match"
    )


    if (
        live_match is None
        or
        live_match.get(
            "match_id"
        ) != match_id
    ):

        return jsonify({
            "success":
                False,

            "error":
                "Geen actieve live wedstrijd."
        }), 400


    connection = get_connection()


    match = connection.execute("""
        SELECT
            id,
            home_club_id,
            away_club_id,
            home_score,
            away_score,
            gespeeld,
            speelronde,
            datum
        FROM matches
        WHERE id = ?
    """, (
        match_id,
    )).fetchone()


    if match is None:

        connection.close()

        return jsonify({
            "success":
                False,

            "error":
                "Wedstrijd niet gevonden."
        }), 404


    if match["gespeeld"]:

        connection.close()

        session.pop(
            "live_match",
            None
        )

        return jsonify({
            "success":
                True,

            "redirect":
                url_for("matches")
        })


    # =========================
    # SCORE BEREKENEN
    # =========================

    home_score = 0
    away_score = 0


    for event in (
        live_match["events"]
    ):

        if event["type"] != "goal":
            continue

        if event["team"] == "home":
            home_score += 1

        else:
            away_score += 1


    home_score = min(
        home_score,
        10
    )

    away_score = min(
        away_score,
        10
    )


    # =========================
    # WEDSTRIJD OPSLAAN
    # =========================

    connection.execute("""
        UPDATE matches
        SET
            home_score = ?,
            away_score = ?,
            gespeeld = 1
        WHERE id = ?
    """, (
        home_score,
        away_score,
        match_id
    ))


    connection.commit()

    connection.close()


    # =========================
    # COMPETITIE BIJWERKEN
    # =========================

    update_competition(
        match["home_club_id"],
        match["away_club_id"],
        home_score,
        away_score
    )


    session.pop(
        "live_match",
        None
    )


    return jsonify({

        "success":
            True,

        "home_score":
            home_score,

        "away_score":
            away_score,

        "redirect":
            url_for("matches")
    })


# =========================
# TRANSFERMARKT
# =========================

@app.route("/transfers")
def transfers():

    club = session.get(
        "club"
    )

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
        JOIN clubs
            ON players.club_id = clubs.id
        WHERE players.club_id != ?
        ORDER BY RANDOM()
        LIMIT 9
    """, (
        club["id"],
    )).fetchall()

    connection.close()

    return render_template(
        "transfers.html",
        club=club,
        players=spelers
    )


# =========================
# SPELER BEKIJKEN
# =========================

@app.route(
    "/player/<int:player_id>"
)
def player_detail(
    player_id
):

    club = session.get(
        "club"
    )

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
        JOIN clubs
            ON players.club_id = clubs.id
        WHERE players.id = ?
    """, (
        player_id,
    )).fetchone()

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

@app.route(
    "/tactics",
    methods=["GET", "POST"]
)
def tactics():

    club = session.get(
        "club"
    )

    if club is None:

        return render_template(
            "dashboard.html",
            club=None
        )


    formaties = [
        "4-3-3",
        "4-4-2",
        "4-2-3-1",
        "3-5-2"
    ]


    speelstijlen = [
        "Gebalanceerd",
        "Aanvallend",
        "Verdedigend",
        "Counter"
    ]


    mentaliteiten = [
        "Voorzichtig",
        "Gebalanceerd",
        "Aanvallend"
    ]


    druk = [
        "Laag",
        "Normaal",
        "Hoog"
    ]


    if request.method == "POST":

        formatie = request.form.get(
            "formatie",
            "4-3-3"
        )

        speelstijl = request.form.get(
            "speelstijl",
            "Gebalanceerd"
        )

        mentaliteit = request.form.get(
            "mentaliteit",
            "Gebalanceerd"
        )

        druk_zetten = request.form.get(
            "druk",
            "Normaal"
        )


        if formatie not in formaties:
            formatie = "4-3-3"

        if speelstijl not in speelstijlen:
            speelstijl = "Gebalanceerd"

        if mentaliteit not in mentaliteiten:
            mentaliteit = "Gebalanceerd"

        if druk_zetten not in druk:
            druk_zetten = "Normaal"


        session["tactieken"] = {

            "formatie":
                formatie,

            "speelstijl":
                speelstijl,

            "mentaliteit":
                mentaliteit,

            "druk":
                druk_zetten
        }


        return redirect(
            url_for("tactics")
        )


    tactieken = session.get(
        "tactieken",
        {

            "formatie":
                "4-3-3",

            "speelstijl":
                "Gebalanceerd",

            "mentaliteit":
                "Gebalanceerd",

            "druk":
                "Normaal"
        }
    )


    return render_template(
        "tactics.html",
        club=club,
        formations=formaties,
        speelstijlen=speelstijlen,
        mentaliteiten=mentaliteiten,
        druk=druk,
        tactieken=tactieken
    )


# =========================
# OPSTELLING
# =========================

@app.route(
    "/lineup",
    methods=["GET", "POST"]
)
def lineup():

    club = session.get(
        "club"
    )

    if club is None:

        return render_template(
            "dashboard.html",
            club=None
        )


    spelers = get_players_for_club(
        club["id"]
    )


    if request.method == "POST":

        opstelling = {

            "keeper":
                request.form.get(
                    "keeper"
                ),

            "verdediger_1":
                request.form.get(
                    "verdediger_1"
                ),

            "verdediger_2":
                request.form.get(
                    "verdediger_2"
                ),

            "verdediger_3":
                request.form.get(
                    "verdediger_3"
                ),

            "verdediger_4":
                request.form.get(
                    "verdediger_4"
                ),

            "middenvelder_1":
                request.form.get(
                    "middenvelder_1"
                ),

            "middenvelder_2":
                request.form.get(
                    "middenvelder_2"
                ),

            "middenvelder_3":
                request.form.get(
                    "middenvelder_3"
                ),

            "aanvaller_1":
                request.form.get(
                    "aanvaller_1"
                ),

            "aanvaller_2":
                request.form.get(
                    "aanvaller_2"
                ),

            "aanvaller_3":
                request.form.get(
                    "aanvaller_3"
                )
        }


        session["opstelling"] = (
            opstelling
        )


        return redirect(
            url_for("lineup")
        )


    opstelling = session.get(
        "opstelling",
        {

            "keeper":
                "",

            "verdediger_1":
                "",

            "verdediger_2":
                "",

            "verdediger_3":
                "",

            "verdediger_4":
                "",

            "middenvelder_1":
                "",

            "middenvelder_2":
                "",

            "middenvelder_3":
                "",

            "aanvaller_1":
                "",

            "aanvaller_2":
                "",

            "aanvaller_3":
                ""
        }
    )


    return render_template(
        "lineup.html",
        club=club,
        players=spelers,
        opstelling=opstelling
    )


# =========================
# BROWSER AUTOMATISCH OPENEN
# =========================

def open_browser():

    webbrowser.open_new(
        "http://127.0.0.1:5000"
    )


# =========================
# START FLASK
# =========================

if __name__ == "__main__":

    create_competition_table()

    create_matches_table()

    generate_matches()


    Timer(
        1,
        open_browser
    ).start()


    app.run(
        debug=True,
        use_reloader=False
    )