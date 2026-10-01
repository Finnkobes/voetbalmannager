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


import json
import math
import random
import sqlite3
import time
import webbrowser

from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from threading import Timer

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


app = Flask(__name__)

app.secret_key = "clubmaster-development-key"

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database" / "football.db"


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# =========================================================
# GEBRUIKERS / LOGIN
# =========================================================

def create_users_table():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            club_id INTEGER,
            lineup_json TEXT NOT NULL DEFAULT '{}',
            tactics_json TEXT NOT NULL DEFAULT '{}',
            transfer_history_json TEXT NOT NULL DEFAULT '[]',
            transfer_offers_json TEXT NOT NULL DEFAULT '[]',
            transfer_offer_date TEXT,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        user_id = session.get("user_id")

        if user_id is None:
            return redirect(
                url_for("login")
            )

        connection = get_connection()

        user = connection.execute("""
            SELECT id
            FROM users
            WHERE id = ?
        """, (
            user_id,
        )).fetchone()

        connection.close()

        if user is None:

            session.clear()

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped_view


def get_current_user():

    user_id = session.get("user_id")

    if user_id is None:
        return None

    connection = get_connection()

    user = connection.execute("""
        SELECT
            id,
            username,
            password_hash,
            club_id,
            lineup_json,
            tactics_json,
            transfer_history_json,
            transfer_offers_json,
            transfer_offer_date,
            created_at
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    connection.close()

    return user


def load_json_value(value, default):

    if not value:
        return default

    try:
        return json.loads(value)

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError
    ):
        return default


def get_user_progress():

    user = get_current_user()

    if user is None:

        return {
            "lineup": {},
            "tactics": {
                "formatie": "4-3-3",
                "speelstijl": "Gebalanceerd",
                "mentaliteit": "Gebalanceerd",
                "druk": "Normaal"
            },
            "transfer_history": [],
            "transfer_offers": [],
            "transfer_offer_date": None
        }

    return {
        "lineup": load_json_value(
            user["lineup_json"],
            {}
        ),

        "tactics": load_json_value(
            user["tactics_json"],
            {
                "formatie": "4-3-3",
                "speelstijl": "Gebalanceerd",
                "mentaliteit": "Gebalanceerd",
                "druk": "Normaal"
            }
        ),

        "transfer_history": load_json_value(
            user["transfer_history_json"],
            []
        ),

        "transfer_offers": load_json_value(
            user["transfer_offers_json"],
            []
        ),

        "transfer_offer_date":
            user["transfer_offer_date"]
    }


def save_user_progress(
    lineup=None,
    tactics=None,
    transfer_history=None,
    transfer_offers=None,
    transfer_offer_date=None,
    club_id=None,
    clear_transfer_offer_date=False
):

    user_id = session.get("user_id")

    if user_id is None:
        return

    current = get_user_progress()

    if lineup is None:
        lineup = current["lineup"]

    if tactics is None:
        tactics = current["tactics"]

    if transfer_history is None:
        transfer_history = current["transfer_history"]

    if transfer_offers is None:
        transfer_offers = current["transfer_offers"]

    if (
        transfer_offer_date is None
        and
        not clear_transfer_offer_date
    ):
        transfer_offer_date = (
            current["transfer_offer_date"]
        )

    if club_id is None:

        user = get_current_user()

        if user:
            club_id = user["club_id"]

    connection = get_connection()

    connection.execute("""
        UPDATE users
        SET
            club_id = ?,
            lineup_json = ?,
            tactics_json = ?,
            transfer_history_json = ?,
            transfer_offers_json = ?,
            transfer_offer_date = ?
        WHERE id = ?
    """, (
        club_id,

        json.dumps(
            lineup,
            ensure_ascii=False
        ),

        json.dumps(
            tactics,
            ensure_ascii=False
        ),

        json.dumps(
            transfer_history,
            ensure_ascii=False
        ),

        json.dumps(
            transfer_offers,
            ensure_ascii=False
        ),

        transfer_offer_date,

        user_id
    ))

    connection.commit()
    connection.close()


# =========================================================
# CLUB VAN GEBRUIKER
# =========================================================

def get_user_club():

    user = get_current_user()

    if user is None:
        return None

    if user["club_id"] is None:
        return None

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
        WHERE id = ?
    """, (
        user["club_id"],
    )).fetchone()

    connection.close()

    return club


def set_user_club(club_id):

    save_user_progress(
        club_id=club_id
    )


# =========================================================
# COMPETITIE
# =========================================================

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
            INSERT OR IGNORE INTO competition (
                club_id
            )
            VALUES (?)
        """, (
            club["id"],
        ))

    connection.commit()
    connection.close()


# =========================================================
# STATISTIEKEN
# =========================================================

def create_statistics_tables():

    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            player_id INTEGER NOT NULL,
            maand TEXT NOT NULL,
            wedstrijden INTEGER NOT NULL DEFAULT 0,
            doelpunten INTEGER NOT NULL DEFAULT 0,
            motm INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (
                player_id,
                maand
            )
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


# =========================================================
# MATCHES
# =========================================================

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
            FOREIGN KEY (
                home_club_id
            ) REFERENCES clubs(id),
            FOREIGN KEY (
                away_club_id
            ) REFERENCES clubs(id)
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
            ADD COLUMN speelronde INTEGER
            NOT NULL DEFAULT 1
        """)

    if "datum" not in column_names:

        connection.execute("""
            ALTER TABLE matches
            ADD COLUMN datum TEXT
        """)

    connection.commit()
    connection.close()


# =========================================================
# CLUBS
# =========================================================

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


# =========================================================
# SPELERS
# =========================================================

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


# =========================================================
# POSITIE
# =========================================================

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


def speler_naar_dict(speler):

    if isinstance(speler, dict):
        return speler

    return {
        key: speler[key]
        for key in speler.keys()
    }


# =========================================================
# BASIS ELF
# =========================================================

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
                    and
                    speler_id not in gebruikte_ids
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
                key=lambda speler:
                int(speler["rating"]),
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
                    key=lambda speler:
                    int(speler["rating"]),
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


