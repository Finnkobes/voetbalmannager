# pyright: reportMissingImports=false

try:
    from flask import (
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
        "Flask is required to run this application. "
        "Install dependencies first."
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
        """, (
            club["id"],
        ))

    connection.commit()
    connection.close()


# =========================
# STATISTIEKEN DATABASE
# =========================

def create_statistics_tables():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            player_id INTEGER NOT NULL,
            maand TEXT NOT NULL,
            wedstrijden INTEGER NOT NULL DEFAULT 0,
            doelpunten INTEGER NOT NULL DEFAULT 0,
            motm INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, maand)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS match_awards (
            match_id INTEGER PRIMARY KEY,
            player_id INTEGER,
            player_name TEXT,
            club_id INTEGER,
            club_name TEXT,
            datum TEXT
        )
    """)

    connection.execute("""
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
    """, (
        club_id,
    )).fetchall()

    connection.close()

    return players


# =========================
# POSITIE HERKENNEN
# =========================

def classificeer_positie(positie):

    positie = str(
        positie or ""
    ).strip().upper()

    if positie in [
        "K",
        "GK",
        "KEEPER",
        "DOELMAN"
    ]:
        return "keeper"

    if positie in [
        "V",
        "VD",
        "VERDEDIGER",
        "VERDEDIGING",
        "CB",
        "LB",
        "RB",
        "LWB",
        "RWB",
        "DF",
        "DC"
    ]:
        return "verdediging"

    if positie in [
        "M",
        "MV",
        "MIDDENVELD",
        "MIDDENVELDER",
        "CM",
        "CDM",
        "CAM",
        "LM",
        "RM",
        "DM",
        "AM"
    ]:
        return "middenveld"

    if positie in [
        "A",
        "AV",
        "AANVALLER",
        "SPITS",
        "ST",
        "CF",
        "LW",
        "RW",
        "LF",
        "RF"
    ]:
        return "aanval"

    return "overig"


# =========================
# PLAYER ROW NAAR DICT
# =========================

def speler_naar_dict(speler):

    if isinstance(speler, dict):
        return speler

    return {
        key: speler[key]
        for key in speler.keys()
    }


# =========================
# BASIS ELF BOUWEN
# =========================

def bouw_basiself(
    spelers,
    opgeslagen_opstelling=None
):

    spelers = [
        speler_naar_dict(speler)
        for speler in spelers
    ]

    opgeslagen_opstelling = (
        opgeslagen_opstelling or {}
    )

    slots = [

        (
            "keeper",
            "GK",
            "keeper"
        ),

        (
            "verdediger_1",
            "LB",
            "verdediging"
        ),

        (
            "verdediger_2",
            "CB",
            "verdediging"
        ),

        (
            "verdediger_3",
            "CB",
            "verdediging"
        ),

        (
            "verdediger_4",
            "RB",
            "verdediging"
        ),

        (
            "middenvelder_1",
            "CM",
            "middenveld"
        ),

        (
            "middenvelder_2",
            "CAM",
            "middenveld"
        ),

        (
            "middenvelder_3",
            "CM",
            "middenveld"
        ),

        (
            "aanvaller_1",
            "LW",
            "aanval"
        ),

        (
            "aanvaller_2",
            "SP",
            "aanval"
        ),

        (
            "aanvaller_3",
            "RW",
            "aanval"
        )
    ]

    gebruikte_ids = set()
    basiself = []

    # =========================
    # EERST OPGESLAGEN SPELERS
    # =========================

    for slot, label, groep in slots:

        opgeslagen_id = (
            opgeslagen_opstelling.get(
                slot
            )
        )

        gekozen = None

        if opgeslagen_id:

            try:
                opgeslagen_id = int(
                    opgeslagen_id
                )
            except (
                TypeError,
                ValueError
            ):
                opgeslagen_id = None

        if opgeslagen_id:

            for speler in spelers:

                speler_id = int(
                    speler["id"]
                )

                if (
                    speler_id == opgeslagen_id
                    and speler_id not in gebruikte_ids
                ):

                    gekozen = speler
                    break

        basiself.append({
            "slot": slot,
            "label": label,
            "player": gekozen
        })

        if gekozen:

            gebruikte_ids.add(
                int(gekozen["id"])
            )

    # =========================
    # MISSENDE POSITIES INVULLEN
    # =========================

    for positie in basiself:

        if positie["player"] is not None:
            continue

        geschikte_spelers = []

        for speler in spelers:

            speler_id = int(
                speler["id"]
            )

            if speler_id in gebruikte_ids:
                continue

            groep = classificeer_positie(
                speler["positie"]
            )

            if (
                positie["label"] == "GK"
                and
                groep == "keeper"
            ):
                geschikte_spelers.append(
                    speler
                )

            elif (
                positie["label"] in [
                    "LB",
                    "CB",
                    "RB"
                ]
                and
                groep == "verdediging"
            ):
                geschikte_spelers.append(
                    speler
                )

            elif (
                positie["label"] in [
                    "CM",
                    "CAM"
                ]
                and
                groep == "middenveld"
            ):
                geschikte_spelers.append(
                    speler
                )

            elif (
                positie["label"] in [
                    "LW",
                    "SP",
                    "RW"
                ]
                and
                groep == "aanval"
            ):
                geschikte_spelers.append(
                    speler
                )

        if geschikte_spelers:

            geschikte_spelers.sort(
                key=lambda speler: int(
                    speler["rating"]
                ),
                reverse=True
            )

            gekozen = geschikte_spelers[0]

        else:

            vrije_spelers = [
                speler
                for speler in spelers
                if int(speler["id"])
                not in gebruikte_ids
            ]

            if vrije_spelers:

                vrije_spelers.sort(
                    key=lambda speler: int(
                        speler["rating"]
                    ),
                    reverse=True
                )

                gekozen = vrije_spelers[0]

            else:

                gekozen = None

        positie["player"] = gekozen

        if gekozen:

            gebruikte_ids.add(
                int(gekozen["id"])
            )

    return basiself


# =========================
# VEILIGE TERUGKEER URL
# =========================

def geldige_interne_url(url):

    if not url:
        return None

    if not url.startswith("/"):
        return None

    if url.startswith("//"):
        return None

    return url


