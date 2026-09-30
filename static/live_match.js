document.addEventListener("DOMContentLoaded", () => {

    const data = window.liveMatchData;

    if (!data) {
        return;
    }


    // =========================
    // TIJDEN
    // =========================

    const FIRST_HALF_SECONDS = 15;
    const HALFTIME_SECONDS = 5;
    const SECOND_HALF_SECONDS = 15;

    const SECOND_HALF_START =
        FIRST_HALF_SECONDS +
        HALFTIME_SECONDS;

    const TOTAL_MATCH_SECONDS =
        FIRST_HALF_SECONDS +
        HALFTIME_SECONDS +
        SECOND_HALF_SECONDS;


    // =========================
    // ELEMENTEN
    // =========================

    const preMatch =
        document.getElementById("pre-match");

    const startButton =
        document.getElementById("start-match-button");

    const liveContent =
        document.getElementById("live-content");

    const minuteElement =
        document.getElementById("match-minute");

    const homeScoreElement =
        document.getElementById("home-score");

    const awayScoreElement =
        document.getElementById("away-score");

    const statusElement =
        document.getElementById("match-status");

    const progressElement =
        document.getElementById("live-progress");

    const eventsContainer =
        document.getElementById("live-events");

    const eventCountElement =
        document.getElementById("event-count");

    const finishedElement =
        document.getElementById("match-finished");

    const finalResultElement =
        document.getElementById("final-result");


    const homeAttackElement =
        document.getElementById("home-attacks");

    const awayAttackElement =
        document.getElementById("away-attacks");

    const homeShotsElement =
        document.getElementById("home-shots");

    const awayShotsElement =
        document.getElementById("away-shots");

    const homeCornersElement =
        document.getElementById("home-corners");

    const awayCornersElement =
        document.getElementById("away-corners");


    // =========================
    // STARTTIJD
    // =========================

    let startedAt = null;

    if (
        data.started_at !== null &&
        data.started_at !== undefined &&
        data.started_at !== ""
    ) {

        const parsedStart =
            Number(data.started_at);

        if (
            Number.isFinite(parsedStart) &&
            parsedStart > 0
        ) {

            startedAt = parsedStart;
        }
    }


    let matchStarted =
        startedAt !== null;

    let finished = false;

    let halftimeShown = false;

    let secondHalfShown = false;

    let finishRequestSent = false;


    // =========================
    // SCORE EN STATS
    // =========================

    let homeScore = 0;
    let awayScore = 0;

    let homeAttacks = 0;
    let awayAttacks = 0;

    let homeShots = 0;
    let awayShots = 0;

    let homeCorners = 0;
    let awayCorners = 0;


    // =========================
    // EVENTS
    // =========================

    const events =
        Array.isArray(data.events)
            ? data.events
            : [];

    const shownEventIndexes =
        new Set();


    // =========================
    // HTML VEILIG MAKEN
    // =========================

    function escapeHtml(value) {

        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    // =========================
    // TIJD FORMATTEREN
    // =========================

    function formatMatchTime(
        totalSeconds
    ) {

        const minutes =
            Math.floor(
                totalSeconds / 60
            );

        const seconds =
            Math.floor(
                totalSeconds % 60
            );

        return (
            String(minutes).padStart(2, "0")
            +
            ":"
            +
            String(seconds).padStart(2, "0")
        );
    }


    // =========================
    // ICOONTJES
    // =========================

    function getEventIcon(type) {

        const icons = {

            attack: "🔥",

            chance: "🎯",

            shot: "💥",

            goal: "⚽",

            yellow: "🟨",

            red: "🟥",

            substitution: "🔄",

            injury: "🩹",

            save: "🧤",

            corner: "🏳️",

            offside: "🚩"
        };

        return (
            icons[type]
            ||
            "•"
        );
    }


    // =========================
    // SYSTEM EVENT
    // =========================

    function addSystemEvent(
        minute,
        title,
        text
    ) {

        const event =
            document.createElement("div");

        event.className =
            "live-event system-event";

        event.innerHTML = `

            <div class="event-minute">
                ${escapeHtml(minute)}'
            </div>

            <div class="event-icon">
                ⏱️
            </div>

            <div class="event-content">

                <strong>
                    ${escapeHtml(title)}
                </strong>

                <span>
                    ${escapeHtml(text)}
                </span>

            </div>
        `;

        eventsContainer.prepend(event);
    }


    // =========================
    // NORMAAL EVENT
    // =========================

    function addEvent(
        eventData
    ) {

        const event =
            document.createElement("div");

        const teamClass =
            eventData.team === "home"
                ? "home-event"
                : "away-event";

        event.className =
            `live-event ${teamClass} event-${eventData.type}`;

        event.innerHTML = `

            <div class="event-minute">
                ${escapeHtml(eventData.minute)}'
            </div>

            <div class="event-icon">
                ${getEventIcon(
                    eventData.type
                )}
            </div>

            <div class="event-content">

                <strong>
                    ${escapeHtml(
                        eventData.title
                    )}
                </strong>

                <span>
                    ${escapeHtml(
                        eventData.text
                    )}
                </span>

            </div>
        `;

        eventsContainer.prepend(event);
    }


    // =========================
    // SCORE RESETTEN
    // =========================

    function resetMatchValues() {

        homeScore = 0;
        awayScore = 0;

        homeAttacks = 0;
        awayAttacks = 0;

        homeShots = 0;
        awayShots = 0;

        homeCorners = 0;
        awayCorners = 0;

        shownEventIndexes.clear();

        halftimeShown = false;

        secondHalfShown = false;

        finished = false;

        finishRequestSent = false;

        updateScore();

        updateStats();
    }


    // =========================
    // SCORE
    // =========================

    function updateScore() {

        homeScoreElement.textContent =
            homeScore;

        awayScoreElement.textContent =
            awayScore;
    }


    // =========================
    // STATS
    // =========================

    function updateStats() {

        homeAttackElement.textContent =
            homeAttacks;

        awayAttackElement.textContent =
            awayAttacks;

        homeShotsElement.textContent =
            homeShots;

        awayShotsElement.textContent =
            awayShots;

        homeCornersElement.textContent =
            homeCorners;

        awayCornersElement.textContent =
            awayCorners;
    }


    // =========================
    // EVENT VERWERKEN
    // =========================

    function processEvent(
        eventData
    ) {

        if (
            eventData.type === "goal"
        ) {

            if (
                eventData.team === "home"
            ) {

                homeScore++;

            } else {

                awayScore++;
            }

            updateScore();
        }


        if (
            eventData.type === "attack"
        ) {

            if (
                eventData.team === "home"
            ) {

                homeAttacks++;

            } else {

                awayAttacks++;
            }
        }


        if (
            eventData.type === "shot"
            ||
            eventData.type === "chance"
            ||
            eventData.type === "goal"
        ) {

            if (
                eventData.team === "home"
            ) {

                homeShots++;

            } else {

                awayShots++;
            }
        }


        if (
            eventData.type === "corner"
        ) {

            if (
                eventData.team === "home"
            ) {

                homeCorners++;

            } else {

                awayCorners++;
            }
        }


        updateStats();

        addEvent(
            eventData
        );
    }


    // =========================
    // ALLE EVENT GEGEVENS OPNIEUW
    // BIJ PAGINA VERNIEUWEN
    // =========================

    function rebuildCurrentStats(
        elapsed
    ) {

        resetMatchValues();


        for (
            let index = 0;
            index < events.length;
            index++
        ) {

            const event =
                events[index];


            if (
                Number(event.at) > elapsed
            ) {
                continue;
            }


            if (
                Number(event.at) >=
                    FIRST_HALF_SECONDS
                &&
                Number(event.at) <
                    SECOND_HALF_START
            ) {

                continue;
            }


            processEvent(
                event
            );

            shownEventIndexes.add(
                index
            );
        }
    }


    // =========================
    // EVENT COUNT
    // =========================

    function updateEventCount() {

        eventCountElement.textContent =
            `${shownEventIndexes.size} events`;
    }


    // =========================
    // EVENTS VERWERKEN
    // =========================

    function processEvents(
        elapsed
    ) {

        for (
            let index = 0;
            index < events.length;
            index++
        ) {

            const event =
                events[index];

            const eventTime =
                Number(event.at);


            if (
                !Number.isFinite(eventTime)
            ) {
                continue;
            }


            if (
                eventTime > elapsed
            ) {
                continue;
            }


            if (
                eventTime >= FIRST_HALF_SECONDS
                &&
                eventTime < SECOND_HALF_START
            ) {
                continue;
            }


            if (
                shownEventIndexes.has(index)
            ) {
                continue;
            }


            shownEventIndexes.add(index);

            processEvent(
                event
            );

            updateEventCount();
        }
    }


    // =========================
    // LIVE WEDSTRIJD
    // =========================

    function updateMatch() {

        if (
            !matchStarted ||
            startedAt === null ||
            finished
        ) {

            return;
        }


        const now =
            Date.now() / 1000;


        let elapsed =
            now - startedAt;


        if (elapsed < 0) {
            elapsed = 0;
        }


        // =========================
        // EINDE
        // =========================

        if (
            elapsed >=
            TOTAL_MATCH_SECONDS
        ) {

            minuteElement.textContent =
                "90:00";

            statusElement.textContent =
                "Einde";

            progressElement.style.width =
                "100%";


            processEvents(
                TOTAL_MATCH_SECONDS
            );


            finishMatch();

            return;
        }


        // =========================
        // EERSTE HELFT
        // =========================

        if (
            elapsed < FIRST_HALF_SECONDS
        ) {

            statusElement.textContent =
                "1e helft";


            const percentage =
                elapsed /
                FIRST_HALF_SECONDS;


            const matchSeconds =
                percentage *
                45 *
                60;


            minuteElement.textContent =
                formatMatchTime(
                    matchSeconds
                );


            progressElement.style.width =
                `${(
                    elapsed /
                    TOTAL_MATCH_SECONDS
                ) * 100}%`;


            processEvents(
                elapsed
            );


            return;
        }


        // =========================
        // RUST
        // =========================

        if (
            elapsed >= FIRST_HALF_SECONDS
            &&
            elapsed < SECOND_HALF_START
        ) {

            statusElement.textContent =
                "Rust";

            minuteElement.textContent =
                "45:00";


            progressElement.style.width =
                `${(
                    elapsed /
                    TOTAL_MATCH_SECONDS
                ) * 100}%`;


            if (!halftimeShown) {

                halftimeShown = true;


                addSystemEvent(
                    "45",
                    "Rust",
                    `${data.home.name} ${homeScore} - ${awayScore} ${data.away.name}`
                );
            }


            // Geen gebeurtenissen tijdens rust.
            return;
        }


        // =========================
        // TWEEDE HELFT
        // =========================

        if (
            elapsed >= SECOND_HALF_START
            &&
            elapsed < TOTAL_MATCH_SECONDS
        ) {

            statusElement.textContent =
                "2e helft";


            if (!secondHalfShown) {

                secondHalfShown = true;


                addSystemEvent(
                    "46",
                    "Tweede helft",
                    "De scheidsrechter fluit voor de hervatting."
                );
            }


            const tweedeHelftElapsed =
                elapsed -
                SECOND_HALF_START;


            const percentage =
                tweedeHelftElapsed /
                SECOND_HALF_SECONDS;


            const matchSeconds =
                45 * 60
                +
                (
                    percentage *
                    45 *
                    60
                );


            minuteElement.textContent =
                formatMatchTime(
                    matchSeconds
                );


            progressElement.style.width =
                `${(
                    elapsed /
                    TOTAL_MATCH_SECONDS
                ) * 100}%`;


            processEvents(
                elapsed
            );
        }
    }


    // =========================
    // WEDSTRIJD STARTEN
    // =========================

    async function startMatch() {

        if (
            matchStarted ||
            finished
        ) {
            return;
        }


        startButton.disabled =
            true;

        startButton.textContent =
            "Wedstrijd starten...";


        try {

            const response =
                await fetch(
                    `/play_match/${data.match_id}/start`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        }
                    }
                );


            const result =
                await response.json();


            if (
                !response.ok ||
                !result.success
            ) {

                throw new Error(
                    result.error ||
                    "De wedstrijd kon niet worden gestart."
                );
            }


            // De ENIGE echte starttijd gebruiken.
            startedAt =
                Number(result.started_at);


            if (
                !Number.isFinite(startedAt) ||
                startedAt <= 0
            ) {

                throw new Error(
                    "De server heeft geen geldige starttijd gegeven."
                );
            }


            matchStarted = true;


            // Nieuwe events van de server ophalen.
            if (
                Array.isArray(result.events)
            ) {

                data.events =
                    result.events;

                events.length = 0;

                for (
                    const event of result.events
                ) {

                    events.push(event);
                }
            }


            resetMatchValues();


            // Voorbeschouwing weg.
            if (preMatch) {

                preMatch.classList.add(
                    "hidden"
                );
            }


            // Live gedeelte tonen.
            if (liveContent) {

                liveContent.classList.remove(
                    "hidden"
                );
            }


            addSystemEvent(
                "0",
                "Aftrap",
                `${data.home.name} - ${data.away.name}`
            );


            startButton.textContent =
                "Wedstrijd bezig";


            updateMatch();


        } catch (error) {

            console.error(error);


            startButton.disabled =
                false;

            startButton.textContent =
                "▶️ Begin wedstrijd";


            alert(
                error.message
            );
        }
    }


    // =========================
    // WEDSTRIJD OPSLAAN
    // =========================

    async function finishMatch() {

        if (
            finishRequestSent
        ) {
            return;
        }


        finishRequestSent = true;

        finished = true;


        statusElement.textContent =
            "Einde";


        minuteElement.textContent =
            "90:00";


        progressElement.style.width =
            "100%";


        if (
            !shownEventIndexes.has(
                "finished"
            )
        ) {

            shownEventIndexes.add(
                "finished"
            );


            addSystemEvent(
                "90",
                "Einde wedstrijd",
                `${data.home.name} ${homeScore} - ${awayScore} ${data.away.name}`
            );
        }


        finalResultElement.textContent =
            `${data.home.name} ${homeScore} - ${awayScore} ${data.away.name}`;


        finishedElement.classList.remove(
            "hidden"
        );


        try {

            const response =
                await fetch(
                    `/play_match/${data.match_id}/finish`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        }
                    }
                );


            const result =
                await response.json();


            if (
                result.success &&
                result.redirect
            ) {

                setTimeout(
                    () => {

                        window.location.href =
                            result.redirect;

                    },
                    2500
                );

            } else {

                finishRequestSent = false;
                finished = false;

                console.error(
                    "Wedstrijd kon niet worden opgeslagen.",
                    result
                );
            }


        } catch (error) {

            finishRequestSent = false;
            finished = false;

            console.error(
                "Fout bij opslaan wedstrijd:",
                error
            );
        }
    }


    // =========================
    // KNOP
    // =========================

    if (startButton) {

        startButton.addEventListener(
            "click",
            startMatch
        );
    }


    // =========================
    // BEGINSTATUS
    // =========================

    if (
        matchStarted &&
        startedAt !== null
    ) {

        if (preMatch) {

            preMatch.classList.add(
                "hidden"
            );
        }


        if (liveContent) {

            liveContent.classList.remove(
                "hidden"
            );
        }


        const now =
            Date.now() / 1000;


        let elapsed =
            now - startedAt;


        if (elapsed < 0) {
            elapsed = 0;
        }


        // Bestaande gebeurtenissen opnieuw
        // in de juiste score/stats verwerken.
        rebuildCurrentStats(
            Math.min(
                elapsed,
                TOTAL_MATCH_SECONDS
            )
        );


        updateScore();

        updateStats();

        updateEventCount();

        updateMatch();

    } else {

        // Nog niet gestart.
        if (preMatch) {

            preMatch.classList.remove(
                "hidden"
            );
        }


        if (liveContent) {

            liveContent.classList.add(
                "hidden"
            );
        }


        minuteElement.textContent =
            "00:00";

        statusElement.textContent =
            "Wedstrijd nog niet begonnen";


        progressElement.style.width =
            "0%";
    }


    // =========================
    // TIMER
    // =========================

    setInterval(
        updateMatch,
        100
    );

});