# =========================================================
# URL
# =========================================================

def geldige_interne_url(url):

    if not url:
        return None

    if not url.startswith("/"):
        return None

    if url.startswith("//"):
        return None

    return url


# =========================================================
# WEDSTRIJD BESCHIKBAAR
# =========================================================

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


# =========================================================
# WEDSTRIJDEN GENEREREN
# =========================================================

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


# =========================================================
# SCORE
# =========================================================

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


# =========================================================
# COMPETITIE BIJWERKEN
# =========================================================

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


# =========================================================
# LIVE SPELER
# =========================================================

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


# =========================================================
# LIVE MINUUT
# =========================================================

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


# =========================================================
# LOGISCHE WISSEL
# =========================================================

def maak_logische_wissel(
    alle_spelers,
    basiself_spelers
):

    alle_spelers = [
        speler_naar_dict(speler)
        for speler in alle_spelers
    ]

    basiself_spelers = [
        speler_naar_dict(speler)
        for speler in basiself_spelers
    ]

    basis_ids = {
        int(speler["id"])
        for speler in basiself_spelers
    }

    bank = [
        speler
        for speler in alle_spelers
        if int(speler["id"]) not in basis_ids
    ]

    if not basiself_spelers or not bank:
        return None

    mogelijke_wissels = []

    groepen = [
        "keeper",
        "verdediging",
        "middenveld",
        "aanval"
    ]

    for groep in groepen:

        spelers_uit = [
            speler
            for speler in basiself_spelers
            if classificeer_positie(
                speler["positie"]
            ) == groep
        ]

        spelers_in = [
            speler
            for speler in bank
            if classificeer_positie(
                speler["positie"]
            ) == groep
        ]

        if (
            spelers_uit
            and
            spelers_in
        ):

            for eruit in spelers_uit:

                for erin in spelers_in:

                    mogelijke_wissels.append(
                        (
                            eruit,
                            erin
                        )
                    )

    if not mogelijke_wissels:
        return None

    return random.choice(
        mogelijke_wissels
    )


def voeg_logische_wissel_toe(
    events,
    gebruikte_tijden,
    team,
    alle_spelers,
    basiself_spelers,
    teamnaam
):

    wissel = maak_logische_wissel(
        alle_spelers,
        basiself_spelers
    )

    if wissel is None:
        return

    eruit, erin = wissel

    tijd = maak_unieke_event_tijd(
        gebruikte_tijden,
        True
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
            "substitution",

        "team":
            team,

        "player":
            erin["naam"],

        "player_id":
            int(erin["id"]),

        "player_out":
            eruit["naam"],

        "player_out_id":
            int(eruit["id"]),

        "title":
            f"Wissel {teamnaam}",

        "text":
            (
                f"{erin['naam']} komt erin "
                f"voor {eruit['naam']}."
            )
    })


# =========================================================
# LIVE EVENTS
# =========================================================

