const players = document.querySelectorAll(".lineup-player");
const pitch = document.getElementById("pitch");

let draggedPlayer = null;

const benchPlayers = document.querySelectorAll(".bench-player");
const formationPositions = document.querySelectorAll(".formation-position");

benchPlayers.forEach(player => {

    player.addEventListener("dragstart", () => {
        draggedPlayer = player;
        player.classList.add("dragging");
    });

    player.addEventListener("dragend", () => {
        player.classList.remove("dragging");
        draggedPlayer = null;
    });

});


formationPositions.forEach(position => {

    position.addEventListener("dragover", (event) => {
        event.preventDefault();

        position.classList.add("drop-hover");
    });

    position.addEventListener("dragleave", () => {
        position.classList.remove("drop-hover");
    });

    position.addEventListener("drop", (event) => {

        event.preventDefault();

        position.classList.remove("drop-hover");

        if (!draggedPlayer) {
            return;
        }

        const playerName = draggedPlayer.dataset.player;
        const playerRating = draggedPlayer.dataset.rating;

        position.innerHTML = `
            <strong>${playerName}</strong>
            <small>${playerRating}</small>
        `;

        position.classList.add("filled");

        draggedPlayer.style.opacity = "0.4";

        draggedPlayer = null;
    });

});



pitch.addEventListener("dragover", (event) => {
    event.preventDefault();
});

pitch.addEventListener("drop", (event) => {

    event.preventDefault();

    if (!draggedPlayer) {
        return;
    }

    const rect = pitch.getBoundingClientRect();

    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    draggedPlayer.style.position = "absolute";
    draggedPlayer.style.left = `${x}px`;
    draggedPlayer.style.top = `${y}px`;
    draggedPlayer.style.transform = "translate(-50%, -50%)";
});