# =========================
# SPEELDAG / WEDSTRIJD BESCHIKBAARHEID
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

    eerste_datum = (
        get_eerste_wedstrijddatum()
    )

    # Eerste speeldag blijft
    # direct beschikbaar om te testen.
    if datum == eerste_datum:
        return True

    nu = datetime.now()

    wedstrijd_datum = datetime.strptime(
        datum,
        "%Y-%m-%d"
    )

    wedstrijd_datum = (
        wedstrijd_datum.replace(
            hour=19,
            minute=0,
            second=0,
            microsecond=0
        )
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

    if (
        bestaande > 0
        and
        gespeelde == 0
    ):

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

    if len(club_ids) % 2 != 0:
        club_ids.append(None)

    aantal_clubs = len(club_ids)
    aantal_rondes = aantal_clubs - 1
    helft = aantal_clubs // 2

    startdatum = date.today()

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

            if (
                thuis is None
                or
                uit is None
            ):
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
            +
            [volgorde[-1]]
            +
            volgorde[1:-1]
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
            timedelta(days=index)
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
                VALUES (
                    ?, ?, 0, 0, 0, ?, ?
                )
            """, (
                thuis,
                uit,
                speelronde,
                datum.isoformat()
            ))

    connection.commit()
    connection.close()


# =========================
# BESTAAND SCHEDULE DAGELIJKS
# =========================

def maak_bestaand_schema_dagelijks():

    connection = get_connection()

    rondes = connection.execute("""
        SELECT
            speelronde,
            MIN(datum) AS datum
        FROM matches
        GROUP BY speelronde
        ORDER BY speelronde ASC
    """).fetchall()

    if not rondes:

        connection.close()
        return

    eerste_datum = None

    try:

        eerste_datum = datetime.strptime(
            rondes[0]["datum"],
            "%Y-%m-%d"
        ).date()

    except (
        TypeError,
        ValueError
    ):

        eerste_datum = date.today()

    for index, ronde in enumerate(rondes):

        nieuwe_datum = (
            eerste_datum
            +
            timedelta(days=index)
        )

        connection.execute("""
            UPDATE matches
            SET datum = ?
            WHERE speelronde = ?
        """, (
            nieuwe_datum.isoformat(),
            ronde["speelronde"]
        ))

    connection.commit()
    connection.close()


# =========================
# OUDE SCORE FUNCTIE
# =========================

def bereken_wedstrijdscore(
    home_rating,
    away_rating
):

    thuissterkte = home_rating + 3
    uitsterkte = away_rating

    totaal = (
        thuissterkte
        +
        uitsterkte
    )

    if totaal <= 0:
        totaal = 1

    thuis_kans = (
        thuissterkte
        /
        totaal
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
# LIVE SPELER KIEZEN
# =========================

def kies_live_speler(
    spelers,
    voorkeur=None
):

    if not spelers:

        return {
            "naam": "Onbekende speler",
            "positie": "",
            "id": 0,
            "rating": 0
        }

    if voorkeur == "keeper":

        kandidaten = [
            speler
            for speler in spelers
            if classificeer_positie(
                speler["positie"]
            ) == "keeper"
        ]

    elif voorkeur == "verdediging":

        kandidaten = [
            speler
            for speler in spelers
            if classificeer_positie(
                speler["positie"]
            ) == "verdediging"
        ]

    elif voorkeur == "middenveld":

        kandidaten = [
            speler
            for speler in spelers
            if classificeer_positie(
                speler["positie"]
            ) == "middenveld"
        ]

    elif voorkeur == "aanval":

        kandidaten = [
            speler
            for speler in spelers
            if classificeer_positie(
                speler["positie"]
            ) == "aanval"
        ]

    else:

        kandidaten = spelers

    if not kandidaten:
        kandidaten = spelers

    return random.choice(
        kandidaten
    )


# =========================
# POISSON
# =========================

def poisson_getal(gemiddelde):

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


# =========================
# LIVE MINUUT
# =========================

def live_minuut_voor_secondes(at):

    eerste_helft = 15
    rust = 5

    tweede_helft_start = (
        eerste_helft
        +
        rust
    )

    if at < eerste_helft:

        minuut = int(
            (
                at
                /
                eerste_helft
            )
            *
            45
        ) + 1

    elif at < tweede_helft_start:

        minuut = 45

    else:

        tweede_helft_at = (
            at
            -
            tweede_helft_start
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


# =========================
# EVENT TIJD
# =========================

def maak_unieke_event_tijd(
    bestaande_tijden,
    tweede_helft=False
):

    if tweede_helft:

        minimum = 21.0
        maximum = 34.0

    else:

        minimum = 1.0
        maximum = 14.0

    for _ in range(300):

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
            ) >= 1.4
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


# =========================
# LIVE EVENTS
# =========================

def genereer_live_events(
    home_players,
    away_players,
    home_name,
    away_name,
    home_rating,
    away_rating,
    home_starting_lineup=None,
    away_starting_lineup=None
):

    events = []
    gebruikte_tijden = []
    kaarten_spelers = set()

    home_players = [
        speler_naar_dict(speler)
        for speler in home_players
    ]

    away_players = [
        speler_naar_dict(speler)
        for speler in away_players
    ]

    home_starting_players = [
        item["player"]
        for item in (
            home_starting_lineup or []
        )
        if item.get("player")
    ]

    away_starting_players = [
        item["player"]
        for item in (
            away_starting_lineup or []
        )
        if item.get("player")
    ]

    def voeg_event(
        type_,
        team,
        speler,
        titel,
        tekst,
        tweede_helft=False
    ):

        tijd = maak_unieke_event_tijd(
            gebruikte_tijden,
            tweede_helft
        )

        gebruikte_tijden.append(
            tijd
        )

        events.append({
            "at": tijd,
            "minute": live_minuut_voor_secondes(
                tijd
            ),
            "type": type_,
            "team": team,
            "player": speler["naam"],
            "title": titel,
            "text": tekst
        })

    # =========================
    # DOELPUNTEN
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
        3
    )

    away_goals = min(
        poisson_getal(
            away_expected_goals
        ),
        3
    )

    if (
        home_goals == 0
        and
        away_goals == 0
    ):

        if random.random() < 0.35:

            if random.random() < 0.5:
                home_goals = 1
            else:
                away_goals = 1

    # =========================
    # GOALS
    # =========================

    for _ in range(home_goals):

        bron = (
            home_starting_players
            or
            home_players
        )

        speler = kies_live_speler(
            bron,
            "aanval"
        )

        voeg_event(
            "goal",
            "home",
            speler,
            f"GOAL! {home_name}",
            f"{speler['naam']} schiet de bal binnen.",
            tweede_helft=(
                random.random() < 0.45
            )
        )

    for _ in range(away_goals):

        bron = (
            away_starting_players
            or
            away_players
        )

        speler = kies_live_speler(
            bron,
            "aanval"
        )

        voeg_event(
            "goal",
            "away",
            speler,
            f"GOAL! {away_name}",
            f"{speler['naam']} schiet de bal binnen.",
            tweede_helft=(
                random.random() < 0.45
            )
        )

    # =========================
    # AANVALLEN
    # =========================

    for _ in range(4):

        if random.random() < 0.5:

            bron = (
                home_starting_players
                or
                home_players
            )

            speler = kies_live_speler(
                bron,
                "middenveld"
            )

            voeg_event(
                "attack",
                "home",
                speler,
                f"{home_name} valt aan",
                f"{speler['naam']} dribbelt richting het doel."
            )

        else:

            bron = (
                away_starting_players
                or
                away_players
            )

            speler = kies_live_speler(
                bron,
                "middenveld"
            )

            voeg_event(
                "attack",
                "away",
                speler,
                f"{away_name} valt aan",
                f"{speler['naam']} zoekt de ruimte."
            )

    # =========================
    # KANSEN
    # =========================

    for _ in range(2):

        if random.random() < 0.5:

            bron = (
                home_starting_players
                or
                home_players
            )

            speler = kies_live_speler(
                bron,
                "aanval"
            )

            voeg_event(
                "chance",
                "home",
                speler,
                f"Grote kans voor {home_name}",
                f"{speler['naam']} komt gevaarlijk voor het doel."
            )

        else:

            bron = (
                away_starting_players
                or
                away_players
            )

            speler = kies_live_speler(
                bron,
                "aanval"
            )

            voeg_event(
                "chance",
                "away",
                speler,
                f"Grote kans voor {away_name}",
                f"{speler['naam']} komt gevaarlijk voor het doel."
            )

    # =========================
    # SCHOTEN
    # =========================

    for _ in range(2):

        if random.random() < 0.5:

            bron = (
                home_starting_players
                or
                home_players
            )

            speler = kies_live_speler(
                bron,
                "aanval"
            )

            voeg_event(
                "shot",
                "home",
                speler,
                f"Schot van {home_name}",
                f"{speler['naam']} haalt uit van afstand."
            )

        else:

            bron = (
                away_starting_players
                or
                away_players
            )

            speler = kies_live_speler(
                bron,
                "aanval"
            )

            voeg_event(
                "shot",
                "away",
                speler,
                f"Schot van {away_name}",
                f"{speler['naam']} haalt uit."
            )

    # =========================
    # CORNERS
    # =========================

    for _ in range(2):

        if random.random() < 0.5:

            bron = (
                home_starting_players
                or
                home_players
            )

            speler = kies_live_speler(
                bron
            )

            voeg_event(
                "corner",
                "home",
                speler,
                f"Corner voor {home_name}",
                f"{speler['naam']} legt de bal voor."
            )

        else:

            bron = (
                away_starting_players
                or
                away_players
            )

            speler = kies_live_speler(
                bron
            )

            voeg_event(
                "corner",
                "away",
                speler,
                f"Corner voor {away_name}",
                f"{speler['naam']} legt de bal voor."
            )

    # =========================
    # REDDINGEN
    # =========================

    for _ in range(2):

        if random.random() < 0.5:

            keeper = kies_live_speler(
                home_starting_players
                or
                home_players,
                "keeper"
            )

            schutter = kies_live_speler(
                away_starting_players
                or
                away_players,
                "aanval"
            )

            voeg_event(
                "save",
                "home",
                keeper,
                f"Redding van {home_name}",
                f"{keeper['naam']} stopt het schot van {schutter['naam']}."
            )

        else:

            keeper = kies_live_speler(
                away_starting_players
                or
                away_players,
                "keeper"
            )

            schutter = kies_live_speler(
                home_starting_players
                or
                home_players,
                "aanval"
            )

            voeg_event(
                "save",
                "away",
                keeper,
                f"Redding van {away_name}",
                f"{keeper['naam']} stopt het schot van {schutter['naam']}."
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

            bron = (
                home_starting_players
                or
                home_players
            )

            speler = kies_live_speler(
                bron,
                "verdediging"
            )

            team = "home"

        else:

            bron = (
                away_starting_players
                or
                away_players
            )

            speler = kies_live_speler(
                bron,
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

        if random.random() < 0.10:

            kaart_type = "red"
            titel = "Rode kaart"

            tekst = (
                f"{speler['naam']} "
                f"krijgt rood en moet het veld verlaten."
            )

        else:

            kaart_type = "yellow"
            titel = "Gele kaart"

            tekst = (
                f"{speler['naam']} "
                f"krijgt geel na een overtreding."
            )

        voeg_event(
            kaart_type,
            team,
            speler,
            titel,
            tekst,
            tweede_helft=(
                random.random() < 0.5
            )
        )

    # =========================
    # WISSELS
    # =========================

    for team, alle_spelers, basiself_spelers, teamnaam in [

        (
            "home",
            home_players,
            home_starting_players,
            home_name
        ),

        (
            "away",
            away_players,
            away_starting_players,
            away_name
        )
    ]:

        basis_ids = {
            int(speler["id"])
            for speler in basiself_spelers
        }

        bank = [
            speler
            for speler in alle_spelers
            if int(speler["id"])
            not in basis_ids
        ]

        if (
            len(basiself_spelers) >= 1
            and
            len(bank) >= 1
        ):

            eruit = random.choice(
                basiself_spelers
            )

            erin = random.choice(
                bank
            )

            voeg_event(
                "substitution",
                team,
                erin,
                f"Wissel {teamnaam}",
                (
                    f"{erin['naam']} komt erin "
                    f"voor {eruit['naam']}."
                ),
                tweede_helft=True
            )

    # =========================
    # BLESSURE
    # =========================

    if random.random() < 0.30:

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_starting_players
                or
                home_players
            )

            voeg_event(
                "injury",
                "home",
                speler,
                f"Blessure bij {home_name}",
                f"{speler['naam']} heeft verzorging nodig."
            )

        else:

            speler = kies_live_speler(
                away_starting_players
                or
                away_players
            )

            voeg_event(
                "injury",
                "away",
                speler,
                f"Blessure bij {away_name}",
                f"{speler['naam']} heeft verzorging nodig."
            )

    # =========================
    # BUITENSPEL
    # =========================

    if random.random() < 0.50:

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_starting_players
                or
                home_players,
                "aanval"
            )

            voeg_event(
                "offside",
                "home",
                speler,
                "Buitenspel",
                f"{speler['naam']} staat buitenspel."
            )

        else:

            speler = kies_live_speler(
                away_starting_players
                or
                away_players,
                "aanval"
            )

            voeg_event(
                "offside",
                "away",
                speler,
                "Buitenspel",
                f"{speler['naam']} staat buitenspel."
            )

    events.sort(
        key=lambda event: event["at"]
    )

    return events


# =========================
# MAN OF THE MATCH
# =========================

def bepaal_motm(
    live_match,
    home_players,
    away_players
):

    kandidaten = {}

    home_players = [
        speler_naar_dict(speler)
        for speler in home_players
    ]

    away_players = [
        speler_naar_dict(speler)
        for speler in away_players
    ]

    for team, spelers in [
        ("home", home_players),
        ("away", away_players)
    ]:

        for speler in spelers:

            kandidaten[
                (
                    team,
                    speler["naam"]
                )
            ] = {
                "player_id": int(
                    speler["id"]
                ),
                "name": speler["naam"],
                "team": team,
                "goals": 0,
                "points": 0,
                "rating": int(
                    speler["rating"]
                )
            }

    for event in live_match.get(
        "events",
        []
    ):

        key = (
            event.get("team"),
            event.get("player")
        )

        speler = kandidaten.get(
            key
        )

        if speler is None:
            continue

        event_type = event.get(
            "type"
        )

        if event_type == "goal":

            speler["goals"] += 1
            speler["points"] += 10

        elif event_type == "save":

            speler["points"] += 5

        elif event_type == "chance":

            speler["points"] += 2

        elif event_type == "shot":

            speler["points"] += 1

        elif event_type == "attack":

            speler["points"] += 1

        elif event_type == "corner":

            speler["points"] += 1

        elif event_type == "yellow":

            speler["points"] -= 1

        elif event_type == "red":

            speler["points"] -= 5

        elif event_type == "injury":

            speler["points"] -= 1

    basis_ids = set()

    for team in [
        "home",
        "away"
    ]:

        for item in live_match[
            team
        ].get(
            "starting_lineup",
            []
        ):

            if not item.get("player"):
                continue

            basis_ids.add(
                (
                    team,
                    item["player"]["naam"]
                )
            )

    geldige_kandidaten = [
        speler
        for key, speler in kandidaten.items()
        if key in basis_ids
    ]

    if not geldige_kandidaten:
        return None

    geldige_kandidaten.sort(
        key=lambda speler: (
            speler["points"],
            speler["goals"],
            speler["rating"]
        ),
        reverse=True
    )

    return geldige_kandidaten[0]


# =========================
# SPELERSTATISTIEKEN OPSLAAN
# =========================

def verwerk_spelerstatistieken(
    match_id,
    match_datum,
    live_match,
    home_players,
    away_players
):

    maand = (
        match_datum[:7]
        if match_datum
        else date.today().strftime(
            "%Y-%m"
        )
    )

    all_players = {
        (
            "home",
            speler["naam"]
        ): speler
        for speler in home_players
    }

    all_players.update({
        (
            "away",
            speler["naam"]
        ): speler
        for speler in away_players
    })

    goal_counts = {}

    for event in live_match.get(
        "events",
        []
    ):

        if event.get("type") != "goal":
            continue

        key = (
            event.get("team"),
            event.get("player")
        )

        goal_counts[key] = (
            goal_counts.get(
                key,
                0
            )
            + 1
        )

    basis_players = []

    for team in [
        "home",
        "away"
    ]:

        for item in live_match[
            team
        ].get(
            "starting_lineup",
            []
        ):

            speler = item.get(
                "player"
            )

            if not speler:
                continue

            basis_players.append({
                "team": team,
                "player": speler
            })

    motm = bepaal_motm(
        live_match,
        home_players,
        away_players
    )

    motm_player_id = (
        motm["player_id"]
        if motm
        else None
    )

    motm_club_id = None
    motm_club_name = None

    if motm:

        if motm["team"] == "home":

            motm_club_id = (
                live_match["home"]["club_id"]
            )

            motm_club_name = (
                live_match["home"]["name"]
            )

        else:

            motm_club_id = (
                live_match["away"]["club_id"]
            )

            motm_club_name = (
                live_match["away"]["name"]
            )

    connection = get_connection()

    # =========================
    # ALLE SPELERS MET GOALS
    # =========================

    for key, aantal_goals in goal_counts.items():

        speler = all_players.get(
            key
        )

        if not speler:
            continue

        player_id = int(
            speler["id"]
        )

        connection.execute("""
            INSERT INTO player_stats (
                player_id,
                maand,
                wedstrijden,
                doelpunten,
                motm
            )
            VALUES (?, ?, 0, ?, 0)

            ON CONFLICT(
                player_id,
                maand
            )

            DO UPDATE SET
                doelpunten =
                    doelpunten + excluded.doelpunten
        """, (
            player_id,
            maand,
            aantal_goals
        ))

    # =========================
    # WEDSTRIJDEN + MOTM
    # =========================

    for item in basis_players:

        speler = item["player"]

        player_id = int(
            speler["id"]
        )

        goals = goal_counts.get(
            (
                item["team"],
                speler["naam"]
            ),
            0
        )

        speler_motm = (
            1
            if player_id == motm_player_id
            else 0
        )

        connection.execute("""
            INSERT INTO player_stats (
                player_id,
                maand,
                wedstrijden,
                doelpunten,
                motm
            )
            VALUES (?, ?, 1, ?, ?)

            ON CONFLICT(
                player_id,
                maand
            )

            DO UPDATE SET
                wedstrijden =
                    wedstrijden + 1,
                doelpunten =
                    doelpunten + excluded.doelpunten,
                motm =
                    motm + excluded.motm
        """, (
            player_id,
            maand,
            goals,
            speler_motm
        ))

    # =========================
    # MOTM OPSLAAN
    # =========================

    connection.execute("""
        INSERT OR REPLACE INTO match_awards (
            match_id,
            player_id,
            player_name,
            club_id,
            club_name,
            datum
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        match_id,
        motm["player_id"] if motm else None,
        motm["name"] if motm else None,
        motm_club_id,
        motm_club_name,
        match_datum
    ))

    # =========================
    # SCORE BEREKENEN
    # =========================

    home_score = 0
    away_score = 0

    for event in live_match.get(
        "events",
        []
    ):

        if event.get("type") != "goal":
            continue

        if event.get("team") == "home":

            home_score += 1

        elif event.get("team") == "away":

            away_score += 1

    # =========================
    # SPELER INTERVIEW
    # =========================

    if motm:

        if motm["goals"] > 0:

            speler_quote = (
                "Ik ben blij dat ik belangrijk "
                "kon zijn voor het team. "
                "We hebben samen hard gewerkt."
            )

        else:

            speler_quote = (
                "Ik ben vooral blij met de "
                "prestatie van het hele team. "
                "We hebben goed samengewerkt."
            )

        connection.execute("""
            INSERT INTO interviews (
                match_id,
                datum,
                spreker,
                rol,
                club_name,
                tekst
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            match_datum,
            motm["name"],
            "Speler",
            motm_club_name,
            speler_quote
        ))

    # =========================
    # TRAINER INTERVIEW
    # =========================

    if home_score > away_score:

        trainer_club = (
            live_match["home"]["name"]
        )

        trainer_quote = (
            "We hebben vandaag goed "
            "gecontroleerd en als team "
            "hard gewerkt."
        )

    elif away_score > home_score:

        trainer_club = (
            live_match["away"]["name"]
        )

        trainer_quote = (
            "De ploeg heeft hard gewerkt "
            "en is blijven geloven in het "
            "resultaat."
        )

    else:

        trainer_club = (
            live_match["home"]["name"]
        )

        trainer_quote = (
            "Het was een spannende wedstrijd. "
            "We nemen het punt mee en kijken "
            "vooruit naar de volgende wedstrijd."
        )

    connection.execute("""
        INSERT INTO interviews (
            match_id,
            datum,
            spreker,
            rol,
            club_name,
            tekst
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        match_id,
        match_datum,
        "ClubMaster trainer",
        "Trainer",
        trainer_club,
        trainer_quote
    ))

    connection.commit()
    connection.close()