def genereer_live_events(
    home_players,
    away_players,
    home_name,
    away_name,
    home_rating,
    away_rating,
    home_starting_lineup=None,
    away_starting_lineup=None,
    tactieken=None,
    eigen_team="home"
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
        speler_naar_dict(item["player"])
        for item in (
            home_starting_lineup or []
        )
        if item.get("player")
    ]

    away_starting_players = [
        speler_naar_dict(item["player"])
        for item in (
            away_starting_lineup or []
        )
        if item.get("player")
    ]

    tactieken = tactieken or {}

    home_attack_modifier = 1.0
    home_defense_modifier = 1.0

    away_attack_modifier = 1.0
    away_defense_modifier = 1.0

    speelstijl = tactieken.get(
        "speelstijl",
        "Gebalanceerd"
    )

    mentaliteit = tactieken.get(
        "mentaliteit",
        "Gebalanceerd"
    )

    druk = tactieken.get(
        "druk",
        "Normaal"
    )

    if speelstijl == "Aanvallend":

        if eigen_team == "home":
            home_attack_modifier += 0.15
        else:
            away_attack_modifier += 0.15

    elif speelstijl == "Verdedigend":

        if eigen_team == "home":

            home_attack_modifier -= 0.10
            home_defense_modifier += 0.15

        else:

            away_attack_modifier -= 0.10
            away_defense_modifier += 0.15

    elif speelstijl == "Counter":

        if eigen_team == "home":

            home_attack_modifier += 0.08
            home_defense_modifier += 0.05

        else:

            away_attack_modifier += 0.08
            away_defense_modifier += 0.05

    if mentaliteit == "Aanvallend":

        if eigen_team == "home":

            home_attack_modifier += 0.12
            home_defense_modifier -= 0.08

        else:

            away_attack_modifier += 0.12
            away_defense_modifier -= 0.08

    elif mentaliteit == "Voorzichtig":

        if eigen_team == "home":

            home_attack_modifier -= 0.10
            home_defense_modifier += 0.10

        else:

            away_attack_modifier -= 0.10
            away_defense_modifier += 0.10

    if druk == "Hoog":

        if eigen_team == "home":

            home_attack_modifier += 0.05
            home_defense_modifier -= 0.05

        else:

            away_attack_modifier += 0.05
            away_defense_modifier -= 0.05

    elif druk == "Laag":

        if eigen_team == "home":

            home_attack_modifier -= 0.03
            home_defense_modifier += 0.04

        else:

            away_attack_modifier -= 0.03
            away_defense_modifier += 0.04

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

            "player_id":
                int(speler.get("id", 0)),

            "title":
                titel,

            "text":
                tekst
        })

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

    home_expected_goals *= (
        home_attack_modifier
        *
        (
            2.0
            -
            away_defense_modifier
        )
    )

    away_expected_goals *= (
        away_attack_modifier
        *
        (
            2.0
            -
            home_defense_modifier
        )
    )

    home_goals = min(
        poisson_getal(
            max(
                0.1,
                home_expected_goals
            )
        ),
        3
    )

    away_goals = min(
        poisson_getal(
            max(
                0.1,
                away_expected_goals
            )
        ),
        3
    )

    if (
        home_goals == 0
        and
        away_goals == 0
        and
        random.random() < 0.35
    ):

        if random.random() < 0.5:
            home_goals = 1
        else:
            away_goals = 1

    for _ in range(home_goals):

        speler = kies_live_speler(
            home_starting_players
            or
            home_players,
            "aanval"
        )

        voeg_event(
            "goal",
            "home",
            speler,
            f"GOAL! {home_name}",
            f"{speler['naam']} schiet de bal binnen.",
            random.random() < 0.45
        )

    for _ in range(away_goals):

        speler = kies_live_speler(
            away_starting_players
            or
            away_players,
            "aanval"
        )

        voeg_event(
            "goal",
            "away",
            speler,
            f"GOAL! {away_name}",
            f"{speler['naam']} schiet de bal binnen.",
            random.random() < 0.45
        )

    aantal_aanvallen = 4

    if speelstijl == "Aanvallend":
        aantal_aanvallen = 5

    elif speelstijl == "Verdedigend":
        aantal_aanvallen = 3

    for _ in range(aantal_aanvallen):

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_starting_players
                or
                home_players,
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

            speler = kies_live_speler(
                away_starting_players
                or
                away_players,
                "middenveld"
            )

            voeg_event(
                "attack",
                "away",
                speler,
                f"{away_name} valt aan",
                f"{speler['naam']} zoekt de ruimte."
            )

    for _ in range(2):

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_starting_players
                or
                home_players,
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

            speler = kies_live_speler(
                away_starting_players
                or
                away_players,
                "aanval"
            )

            voeg_event(
                "chance",
                "away",
                speler,
                f"Grote kans voor {away_name}",
                f"{speler['naam']} komt gevaarlijk voor het doel."
            )

    for _ in range(2):

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_starting_players
                or
                home_players,
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

            speler = kies_live_speler(
                away_starting_players
                or
                away_players,
                "aanval"
            )

            voeg_event(
                "shot",
                "away",
                speler,
                f"Schot van {away_name}",
                f"{speler['naam']} haalt uit."
            )

    for _ in range(2):

        if random.random() < 0.5:

            speler = kies_live_speler(
                home_starting_players
                or
                home_players
            )

            voeg_event(
                "corner",
                "home",
                speler,
                f"Corner voor {home_name}",
                f"{speler['naam']} legt de bal voor."
            )

        else:

            speler = kies_live_speler(
                away_starting_players
                or
                away_players
            )

            voeg_event(
                "corner",
                "away",
                speler,
                f"Corner voor {away_name}",
                f"{speler['naam']} legt de bal voor."
            )

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
                home_starting_players
                or
                home_players,
                "verdediging"
            )

            team = "home"

        else:

            speler = kies_live_speler(
                away_starting_players
                or
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
            random.random() < 0.5
        )

    # -----------------------------------------------------
    # LOGISCHE WISSELS
    # -----------------------------------------------------

    voeg_logische_wissel_toe(
        events,
        gebruikte_tijden,
        "home",
        home_players,
        home_starting_players,
        home_name
    )

    voeg_logische_wissel_toe(
        events,
        gebruikte_tijden,
        "away",
        away_players,
        away_starting_players,
        away_name
    )

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


# =========================================================
# SPELERS DIE ECHT GESPEELD HEBBEN
# =========================================================

def get_played_player_ids(
    live_match,
    team
):

    ids = set()

    team_data = live_match.get(
        team,
        {}
    )

    for item in team_data.get(
        "starting_lineup",
        []
    ):

        speler = item.get(
            "player"
        )

        if not speler:
            continue

        try:

            ids.add(
                int(speler["id"])
            )

        except (
            TypeError,
            ValueError
        ):
            continue

    for event in live_match.get(
        "events",
        []
    ):

        if event.get("team") != team:
            continue

        if event.get("type") != "substitution":
            continue

        player_id = event.get(
            "player_id"
        )

        if player_id is None:
            continue

        try:

            ids.add(
                int(player_id)
            )

        except (
            TypeError,
            ValueError
        ):
            continue

    return ids


def get_played_players(
    live_match,
    team,
    all_players
):

    all_players = [
        speler_naar_dict(speler)
        for speler in all_players
    ]

    played_ids = get_played_player_ids(
        live_match,
        team
    )

    return [
        speler
        for speler in all_players
        if int(speler["id"]) in played_ids
    ]


