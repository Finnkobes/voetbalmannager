document.addEventListener("DOMContentLoaded", () => {

    const players = document.querySelectorAll(".player-bar");
    const slots = document.querySelectorAll(".position-slot");

    let draggedPlayer = null;


    /*
     * SPELER SLEPEN
     */

    players.forEach(player => {

        player.addEventListener("dragstart", event => {

            draggedPlayer = player;

            player.classList.add("dragging");

            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData(
                "text/plain",
                player.dataset.playerId
            );
        });


        player.addEventListener("dragend", () => {

            player.classList.remove("dragging");

            draggedPlayer = null;

            slots.forEach(slot => {
                slot.classList.remove("drag-over");
            });

        });

    });


    /*
     * POSITIE SLEPEN
     */

    slots.forEach(slot => {

        slot.addEventListener("dragover", event => {

            event.preventDefault();

            if (!draggedPlayer) {
                return;
            }

            slot.classList.add("drag-over");
        });


        slot.addEventListener("dragleave", () => {

            slot.classList.remove("drag-over");

        });


        slot.addEventListener("drop", event => {

            event.preventDefault();

            slot.classList.remove("drag-over");

            if (!draggedPlayer) {
                return;
            }

            const playerId = draggedPlayer.dataset.playerId;
            const playerName = draggedPlayer.dataset.playerName;
            const playerRating = draggedPlayer.dataset.playerRating;

            const oldSlot = document.querySelector(
                `.position-slot[data-player-id="${playerId}"]`
            );


            /*
             * ALS DE SPELER AL OP HET VELD STAAT
             * VERPLAATSEN WE HEM.
             */

            if (oldSlot && oldSlot !== slot) {

                oldSlot.dataset.playerId = "";

                oldSlot.querySelector(".drop-zone").innerHTML = `
                    <span class="empty-position">
                        Sleep speler
                    </span>
                `;

                updateInput(oldSlot);

            }


            /*
             * ALS ER AL EEN SPELER OP DE NIEUWE POSITIE STAAT
             * WISSELEN WE DE SPELERS.
             */

            const existingPlayerId = slot.dataset.playerId;

            if (
                existingPlayerId &&
                existingPlayerId !== playerId
            ) {

                const existingPlayer = document.querySelector(
                    `.player-bar[data-player-id="${existingPlayerId}"]`
                );

                if (existingPlayer) {

                    const oldPlayerName =
                        existingPlayer.dataset.playerName;

                    const oldPlayerRating =
                        existingPlayer.dataset.playerRating;


                    if (oldSlot) {

                        oldSlot.dataset.playerId =
                            existingPlayerId;

                        oldSlot.querySelector(".drop-zone").innerHTML = `
                            <div class="field-player">
                                <strong>${oldPlayerName}</strong>
                                <span>${oldPlayerRating}</span>
                            </div>
                        `;

                        updateInput(oldSlot);

                    } else {

                        existingPlayer.classList.remove("on-field");

                    }

                }

            }


            /*
             * NIEUWE SPELER OP POSITIE
             */

            slot.dataset.playerId = playerId;

            slot.querySelector(".drop-zone").innerHTML = `
                <div class="field-player">
                    <strong>${playerName}</strong>
                    <span>${playerRating}</span>
                </div>
            `;

            draggedPlayer.classList.add("on-field");

            updateInput(slot);

            draggedPlayer = null;

        });

    });


    /*
     * INPUT BIJWERKEN
     */

    function updateInput(slot) {

        const slotName = slot.dataset.slot;

        const input = document.getElementById(
            `input-${slotName}`
        );

        if (!input) {
            return;
        }

        input.value = slot.dataset.playerId || "";

    }


    /*
     * BESTAANDE OPSTELLING TERUGZETTEN
     *
     * De waarden die Flask vanuit de session
     * doorgeeft worden hier gebruikt.
     */

    const savedLineup = window.savedLineup || {};

    slots.forEach(slot => {

        const slotName = slot.dataset.slot;

        const playerId = savedLineup[slotName];

        if (!playerId) {
            return;
        }

        const player = document.querySelector(
            `.player-bar[data-player-id="${playerId}"]`
        );

        if (!player) {
            return;
        }

        const playerName = player.dataset.playerName;
        const playerRating = player.dataset.playerRating;

        slot.dataset.playerId = playerId;

        slot.querySelector(".drop-zone").innerHTML = `
            <div class="field-player">
                <strong>${playerName}</strong>
                <span>${playerRating}</span>
            </div>
        `;

        player.classList.add("on-field");

        updateInput(slot);

    });


    /*
     * FORMULIER
     */

    const form = document.getElementById("lineup-form");

    if (form) {

        form.addEventListener("submit", () => {

            slots.forEach(slot => {
                updateInput(slot);
            });

        });

    }

});