# =========================
# AI WEDSTRIJDEN
# =========================

def speel_ai_wedstrijden():

    gebruiker_club = session.get("club")

    if gebruiker_club is None:
        return

    connection = get_connection()

    wedstrijden = connection.execute("""
        SELECT
            matches.id,
            matches.home_club_id,
            matches.away_club_id,
            matches.gespeeld,
            matches.datum,
            matches.home_score,
            matches.away_score,

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

        WHERE matches.gespeeld = 0

        ORDER BY
            matches.speelronde,
            matches.id
    """).fetchall()

    connection.close()

    for match in wedstrijden:

        # Eigen wedstrijden blijven voor
        # de speler zelf.
        if gebruiker_club["id"] in [
            match["home_club_id"],
            match["away_club_id"]
        ]:
            continue

        if not wedstrijd_beschikbaar(
            match["datum"]
        ):
            continue

        home_players = get_players_for_club(
            match["home_club_id"]
        )

        away_players = get_players_for_club(
            match["away_club_id"]
        )

        home_lineup = bouw_basiself(
            home_players
        )

        away_lineup = bouw_basiself(
            away_players
        )

        # =========================
        # AI SCORE
        # =========================

        home_score, away_score = (
            bereken_wedstrijdscore(
                match["home_rating"],
                match["away_rating"]
            )
        )

        # =========================
        # GOAL EVENTS
        # =========================

        events = []
        gebruikte_tijden = []

        def voeg_ai_goal(
            team,
            speler,
            clubnaam,
            tweede_helft=False
        ):

            tijd = maak_unieke_event_tijd(
                gebruikte_tijden,
                tweede_helft
            )

            gebruikte_tijden.append(
                tijd
            )

            events.append({
                "at": tijd,
                "minute": live_minuut_voor_secondes(
                    tijd
                ),
                "type": "goal",
                "team": team,
                "player": speler["naam"],
                "title": f"GOAL! {clubnaam}",
                "text": (
                    f"{speler['naam']} "
                    f"schiet de bal binnen."
                )
            })

        for _ in range(home_score):

            aanvallers = [
                item["player"]
                for item in home_lineup
                if (
                    item.get("player")
                    and
                    classificeer_positie(
                        item["player"]["positie"]
                    ) == "aanval"
                )
            ]

            bron = (
                aanvallers
                if aanvallers
                else home_players
            )

            speler = kies_live_speler(
                bron,
                "aanval"
            )

            voeg_ai_goal(
                "home",
                speler,
                match["home_naam"],
                random.random() < 0.45
            )

        for _ in range(away_score):

            aanvallers = [
                item["player"]
                for item in away_lineup
                if (
                    item.get("player")
                    and
                    classificeer_positie(
                        item["player"]["positie"]
                    ) == "aanval"
                )
            ]

            bron = (
                aanvallers
                if aanvallers
                else away_players
            )

            speler = kies_live_speler(
                bron,
                "aanval"
            )

            voeg_ai_goal(
                "away",
                speler,
                match["away_naam"],
                random.random() < 0.45
            )

        events.sort(
            key=lambda event: event["at"]
        )

        ai_live_match = {

            "match_id":
                match["id"],

            "started_at":
                time.time(),

            "home": {

                "club_id":
                    match["home_club_id"],

                "name":
                    match["home_naam"],

                "logo":
                    match["home_logo"],

                "rating":
                    match["home_rating"],

                "starting_lineup":
                    home_lineup
            },

            "away": {

                "club_id":
                    match["away_club_id"],

                "name":
                    match["away_naam"],

                "logo":
                    match["away_logo"],

                "rating":
                    match["away_rating"],

                "starting_lineup":
                    away_lineup
            },

            "events":
                events
        }

        # =========================
        # WEDSTRIJD OPSLAAN
        # =========================

        connection = get_connection()

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
            match["id"]
        ))

        connection.commit()
        connection.close()

        # =========================
        # STATISTIEKEN
        # =========================

        verwerk_spelerstatistieken(
            match["id"],
            match["datum"],
            ai_live_match,
            home_players,
            away_players
        )

        # =========================
        # COMPETITIE
        # =========================

        update_competition(
            match["home_club_id"],
            match["away_club_id"],
            home_score,
            away_score
        )


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