# =========================================================
# MOTM
# =========================================================

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

        played_ids = get_played_player_ids(
            live_match,
            team
        )

        for speler in spelers:

            if int(speler["id"]) not in played_ids:
                continue

            kandidaten[
                (
                    team,
                    int(speler["id"])
                )
            ] = {
                "player_id":
                    int(speler["id"]),

                "name":
                    speler["naam"],

                "team":
                    team,

                "goals":
                    0,

                "points":
                    0,

                "rating":
                    int(speler["rating"])
            }

    for event in live_match.get(
        "events",
        []
    ):

        team = event.get(
            "team"
        )

        player_id = event.get(
            "player_id"
        )

        try:

            if player_id is not None:
                player_id = int(
                    player_id
                )
            else:
                raise ValueError

        except (
            TypeError,
            ValueError
        ):

            speler_naam = event.get(
                "player"
            )

            player_id = None

            for key, kandidaat in kandidaten.items():

                if (
                    key[0] == team
                    and
                    kandidaat["name"]
                    ==
                    speler_naam
                ):

                    player_id = key[1]
                    break

            if player_id is None:
                continue

        key = (
            team,
            player_id
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

    geldige_kandidaten = list(
        kandidaten.values()
    )

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


# =========================================================
# INTERVIEWS
# =========================================================

def maak_interviewteksten(
    clubnaam,
    tegenstander,
    winst,
    gelijk,
    motm,
    extra_speler
):

    resultaten = []

    if winst:

        speler_teksten = [
            f"Dit was een lekkere overwinning voor {clubnaam}. We bleven rustig en maakten onze kansen goed af.",
            f"Ik denk dat we vandaag als team hebben laten zien wat we kunnen. De drie punten zijn het belangrijkste.",
            f"Het voelde alsof we steeds controle hielden. We mogen tevreden zijn met deze wedstrijd.",
            f"We hebben hard gewerkt voor dit resultaat. Nu moeten we dezelfde instelling meenemen naar de volgende wedstrijd.",
            f"Een mooie wedstrijd voor ons. Iedereen heeft zijn steentje bijgedragen en dat zie je terug in het resultaat."
        ]

        trainer_teksten = [
            f"Ik ben tevreden met hoe {clubnaam} de wedstrijd heeft aangepakt. We hebben op de belangrijke momenten toegeslagen.",
            f"De spelers hebben vandaag goed geluisterd en uitgevoerd wat we hadden afgesproken.",
            f"Tegen {tegenstander} was het belangrijk om geduldig te blijven. Dat hebben we goed gedaan.",
            f"De ploeg heeft karakter getoond. We bleven ons eigen spel spelen en zijn daarvoor beloond.",
            f"Dit resultaat geeft vertrouwen. We gaan de wedstrijd rustig analyseren en daarna vooruitkijken."
        ]

    elif gelijk:

        speler_teksten = [
            f"Tegen {tegenstander} was het zwaar. We hadden graag gewonnen, maar we pakken dit punt mee.",
            f"Er waren momenten waarop we de wedstrijd konden beslissen. Helaas lukte dat vandaag niet.",
            f"We hebben gevochten tot het einde. Het is geen perfecte uitslag, maar we blijven positief.",
            f"Het was een wedstrijd waarin beide teams kansen kregen. We moeten vooral naar de goede dingen kijken.",
            f"Een punt is niet waar we vooraf voor kwamen, maar we hebben in ieder geval niet opgegeven."
        ]

        trainer_teksten = [
            f"Ik vond dat {clubnaam} vandaag hard heeft gewerkt. We moeten alleen efficiënter worden.",
            f"Het was een gelijkwaardige wedstrijd. We nemen het punt mee en gaan verder.",
            f"We hadden graag meer uit deze wedstrijd gehaald, maar de spelers hebben tot het einde gestreden.",
            f"Tegen {tegenstander} kregen we niet alles cadeau. Het team bleef georganiseerd en dat vond ik goed.",
            f"We moeten vooral leren van de momenten waarop we kansen lieten liggen."
        ]

    else:

        speler_teksten = [
            f"Dit is natuurlijk niet het resultaat dat we wilden. We moeten nu snel reageren.",
            f"We hebben geprobeerd terug te komen in de wedstrijd, maar het zat vandaag niet mee.",
            f"Dit doet pijn, zeker omdat we hard hebben gewerkt. Volgende wedstrijd moet het beter.",
            f"We moeten deze nederlaag achter ons laten en focussen op wat hierna komt.",
            f"Vandaag kregen we het niet voor elkaar. Daar moeten we eerlijk over zijn."
        ]

        trainer_teksten = [
            f"De uitslag tegen {tegenstander} is teleurstellend. We moeten kritisch naar onze eigen wedstrijd kijken.",
            f"We hadden vandaag te weinig controle. Daar gaan we de komende dagen aan werken.",
            f"De ploeg bleef proberen, maar we waren niet goed genoeg op de beslissende momenten.",
            f"Dit was niet onze beste wedstrijd. We moeten herstellen en zorgen dat we de volgende wedstrijd beter voor de dag komen.",
            f"Ik neem de verantwoordelijkheid voor deze wedstrijd. We analyseren wat beter moet."
        ]

    extra_teksten = [
        f"{extra_speler} vond dat de ploeg vooral samen moest blijven spelen en elkaar moest blijven helpen.",
        f"{extra_speler} was tevreden over de inzet van het team en keek direct vooruit naar de volgende wedstrijd.",
        f"{extra_speler} benadrukte dat de sfeer in de groep goed blijft, ongeacht het resultaat.",
        f"{extra_speler} zag vooral ruimte voor verbetering en verwacht een reactie van de ploeg.",
        f"{extra_speler} vond dat de spelers veel energie hebben gegeven gedurende de hele wedstrijd."
    ]

    resultaten.append(
        (
            motm["name"],
            "Speler",
            clubnaam,
            random.choice(
                speler_teksten
            )
        )
    )

    resultaten.append(
        (
            "ClubMaster trainer",
            "Trainer",
            clubnaam,
            random.choice(
                trainer_teksten
            )
        )
    )

    if extra_speler:

        resultaten.append(
            (
                extra_speler,
                "Speler",
                clubnaam,
                random.choice(
                    extra_teksten
                )
            )
        )

    unieke = []
    gebruikte_teksten = set()

    for interview in resultaten:

        spreker, rol, club, tekst = interview

        if tekst in gebruikte_teksten:
            continue

        gebruikte_teksten.add(
            tekst
        )

        unieke.append(
            interview
        )

    return unieke[:3]


# =========================================================
# SPELERSTATISTIEKEN OPSLAAN
# =========================================================

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

    home_players = [
        speler_naar_dict(speler)
        for speler in home_players
    ]

    away_players = [
        speler_naar_dict(speler)
        for speler in away_players
    ]

    all_players = {
        (
            "home",
            int(speler["id"])
        ): speler
        for speler in home_players
    }

    all_players.update({
        (
            "away",
            int(speler["id"])
        ): speler
        for speler in away_players
    })

    # -----------------------------------------------------
    # WIE HEEFT ECHT GESPEELD?
    # -----------------------------------------------------

    played_players = []

    for team in [
        "home",
        "away"
    ]:

        team_players = (
            home_players
            if team == "home"
            else away_players
        )

        played_ids = get_played_player_ids(
            live_match,
            team
        )

        for player_id in played_ids:

            speler = all_players.get(
                (
                    team,
                    player_id
                )
            )

            if speler:

                played_players.append({
                    "team": team,
                    "player": speler
                })

    # -----------------------------------------------------
    # GOALS
    # -----------------------------------------------------

    goal_counts = {}

    for event in live_match.get(
        "events",
        []
    ):

        if event.get("type") != "goal":
            continue

        team = event.get(
            "team"
        )

        player_id = event.get(
            "player_id"
        )

        if player_id is None:

            speler_naam = event.get(
                "player"
            )

            gevonden = None

            for key, speler in all_players.items():

                if (
                    key[0] == team
                    and
                    speler["naam"] == speler_naam
                ):

                    gevonden = key[1]
                    break

            if gevonden is None:
                continue

            player_id = gevonden

        try:

            player_id = int(
                player_id
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        key = (
            team,
            player_id
        )

        goal_counts[key] = (
            goal_counts.get(
                key,
                0
            )
            +
            1
        )

    # -----------------------------------------------------
    # MOTM
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # SPELERS DIE GESPEELD HEBBEN
    # -----------------------------------------------------

    for item in played_players:

        team = item["team"]
        speler = item["player"]

        player_id = int(
            speler["id"]
        )

        aantal_goals = goal_counts.get(
            (
                team,
                player_id
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
            VALUES (
                ?, ?, 1, ?, ?
            )

            ON CONFLICT(
                player_id,
                maand
            )

            DO UPDATE SET
                wedstrijden =
                    wedstrijden + 1,

                doelpunten =
                    doelpunten
                    +
                    excluded.doelpunten,

                motm =
                    motm
                    +
                    excluded.motm
        """, (
            player_id,
            maand,
            aantal_goals,
            speler_motm
        ))

    # -----------------------------------------------------
    # MOTM OPSLAAN
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # INTERVIEWS
    # Alleen spelers die echt gespeeld hebben.
    # -----------------------------------------------------

    connection.execute("""
        DELETE FROM interviews
        WHERE match_id = ?
    """, (
        match_id,
    ))

    if motm:

        if motm["team"] == "home":

            eigen_club = (
                live_match["home"]["name"]
            )

            tegenstander = (
                live_match["away"]["name"]
            )

            eigen_team = "home"

        else:

            eigen_club = (
                live_match["away"]["name"]
            )

            tegenstander = (
                live_match["home"]["name"]
            )

            eigen_team = "away"

        winst = (
            (
                eigen_team == "home"
                and
                home_score > away_score
            )
            or
            (
                eigen_team == "away"
                and
                away_score > home_score
            )
        )

        gelijk = (
            home_score == away_score
        )

        eigen_spelers_die_gespeeld_hebben = (
            get_played_players(
                live_match,
                eigen_team,
                (
                    home_players
                    if eigen_team == "home"
                    else away_players
                )
            )
        )

        mogelijke_extra_spelers = [
            speler["naam"]
            for speler in
            eigen_spelers_die_gespeeld_hebben
            if int(speler["id"])
            !=
            int(motm["player_id"])
        ]

        extra_speler = (
            random.choice(
                mogelijke_extra_spelers
            )
            if mogelijke_extra_spelers
            else None
        )

        interviews = maak_interviewteksten(
            eigen_club,
            tegenstander,
            winst,
            gelijk,
            motm,
            extra_speler
        )

        for (
            spreker,
            rol,
            club_name,
            tekst
        ) in interviews:

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
                spreker,
                rol,
                club_name,
                tekst
            ))

    connection.commit()
    connection.close()


# =========================================================
# AI WEDSTRIJDEN
# =========================================================

def speel_ai_wedstrijden():

    user_club = get_user_club()

    if user_club is None:
        return

    connection = get_connection()

    wedstrijden = connection.execute("""
        SELECT
            matches.id,
            matches.home_club_id,
            matches.away_club_id,
            matches.gespeeld,
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

        WHERE matches.gespeeld = 0

        ORDER BY
            matches.speelronde,
            matches.id
    """).fetchall()

    connection.close()

    for match in wedstrijden:

        if user_club["id"] in [
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

        home_score, away_score = (
            bereken_wedstrijdscore(
                match["home_rating"],
                match["away_rating"]
            )
        )

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
                "at":
                    tijd,

                "minute":
                    live_minuut_voor_secondes(
                        tijd
                    ),

                "type":
                    "goal",

                "team":
                    team,

                "player":
                    speler["naam"],

                "player_id":
                    int(speler["id"]),

                "title":
                    f"GOAL! {clubnaam}",

                "text":
                    f"{speler['naam']} schiet de bal binnen."
            })

        for _ in range(home_score):

            speler = kies_live_speler(
                [
                    item["player"]
                    for item in home_lineup
                    if item.get("player")
                ],
                "aanval"
            )

            voeg_ai_goal(
                "home",
                speler,
                match["home_naam"],
                random.random() < 0.45
            )

        for _ in range(away_score):

            speler = kies_live_speler(
                [
                    item["player"]
                    for item in away_lineup
                    if item.get("player")
                ],
                "aanval"
            )

            voeg_ai_goal(
                "away",
                speler,
                match["away_naam"],
                random.random() < 0.45
            )

        # -------------------------------------------------
        # LOGISCHE AI-WISSELS
        # -------------------------------------------------

        voeg_logische_wissel_toe(
            events,
            gebruikte_tijden,
            "home",
            home_players,
            [
                item["player"]
                for item in home_lineup
                if item.get("player")
            ],
            match["home_naam"]
        )

        voeg_logische_wissel_toe(
            events,
            gebruikte_tijden,
            "away",
            away_players,
            [
                item["player"]
                for item in away_lineup
                if item.get("player")
            ],
            match["away_naam"]
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

        verwerk_spelerstatistieken(
            match["id"],
            match["datum"],
            ai_live_match,
            home_players,
            away_players
        )

        update_competition(
            match["home_club_id"],
            match["away_club_id"],
            home_score,
            away_score
        )


# =========================================================
# AI TRANSFERBIEDINGEN
# =========================================================

def genereer_ai_transferbiedingen():

    club = get_user_club()

    if club is None:
        return []

    progress = get_user_progress()

    vandaag = date.today().isoformat()

    if (
        progress["transfer_offer_date"]
        ==
        vandaag
    ):

        return progress["transfer_offers"]

    spelers = get_players_for_club(
        club["id"]
    )

    if not spelers:

        save_user_progress(
            transfer_offers=[],
            transfer_offer_date=vandaag
        )

        return []

    connection = get_connection()

    ai_clubs = connection.execute("""
        SELECT
            id,
            naam,
            logo,
            budget,
            rating
        FROM clubs
        WHERE id != ?
    """, (
        club["id"],
    )).fetchall()

    connection.close()

    if not ai_clubs:

        save_user_progress(
            transfer_offers=[],
            transfer_offer_date=vandaag
        )

        return []

    aantal_biedingen = random.randint(
        1,
        min(
            3,
            len(spelers),
            len(ai_clubs)
        )
    )

    gekozen_spelers = random.sample(
        spelers,
        aantal_biedingen
    )

    gekozen_clubs = random.sample(
        ai_clubs,
        min(
            aantal_biedingen,
            len(ai_clubs)
        )
    )

    biedingen = []

    for index, speler in enumerate(
        gekozen_spelers
    ):

        ai_club = gekozen_clubs[
            index % len(gekozen_clubs)
        ]

        marktwaarde = int(
            speler["marktwaarde"]
        )

        if int(speler["rating"]) >= 80:

            minimum_factor = 1.00
            maximum_factor = 1.30

        elif int(speler["rating"]) >= 75:

            minimum_factor = 0.95
            maximum_factor = 1.20

        else:

            minimum_factor = 0.85
            maximum_factor = 1.15

        bod = int(
            marktwaarde
            *
            random.uniform(
                minimum_factor,
                maximum_factor
            )
        )

        bod = max(
            100000,
            round(
                bod / 10000
            )
            *
            10000
        )

        if bod > int(ai_club["budget"]):
            continue

        biedingen.append({
            "id":
                f"{vandaag}-{speler['id']}-{ai_club['id']}",

            "player_id":
                int(speler["id"]),

            "player_name":
                speler["naam"],

            "position":
                speler["positie"],

            "rating":
                int(speler["rating"]),

            "market_value":
                marktwaarde,

            "from_club":
                club["naam"],

            "to_club":
                ai_club["naam"],

            "to_club_id":
                int(ai_club["id"]),

            "offer":
                bod,

            "date":
                datetime.now().strftime(
                    "%d-%m-%Y %H:%M"
                )
        })

    save_user_progress(
        transfer_offers=biedingen,
        transfer_offer_date=vandaag
    )

    return biedingen


# =========================================================
# HOME / LOGIN
# =========================================================

@app.route("/")
def home():

    if session.get("user_id"):

        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if session.get("user_id"):

        return redirect(
            url_for("dashboard")
        )

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_connection()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (
            username,
        )).fetchone()

        connection.close()

        if (
            user is None
            or
            not check_password_hash(
                user["password_hash"],
                password
            )
        ):

            error = (
                "Gebruikersnaam of wachtwoord is onjuist."
            )

        else:

            session.clear()

            session["user_id"] = (
                user["id"]
            )

            session["username"] = (
                user["username"]
            )

            return redirect(
                url_for("dashboard")
            )

    return render_template(
        "login.html",
        error=error
    )


@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if session.get("user_id"):

        return redirect(
            url_for("dashboard")
        )

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        password2 = request.form.get(
            "password2",
            ""
        )

        if len(username) < 3:

            error = (
                "Gebruikersnaam moet minimaal 3 tekens zijn."
            )

        elif len(password) < 6:

            error = (
                "Wachtwoord moet minimaal 6 tekens zijn."
            )

        elif password != password2:

            error = (
                "De wachtwoorden komen niet overeen."
            )

        else:

            connection = get_connection()

            try:

                cursor = connection.execute("""
                    INSERT INTO users (
                        username,
                        password_hash,
                        created_at
                    )
                    VALUES (?, ?, ?)
                """, (
                    username,
                    generate_password_hash(
                        password
                    ),
                    datetime.now().isoformat()
                ))

                connection.commit()

                user_id = cursor.lastrowid

                session.clear()

                session["user_id"] = (
                    user_id
                )

                session["username"] = (
                    username
                )

                connection.close()

                return redirect(
                    url_for("clubs_page")
                )

            except sqlite3.IntegrityError:

                connection.close()

                error = (
                    "Deze gebruikersnaam bestaat al."
                )

    return render_template(
        "register.html",
        error=error
    )


@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# CLUB KIEZEN
# =========================================================

@app.route("/clubs")
@login_required
def clubs_page():

    clubs = get_clubs()

    return render_template(
        "clubs.html",
        clubs=clubs
    )


@app.route(
    "/choose/<club_name>"
)
@login_required
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

    nieuwe_opstelling = {
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

    nieuwe_tactieken = {
        "formatie": "4-3-3",
        "speelstijl": "Gebalanceerd",
        "mentaliteit": "Gebalanceerd",
        "druk": "Normaal"
    }

    save_user_progress(
        lineup=nieuwe_opstelling,
        tactics=nieuwe_tactieken,
        transfer_history=[],
        transfer_offers=[],
        transfer_offer_date=None,
        club_id=club["id"],
        clear_transfer_offer_date=True
    )

    return redirect(
        url_for("dashboard")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    speel_ai_wedstrijden()

    club = get_user_club()

    if club is None:

        return render_template(
            "dashboard.html",
            club=None,
            interviews=[]
        )

    genereer_ai_transferbiedingen()

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
        LIMIT 3
    """).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        club=club,
        competitie=eigen_team,
        positie=positie,
        interviews=interviews
    )


# =========================================================
# SELECTIE
# =========================================================

@app.route("/selection")
@login_required
def selection():

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
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


# =========================================================
# STATISTIEKEN
# =========================================================

@app.route("/statistics")
@login_required
def statistics():

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
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
        recente_motm=recente_motm,
        interviews=interviews
    )


# =========================================================
# COMPETITIE
# =========================================================

@app.route("/competition")
@login_required
def competition():

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
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


# =========================================================
# WEDSTRIJDEN
# =========================================================

@app.route("/matches")
@login_required
def matches():

    # Na een reset mag de AI niet direct
    # de wedstrijden weer spelen.
    if not session.pop(
        "skip_ai_after_reset",
        False
    ):
        speel_ai_wedstrijden()

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
        )

    connection = get_connection()

    wedstrijden_db = connection.execute("""
        SELECT
            matches.id,
            matches.home_club_id,
            matches.away_club_id,
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

    for match in wedstrijden_db:

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
                match["home_club_id"],
                match["away_club_id"]
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


# =========================================================
# LIVE WEDSTRIJD OPENEN
# =========================================================

@app.route(
    "/play_match/<int:match_id>"
)
@login_required
def play_match(match_id):

    club = get_user_club()

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

    progress = get_user_progress()

    opgeslagen_opstelling = (
        progress["lineup"]
    )

    tactieken = (
        progress["tactics"]
    )

    if club["id"] == match["home_club_id"]:

        home_lineup = bouw_basiself(
            home_players,
            opgeslagen_opstelling
        )

        away_lineup = bouw_basiself(
            away_players
        )

        eigen_team = "home"

    else:

        home_lineup = bouw_basiself(
            home_players
        )

        away_lineup = bouw_basiself(
            away_players,
            opgeslagen_opstelling
        )

        eigen_team = "away"

    bestaande_live = session.get(
        "live_match"
    )

    # Voor de aftrap altijd opnieuw bouwen.
    if (
        bestaande_live is None
        or
        bestaande_live.get(
            "match_id"
        ) != match_id
        or
        bestaande_live.get(
            "started_at"
        ) is None
    ):

        events = genereer_live_events(
            home_players,
            away_players,
            match["home_naam"],
            match["away_naam"],
            match["home_rating"],
            match["away_rating"],
            home_lineup,
            away_lineup,
            tactieken,
            eigen_team
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
                events,

            "tactieken":
                tactieken
        }

        session["live_match"] = (
            bestaande_live
        )

        session.modified = True

    return render_template(
        "live_match.html",
        club=club,
        live_match=bestaande_live,
        tactieken=tactieken
    )


# =========================================================
# LIVE START
# =========================================================

@app.route(
    "/play_match/<int:match_id>/start",
    methods=["POST"]
)
@login_required
def start_live_match(match_id):

    club = get_user_club()

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


# =========================================================
# LIVE AFSLUITEN
# =========================================================

@app.route(
    "/play_match/<int:match_id>/finish",
    methods=["POST"]
)
@login_required
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

        return jsonify({
            "success": True,
            "redirect":
                url_for("matches")
        })

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
        "success": True,
        "home_score": home_score,
        "away_score": away_score,
        "redirect":
            url_for("matches")
    })


# =========================================================
# TRANSFERMARKT
# =========================================================

@app.route("/transfers")
@login_required
def transfers():

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
        )

    transfer_offers = (
        genereer_ai_transferbiedingen()
    )

    progress = get_user_progress()

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
        ORDER BY players.rating DESC
        LIMIT 50
    """, (
        club["id"],
    )).fetchall()

    connection.close()

    return render_template(
        "transfers.html",
        club=club,
        players=spelers,
        transfer_history=
            progress["transfer_history"],
        transfer_offers=
            transfer_offers
    )


