document.addEventListener("DOMContentLoaded", () => {

    const data = window.liveMatchData;

    if (!data) {
        return;
    }


    /* =========================
       INSTELLINGEN
       ========================= */

    const FIRST_HALF_SECONDS = 20;
    const HALFTIME_SECONDS = 4;
    const SECOND_HALF_SECONDS = 20;

    const TOTAL_SECONDS =
        FIRST_HALF_SECONDS +
        HALFTIME_SECONDS +
        SECOND_HALF_SECONDS;


    /* =========================
       ELEMENTEN
       ========================= */

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


    /* =========================
       STATUS
       ========================= */

    let shownEvents = 0;

    let halftimeShown = false;
    let secondHalfShown = false;
    let finished = false;

    let homeScore = 0;
    let awayScore = 0;

    let homeAttacks = 0;
    let awayAttacks = 0;

    let homeShots = 0;
    let awayShots = 0;

    let homeCorners = 0;
    let awayCorners = 0;


    /* =========================
       HELPERS
       ========================= */

    function escapeHtml(value) {

        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function formatMatchTime(totalSeconds) {

        let minutes = Math.floor(totalSeconds / 60);

        let seconds = Math.floor(totalSeconds % 60);

        return (
            String(minutes).padStart(2, "0") +
            ":" +
            String(seconds).padStart(2, "0")
        );
    }


    function getTeamName(side) {

        if (side === "home") {
            return data.home.name;
        }

        return data.away.name;
    }


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

        return icons[type] || "•";
    }


    function addSystemEvent(minute, title, text) {

        const event = document.createElement("div");

        event.className = "live-event system-event";

        event.innerHTML = `
            <div class="event-minute">
                ${escapeHtml(minute)}'
            </div>

            <div class="event-icon">
                ⏱️
            </div>

            <div class="event-content">
                <strong>${escapeHtml(title)}</strong>
                <span>${escapeHtml(text)}</span>
            </div>
        `;

        eventsContainer.prepend(event);

    }


    function addEvent(eventData) {

        const event = document.createElement("div");

        let teamClass =
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
                ${getEventIcon(eventData.type)}
            </div>

            <div class="event-content">

                <strong>
                    ${escapeHtml(eventData.title)}
                </strong>

                <span>
                    ${escapeHtml(eventData.text)}
                </span>

            </div>
        `;


        eventsContainer.prepend(event);

    }


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


    function processEvent(eventData) {

        if (eventData.type === "goal") {

            if (eventData.team === "home") {
                homeScore++;
            } else {
                awayScore++;
            }

            homeScoreElement.textContent =
                homeScore;

            awayScoreElement.textContent =
                awayScore;

        }


        if (eventData.type === "attack") {

            if (eventData.team === "home") {
                homeAttacks++;
            } else {
                awayAttacks++;
            }

        }


        if (
            eventData.type === "shot" ||
            eventData.type === "chance" ||
            eventData.type === "goal"
        ) {

            if (eventData.team === "home") {
                homeShots++;
            } else {
                awayShots++;
            }

        }


        if (eventData.type === "corner") {

            if (eventData.team === "home") {
                homeCorners++;
            } else {
                awayCorners++;
            }

        }


        updateStats();

        addEvent(eventData);

    }


    /* =========================
       STARTTIJD
       ========================= */

    const startedAt =
        Number(data.started_at);


    /* =========================
       TICK
       ========================= */

    function updateMatch() {

        if (finished) {
            return;
        }


        const now =
            Date.now() / 1000;


        const elapsed =
            now - startedAt;


        /* =========================
           1E HELFT
           ========================= */

        if (
            elapsed >= 0 &&
            elapsed < FIRST_HALF_SECONDS
        ) {

            statusElement.textContent =
                "1e helft";


            const percentage =
                elapsed / FIRST_HALF_SECONDS;


            const matchSeconds =
                percentage * 45 * 60;


            minuteElement.textContent =
                formatMatchTime(matchSeconds);


            progressElement.style.width =
                `${(elapsed / TOTAL_SECONDS) * 100}%`;

        }


        /* =========================
           RUST
           ========================= */

        else if (
            elapsed >= FIRST_HALF_SECONDS &&
            elapsed <
                FIRST_HALF_SECONDS +
                HALFTIME_SECONDS
        ) {

            statusElement.textContent =
                "Rust";


            minuteElement.textContent =
                "45:00";


            progressElement.style.width =
                `${(elapsed / TOTAL_SECONDS) * 100}%`;


            if (!halftimeShown) {

                halftimeShown = true;

                addSystemEvent(
                    "45",
                    "Rust",
                    `Rust in ${data.home.name} ${homeScore} - ${awayScore} ${data.away.name}`
                );

            }

        }


        /* =========================
           2E HELFT
           ========================= */

        else if (
            elapsed >=
                FIRST_HALF_SECONDS +
                HALFTIME_SECONDS &&
            elapsed < TOTAL_SECONDS
        ) {

            statusElement.textContent =
                "2e helft";


            if (!secondHalfShown) {

                secondHalfShown = true;

                addSystemEvent(
                    "46",
                    "2e helft",
                    "De wedstrijd wordt hervat."
                );

            }


            const secondHalfElapsed =
                elapsed -
                FIRST_HALF_SECONDS -
                HALFTIME_SECONDS;


            const percentage =
                secondHalfElapsed /
                SECOND_HALF_SECONDS;


            const matchSeconds =
                (45 * 60) +
                (percentage * 45 * 60);


            minuteElement.textContent =
                formatMatchTime(matchSeconds);


            progressElement.style.width =
                `${(elapsed / TOTAL_SECONDS) * 100}%`;

        }


        /* =========================
           EINDE
           ========================= */

        else {

            minuteElement.textContent =
                "90:00";

            statusElement.textContent =
                "Einde";

            progressElement.style.width =
                "100%";


            if (!finished) {

                finishMatch();

            }

            return;

        }


        /* =========================
           EVENTS
           ========================= */

        const events =
            Array.isArray(data.events)
                ? data.events
                : [];


        while (
            shownEvents < events.length &&
            events[shownEvents].at <= elapsed
        ) {

            processEvent(
                events[shownEvents]
            );

            shownEvents++;

            eventCountElement.textContent =
                `${shownEvents} events`;

        }

    }


    /* =========================
       WEDSTRIJD AFRONDEN
       ========================= */

    async function finishMatch() {

        if (finished) {
            return;
        }

        finished = true;


        addSystemEvent(
            "90",
            "Einde wedstrijd",
            `${data.home.name} ${homeScore} - ${awayScore} ${data.away.name}`
        );


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


            if (result.success) {

                setTimeout(() => {

                    window.location.href =
                        result.redirect;

                }, 2500);

            }

        } catch (error) {

            console.error(
                "Kon wedstrijd niet opslaan:",
                error
            );

        }

    }


    /* =========================
       START
       ========================= */

    updateMatch();

    setInterval(
        updateMatch,
        100
    );

});