@app.route("/choose/<club_name>")
def choose_club(club_name):

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
        "id": club["id"],
        "naam": club["naam"],
        "stad": club["stad"],
        "rating": club["rating"],
        "logo": club["logo"],
        "budget": club["budget"]
    }

    session["transfer_testmodus"] = True
    session["test_aankopen"] = []
    session["transfer_history"] = []

    return redirect(
        url_for("dashboard")
    )


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    # AI speelt automatisch wedstrijden
    # die voor vandaag beschikbaar zijn.
    speel_ai_wedstrijden()

    club = session.get("club")

    if club is None:

        return render_template(
            "dashboard.html",
            club=None,
            interviews=[]
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

    interviews = connection.execute("""
        SELECT
            id,
            match_id,
            datum,
            spreker,
            rol,
            club_name,
            tekst
        FROM interviews
        ORDER BY id DESC
        LIMIT 4
    """).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        club=club,
        competitie=eigen_team,
        positie=positie,
        interviews=interviews
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

    club = session.get("club")

    if club is None:

        return render_template(
            "dashboard.html",
            club=None
        )

    connection = get_connection()

    spelers = connection.execute("""
        SELECT
            p.id,
            p.naam,
            p.positie,
            p.leeftijd,
            p.marktwaarde,
            p.rating,
            p.salaris,
            p.contractduur,
            COALESCE(
                SUM(s.wedstrijden),
                0
            ) AS wedstrijden,
            COALESCE(
                SUM(s.doelpunten),
                0
            ) AS doelpunten,
            COALESCE(
                SUM(s.motm),
                0
            ) AS motm
        FROM players p
        LEFT JOIN player_stats s
            ON s.player_id = p.id
        WHERE p.club_id = ?
        GROUP BY p.id
        ORDER BY p.rating DESC
    """, (
        club["id"],
    )).fetchall()

    totaal_spelers = len(
        spelers
    )

    gemiddelde_rating = (
        round(
            sum(
                int(player["rating"])
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
        int(player["marktwaarde"])
        for player in spelers
    )

    hoogste_rating = (
        spelers[0]
        if spelers
        else None
    )

    topscorers = connection.execute("""
        SELECT
            p.id,
            p.naam,
            p.positie,
            p.rating,
            c.naam AS club_naam,
            c.logo AS club_logo,
            COALESCE(
                SUM(s.doelpunten),
                0
            ) AS doelpunten
        FROM players p
        JOIN clubs c
            ON c.id = p.club_id
        LEFT JOIN player_stats s
            ON s.player_id = p.id
        GROUP BY p.id
        HAVING COALESCE(
            SUM(s.doelpunten),
            0
        ) > 0
        ORDER BY
            doelpunten DESC,
            p.rating DESC,
            p.naam ASC
        LIMIT 10
    """).fetchall()

    huidige_maand = date.today().strftime(
        "%Y-%m"
    )

    player_of_month = connection.execute("""
        SELECT
            p.id,
            p.naam,
            p.positie,
            p.rating,
            c.naam AS club_naam,
            c.logo AS club_logo,
            s.wedstrijden,
            s.doelpunten,
            s.motm
        FROM player_stats s
        JOIN players p
            ON p.id = s.player_id
        JOIN clubs c
            ON c.id = p.club_id
        WHERE s.maand = ?
        ORDER BY
            s.doelpunten DESC,
            s.motm DESC,
            s.wedstrijden DESC,
            p.rating DESC,
            p.naam ASC
        LIMIT 1
    """, (
        huidige_maand,
    )).fetchone()

    recente_motm = connection.execute("""
        SELECT
            match_awards.match_id,
            match_awards.player_name,
            match_awards.club_name,
            match_awards.datum,
            players.rating
        FROM match_awards
        LEFT JOIN players
            ON players.id =
               match_awards.player_id
        WHERE match_awards.player_name IS NOT NULL
        ORDER BY match_awards.match_id DESC
        LIMIT 5
    """).fetchall()

    interviews = connection.execute("""
        SELECT
            id,
            match_id,
            datum,
            spreker,
            rol,
            club_name,
            tekst
        FROM interviews
        ORDER BY id DESC
        LIMIT 8
    """).fetchall()

    connection.close()

    return render_template(
        "statistics.html",
        club=club,
        players=spelers,
        totaal_spelers=totaal_spelers,
        gemiddelde_rating=gemiddelde_rating,
        totale_waarde=totale_waarde,
        hoogste_rating=hoogste_rating,
        topscorers=topscorers,
        player_of_month=player_of_month,
        recente_motm=recente_motm,
        interviews=interviews
    )


# =========================
# COMPETITIE
# =========================

@app.route("/competition")
def competition():

    club = session.get("club")

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

    # AI-wedstrijden automatisch afhandelen.
    speel_ai_wedstrijden()

    club = session.get("club")

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

        wedstrijd["eigen_wedstrijd"] = (
            club["id"] in [
                match["home_club_id"]
                if "home_club_id" in match.keys()
                else -1,
                match["away_club_id"]
                if "away_club_id" in match.keys()
                else -1
            ]
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
# LIVE WEDSTRIJD OPENEN
# =========================

@app.route(
    "/play_match/<int:match_id>"
)
def play_match(match_id):

    club = session.get("club")

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

    connection.close()

    if match is None:

        return "Wedstrijd niet gevonden", 404

    if match["gespeeld"]:

        return redirect(
            url_for("matches")
        )

    if not wedstrijd_beschikbaar(
        match["datum"]
    ):

        return redirect(
            url_for("matches")
        )

    if club["id"] not in [
        match["home_club_id"],
        match["away_club_id"]
    ]:

        return redirect(
            url_for("matches")
        )

    home_players = get_players_for_club(
        match["home_club_id"]
    )

    away_players = get_players_for_club(
        match["away_club_id"]
    )

    opgeslagen_opstelling = session.get(
        "opstelling",
        {}
    )

    if club["id"] == match["home_club_id"]:

        home_lineup = bouw_basiself(
            home_players,
            opgeslagen_opstelling
        )

        away_lineup = bouw_basiself(
            away_players
        )

    else:

        home_lineup = bouw_basiself(
            home_players
        )

        away_lineup = bouw_basiself(
            away_players,
            opgeslagen_opstelling
        )

    bestaande_live = session.get(
        "live_match"
    )

    # =========================
    # NIEUWE / NOG NIET GESTARTE
    # WEDSTRIJD
    # =========================

    if (
        bestaande_live is None
        or
        bestaande_live.get(
            "match_id"
        ) != match_id
        or
        bestaande_live.get(
            "started_at"
        ) is not None
    ):

        events = genereer_live_events(
            home_players,
            away_players,
            match["home_naam"],
            match["away_naam"],
            match["home_rating"],
            match["away_rating"],
            home_lineup,
            away_lineup
        )

        bestaande_live = {

            "match_id":
                match_id,

            "started_at":
                None,

            "home": {

                "club_id":
                    match["home_club_id"],

                "name":
                    match["home_naam"],

                "logo":
                    match["home_logo"],

                "rating":
                    match["home_rating"],

                "starting_lineup":
                    home_lineup
            },

            "away": {

                "club_id":
                    match["away_club_id"],

                "name":
                    match["away_naam"],

                "logo":
                    match["away_logo"],

                "rating":
                    match["away_rating"],

                "starting_lineup":
                    away_lineup
            },

            "events":
                events
        }

        session["live_match"] = (
            bestaande_live
        )

        session.modified = True

    # Actuele tactieken meegeven.
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
        "live_match.html",
        club=club,
        live_match=bestaande_live,
        tactieken=tactieken
    )


# =========================
# LIVE WEDSTRIJD STARTEN
# =========================

@app.route(
    "/play_match/<int:match_id>/start",
    methods=["POST"]
)
def start_live_match(match_id):

    club = session.get("club")

    if club is None:

        return jsonify({
            "success": False,
            "error": "Geen club geselecteerd."
        }), 400

    connection = get_connection()

    match = connection.execute("""
        SELECT
            id,
            home_club_id,
            away_club_id,
            gespeeld
        FROM matches
        WHERE id = ?
    """, (
        match_id,
    )).fetchone()

    connection.close()

    if match is None:

        return jsonify({
            "success": False,
            "error": "Wedstrijd niet gevonden."
        }), 404

    if match["gespeeld"]:

        session.pop(
            "live_match",
            None
        )

        session.modified = True

        return jsonify({
            "success": False,
            "error": "Deze wedstrijd is al gespeeld."
        }), 400

    if club["id"] not in [
        match["home_club_id"],
        match["away_club_id"]
    ]:

        return jsonify({
            "success": False,
            "error": "Je speelt deze wedstrijd niet."
        }), 403

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
            "success": False,
            "error": "Geen actieve wedstrijd."
        }), 400

    started_at = time.time()

    live_match["started_at"] = (
        started_at
    )

    session["live_match"] = (
        live_match
    )

    session.modified = True

    return jsonify({
        "success": True,
        "started_at": started_at,
        "events": live_match.get(
            "events",
            []
        )
    })


# =========================
# LIVE WEDSTRIJD AFSLUITEN
# =========================

@app.route(
    "/play_match/<int:match_id>/finish",
    methods=["POST"]
)
def finish_played_match(match_id):

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
            "success": False,
            "error": "Geen actieve live wedstrijd."
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

        session.pop(
            "live_match",
            None
        )

        session.modified = True

        return jsonify({
            "success": False,
            "error": "Wedstrijd niet gevonden."
        }), 404

    if match["gespeeld"]:

        connection.close()

        session.pop(
            "live_match",
            None
        )

        session.modified = True

        return jsonify({
            "success": True,
            "redirect": url_for("matches")
        })

    # =========================
    # SCORE UIT GOALS
    # =========================

    home_score = 0
    away_score = 0

    for event in live_match.get(
        "events",
        []
    ):

        if event.get("type") != "goal":
            continue

        if event.get("team") == "home":

            home_score += 1

        elif event.get("team") == "away":

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
    # SPELERSTATISTIEKEN
    # =========================

    home_players = get_players_for_club(
        match["home_club_id"]
    )

    away_players = get_players_for_club(
        match["away_club_id"]
    )

    verwerk_spelerstatistieken(
        match_id,
        match["datum"],
        live_match,
        home_players,
        away_players
    )

    # =========================
    # COMPETITIE
    # =========================

    update_competition(
        match["home_club_id"],
        match["away_club_id"],
        home_score,
        away_score
    )

    # =========================
    # LIVE SESSION WEG
    # =========================

    session.pop(
        "live_match",
        None
    )

    session.modified = True

    return jsonify({
        "success": True,
        "home_score": home_score,
        "away_score": away_score,
        "redirect": url_for("matches")
    })


# =========================
# TRANSFERMARKT
# =========================

@app.route("/transfers")
def transfers():

    club = session.get("club")

    if club is None:

        return redirect(
            url_for("clubs_page")
        )

    testmodus = session.get(
        "transfer_testmodus",
        True
    )

    raw_test_aankopen = session.get(
        "test_aankopen",
        []
    )

    test_aankopen = []

    for player_id in raw_test_aankopen:

        try:

            test_aankopen.append(
                int(player_id)
            )

        except (
            TypeError,
            ValueError
        ):

            pass

    session["test_aankopen"] = (
        test_aankopen
    )

    transfer_history = session.get(
        "transfer_history",
        []
    )

    connection = get_connection()

    alle_spelers = connection.execute("""
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
        ORDER BY players.rating DESC
        LIMIT 50
    """, (
        club["id"],
    )).fetchall()

    spelers = [
        player
        for player in alle_spelers
        if int(player["id"])
        not in test_aankopen
    ]

    test_players = []

    if test_aankopen:

        placeholders = ",".join(
            ["?"] * len(test_aankopen)
        )

        test_players = connection.execute(
            f"""
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
                WHERE players.id IN ({placeholders})
                ORDER BY players.rating DESC
            """,
            test_aankopen
        ).fetchall()

    connection.close()

    return render_template(
        "transfers.html",
        club=club,
        players=spelers,
        test_players=test_players,
        testmodus=testmodus,
        test_aankopen=test_aankopen,
        transfer_history=transfer_history
    )


@app.route(
    "/transfers/toggle-testmode",
    methods=["POST"]
)
def toggle_transfer_testmode():

    huidige_status = session.get(
        "transfer_testmodus",
        True
    )

    session["transfer_testmodus"] = (
        not huidige_status
    )

    return redirect(
        url_for("transfers")
    )


@app.route(
    "/transfers/buy/<int:player_id>",
    methods=["POST"]
)
def buy_transfer(player_id):

    club = session.get("club")

    if club is None:

        return redirect(
            url_for("clubs_page")
        )

    testmodus = session.get(
        "transfer_testmodus",
        True
    )

    raw_test_aankopen = session.get(
        "test_aankopen",
        []
    )

    test_aankopen = []

    for old_id in raw_test_aankopen:

        try:

            test_aankopen.append(
                int(old_id)
            )

        except (
            TypeError,
            ValueError
        ):

            pass

    transfer_history = session.get(
        "transfer_history",
        []
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
            players.club_id,
            clubs.naam AS club_naam
        FROM players
        JOIN clubs
            ON players.club_id = clubs.id
        WHERE players.id = ?
    """, (
        player_id,
    )).fetchone()

    if player is None:

        connection.close()

        return redirect(
            url_for("transfers")
        )

    if int(player["club_id"]) == int(
        club["id"]
    ):

        connection.close()

        return redirect(
            url_for("transfers")
        )

    # =========================
    # TESTMODUS
    # =========================

    if testmodus:

        if player_id not in test_aankopen:

            test_aankopen.append(
                player_id
            )

            session["test_aankopen"] = (
                test_aankopen
            )

            transfer_history.insert(
                0,
                {
                    "player_name":
                        player["naam"],

                    "position":
                        player["positie"],

                    "rating":
                        int(
                            player["rating"]
                        ),

                    "from_club":
                        player["club_naam"],

                    "to_club":
                        club["naam"],

                    "price":
                        int(
                            player["marktwaarde"]
                        ),

                    "date":
                        datetime.now().strftime(
                            "%d-%m-%Y %H:%M"
                        ),

                    "test":
                        True
                }
            )

            session["transfer_history"] = (
                transfer_history[:50]
            )

        connection.close()

        return redirect(
            url_for("transfers")
        )

    # =========================
    # ECHTE TRANSFER
    # =========================

    transferprijs = int(
        player["marktwaarde"]
    )

    huidige_club = connection.execute("""
        SELECT budget
        FROM clubs
        WHERE id = ?
    """, (
        club["id"],
    )).fetchone()

    if huidige_club is None:

        connection.close()

        return redirect(
            url_for("transfers")
        )

    if int(
        huidige_club["budget"]
    ) < transferprijs:

        connection.close()

        return redirect(
            url_for("transfers")
        )

    connection.execute("""
        UPDATE players
        SET club_id = ?
        WHERE id = ?
    """, (
        club["id"],
        player_id
    ))

    nieuw_budget = (
        int(huidige_club["budget"])
        -
        transferprijs
    )

    connection.execute("""
        UPDATE clubs
        SET budget = ?
        WHERE id = ?
    """, (
        nieuw_budget,
        club["id"]
    ))

    connection.commit()
    connection.close()

    transfer_history.insert(
        0,
        {
            "player_name":
                player["naam"],

            "position":
                player["positie"],

            "rating":
                int(
                    player["rating"]
                ),

            "from_club":
                player["club_naam"],

            "to_club":
                club["naam"],

            "price":
                transferprijs,

            "date":
                datetime.now().strftime(
                    "%d-%m-%Y %H:%M"
                ),

            "test":
                False
        }
    )

    session["transfer_history"] = (
        transfer_history[:50]
    )

    club["budget"] = (
        nieuw_budget
    )

    session["club"] = club

    return redirect(
        url_for("transfers")
    )


@app.route(
    "/transfers/test-sell/<int:player_id>",
    methods=["POST"]
)
def test_sell_transfer(player_id):

    raw_test_aankopen = session.get(
        "test_aankopen",
        []
    )

    test_aankopen = []

    for old_id in raw_test_aankopen:

        try:

            old_id = int(
                old_id
            )

            if old_id != player_id:

                test_aankopen.append(
                    old_id
                )

        except (
            TypeError,
            ValueError
        ):

            pass

    session["test_aankopen"] = (
        test_aankopen
    )

    return redirect(
        url_for("transfers")
    )


# =========================
# SPELER BEKIJKEN
# =========================

@app.route(
    "/player/<int:player_id>"
)
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

    club = session.get("club")

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

        terug_naar = session.pop(
            "_tactics_next",
            None
        )

        terug_naar = geldige_interne_url(
            terug_naar
        )

        if terug_naar:

            return redirect(
                terug_naar
            )

        return redirect(
            url_for("tactics")
        )

    next_url = geldige_interne_url(
        request.args.get("next")
    )

    if next_url:

        session["_tactics_next"] = (
            next_url
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

    club = session.get("club")

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

        terug_naar = session.pop(
            "_lineup_next",
            None
        )

        terug_naar = geldige_interne_url(
            terug_naar
        )

        if terug_naar:

            return redirect(
                terug_naar
            )

        return redirect(
            url_for("lineup")
        )

    next_url = geldige_interne_url(
        request.args.get("next")
    )

    if next_url:

        session["_lineup_next"] = (
            next_url
        )

    opstelling = session.get(
        "opstelling",
        {
            "keeper": "",
            "verdediger_1": "",
            "verdediger_2": "",
            "verdediger_3": "",
            "verdediger_4": "",
            "middenvelder_1": "",
            "middenvelder_2": "",
            "middenvelder_3": "",
            "aanvaller_1": "",
            "aanvaller_2": "",
            "aanvaller_3": ""
        }
    )

    return render_template(
        "lineup.html",
        club=club,
        players=spelers,
        opstelling=opstelling
    )


# =========================
# TEST RESET
# =========================

@app.route("/reset-test")
def reset_test_route():

    connection = get_connection()

    # =========================
    # WEDSTRIJDEN
    # =========================

    connection.execute("""
        UPDATE matches
        SET
            home_score = 0,
            away_score = 0,
            gespeeld = 0
    """)

    # =========================
    # COMPETITIE
    # =========================

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
    """)

    # =========================
    # STATISTIEKEN
    # =========================

    connection.execute("""
        DELETE FROM player_stats
    """)

    connection.execute("""
        DELETE FROM match_awards
    """)

    connection.execute("""
        DELETE FROM interviews
    """)

    connection.commit()
    connection.close()

    session.pop(
        "live_match",
        None
    )

    session.modified = True

    return """
    <!DOCTYPE html>

    <html lang="nl">

    <head>

        <meta charset="UTF-8">

        <title>
            ClubMaster reset
        </title>

        <style>

            body {
                background: #0b0f19;
                color: white;
                font-family: Arial, sans-serif;
                text-align: center;
                padding-top: 100px;
            }

            a {
                display: inline-block;
                margin-top: 20px;
                padding: 12px 20px;
                background: #22c55e;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
            }

        </style>

    </head>

    <body>

        <h1>
            ClubMaster is gereset
        </h1>

        <p>
            Wedstrijden zijn teruggezet naar 0 gespeeld.
        </p>

        <p>
            Scores en competitie zijn gereset.
        </p>

        <p>
            Topscoorders, MOTM en interviews zijn gewist.
        </p>

        <p>
            De oude live wedstrijd is verwijderd.
        </p>

        <a href="/matches">
            Naar wedstrijden
        </a>

    </body>

    </html>
    """


# =========================
# BROWSER AUTOMATISCH OPENEN
# =========================

def open_browser():

    webbrowser.open_new(
        "http://127.0.0.1:5000"
    )


# =========================
# START
# =========================

if __name__ == "__main__":

    create_competition_table()

    create_matches_table()

    create_statistics_tables()

    generate_matches()

    maak_bestaand_schema_dagelijks()

    Timer(
        1,
        open_browser
    ).start()

    app.run(
        debug=True,
        use_reloader=False
    )