# =========================================================
# AI BOD ACCEPTEREN
# =========================================================

@app.route(
    "/transfers/offer/<offer_id>/accept",
    methods=["POST"]
)
@login_required
def accept_transfer_offer(offer_id):

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
        )

    progress = get_user_progress()

    offers = progress[
        "transfer_offers"
    ]

    offer = next(
        (
            item
            for item in offers
            if item.get("id") == offer_id
        ),
        None
    )

    if offer is None:

        return redirect(
            url_for("transfers")
        )

    player_id = int(
        offer["player_id"]
    )

    connection = get_connection()

    player = connection.execute("""
        SELECT
            id,
            naam,
            club_id
        FROM players
        WHERE id = ?
    """, (
        player_id,
    )).fetchone()

    if player is None:

        connection.close()

        return redirect(
            url_for("transfers")
        )

    if int(player["club_id"]) != int(
        club["id"]
    ):

        connection.close()

        return redirect(
            url_for("transfers")
        )

    ai_club = connection.execute("""
        SELECT
            id,
            naam,
            budget
        FROM clubs
        WHERE id = ?
    """, (
        offer["to_club_id"],
    )).fetchone()

    if ai_club is None:

        connection.close()

        return redirect(
            url_for("transfers")
        )

    transferprijs = int(
        offer["offer"]
    )

    if int(ai_club["budget"]) < transferprijs:

        connection.close()

        offers = [
            item
            for item in offers
            if item.get("id") != offer_id
        ]

        save_user_progress(
            transfer_offers=offers
        )

        return redirect(
            url_for("transfers")
        )

    connection.execute("""
        UPDATE players
        SET club_id = ?
        WHERE id = ?
    """, (
        ai_club["id"],
        player_id
    ))

    connection.execute("""
        UPDATE clubs
        SET
            budget = budget + ?
        WHERE id = ?
    """, (
        transferprijs,
        club["id"]
    ))

    connection.execute("""
        UPDATE clubs
        SET
            budget = budget - ?
        WHERE id = ?
    """, (
        transferprijs,
        ai_club["id"]
    ))

    connection.commit()
    connection.close()

    offers = [
        item
        for item in offers
        if item.get("id") != offer_id
    ]

    history = progress[
        "transfer_history"
    ]

    history.insert(
        0,
        {
            "player_name":
                offer["player_name"],

            "position":
                offer["position"],

            "rating":
                offer["rating"],

            "from_club":
                club["naam"],

            "to_club":
                offer["to_club"],

            "price":
                transferprijs,

            "date":
                offer["date"],

            "test":
                False
        }
    )

    save_user_progress(
        transfer_history=history[:50],
        transfer_offers=offers
    )

    return redirect(
        url_for("transfers")
    )


# =========================================================
# AI BOD AFWIJZEN
# =========================================================

@app.route(
    "/transfers/offer/<offer_id>/reject",
    methods=["POST"]
)
@login_required
def reject_transfer_offer(offer_id):

    progress = get_user_progress()

    offers = [
        item
        for item in progress["transfer_offers"]
        if item.get("id") != offer_id
    ]

    save_user_progress(
        transfer_offers=offers
    )

    return redirect(
        url_for("transfers")
    )


# =========================================================
# SPELER KOPEN
# =========================================================

@app.route(
    "/transfers/buy/<int:player_id>",
    methods=["POST"]
)
@login_required
def buy_transfer(player_id):

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
        )

    progress = get_user_progress()

    transfer_history = (
        progress["transfer_history"]
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

    oude_club_id = int(
        player["club_id"]
    )

    connection.execute("""
        UPDATE players
        SET club_id = ?
        WHERE id = ?
    """, (
        club["id"],
        player_id
    ))

    connection.execute("""
        UPDATE clubs
        SET
            budget = budget - ?
        WHERE id = ?
    """, (
        transferprijs,
        club["id"]
    ))

    connection.execute("""
        UPDATE clubs
        SET
            budget = budget + ?
        WHERE id = ?
    """, (
        transferprijs,
        oude_club_id
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

    offers = [
        offer
        for offer in progress["transfer_offers"]
        if int(
            offer.get("player_id", -1)
        ) != player_id
    ]

    save_user_progress(
        transfer_history=
            transfer_history[:50],
        transfer_offers=
            offers
    )

    return redirect(
        url_for("transfers")
    )


# =========================================================
# SPELER DETAIL
# =========================================================

@app.route(
    "/player/<int:player_id>"
)
@login_required
def player_detail(player_id):

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
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


# =========================================================
# CLUB VIEWER
# =========================================================

@app.route("/club-viewer")
@login_required
def club_viewer():

    eigen_club = get_user_club()

    if eigen_club is None:

        return redirect(
            url_for("clubs_page")
        )

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
        ORDER BY rating DESC, naam ASC
    """).fetchall()

    connection.close()

    return render_template(
        "club_viewer.html",
        eigen_club=eigen_club,
        clubs=clubs
    )


@app.route(
    "/club-viewer/<int:club_id>"
)
@login_required
def club_viewer_detail(club_id):

    eigen_club = get_user_club()

    if eigen_club is None:

        return redirect(
            url_for("clubs_page")
        )

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
        WHERE id = ?
    """, (
        club_id,
    )).fetchone()

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
        ORDER BY rating DESC, naam ASC
    """, (
        club_id,
    )).fetchall()

    connection.close()

    if club is None:

        return "Club niet gevonden", 404

    return render_template(
        "club_viewer_detail.html",
        eigen_club=eigen_club,
        club=club,
        players=players
    )


# =========================================================
# TACTIEKEN
# =========================================================

@app.route(
    "/tactics",
    methods=["GET", "POST"]
)
@login_required
def tactics():

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
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

        nieuwe_tactieken = {

            "formatie":
                formatie,

            "speelstijl":
                speelstijl,

            "mentaliteit":
                mentaliteit,

            "druk":
                druk_zetten
        }

        save_user_progress(
            tactics=nieuwe_tactieken
        )

        terug_naar = (
            request.args.get("next")
        )

        if not terug_naar:

            terug_naar = session.pop(
                "_tactics_next",
                None
            )

        terug_naar = (
            geldige_interne_url(
                terug_naar
            )
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

    progress = get_user_progress()

    tactieken = progress[
        "tactics"
    ]

    return render_template(
        "tactics.html",
        club=club,
        formations=formaties,
        speelstijlen=speelstijlen,
        mentaliteiten=mentaliteiten,
        druk=druk,
        tactieken=tactieken
    )


# =========================================================
# OPSTELLING
# =========================================================

@app.route(
    "/lineup",
    methods=["GET", "POST"]
)
@login_required
def lineup():

    club = get_user_club()

    if club is None:

        return redirect(
            url_for("clubs_page")
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

        save_user_progress(
            lineup=opstelling
        )

        terug_naar = (
            request.args.get("next")
        )

        if not terug_naar:

            terug_naar = session.pop(
                "_lineup_next",
                None
            )

        terug_naar = (
            geldige_interne_url(
                terug_naar
            )
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

    progress = get_user_progress()

    opstelling = progress[
        "lineup"
    ]

    if not opstelling:

        opstelling = {
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

    return render_template(
        "lineup.html",
        club=club,
        players=spelers,
        opstelling=opstelling
    )


# =========================================================
# RESET
# =========================================================

@app.route("/reset-test")
@login_required
def reset_test_route():

    connection = get_connection()

    # ALLE wedstrijden resetten
    connection.execute("""
        UPDATE matches
        SET
            home_score = 0,
            away_score = 0,
            gespeeld = 0
    """)

    # Competitie resetten
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

    # Alle spelerstatistieken resetten
    connection.execute("""
        DELETE FROM player_stats
    """)

    # Alle MOTM-awards resetten
    connection.execute("""
        DELETE FROM match_awards
    """)

    # Alle interviews resetten
    connection.execute("""
        DELETE FROM interviews
    """)

    connection.commit()
    connection.close()

    # Eventuele live wedstrijd verwijderen
    session.pop(
        "live_match",
        None
    )

    # AI mag na de reset niet direct wedstrijden spelen
    session["skip_ai_after_reset"] = True

    return redirect(
        url_for("matches")
    )

# =========================================================
# BROWSER
# =========================================================

def open_browser():

    webbrowser.open_new(
        "http://127.0.0.1:5000"
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    create_users_table()

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