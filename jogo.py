from __future__ import annotations

from flask import Blueprint, render_template, request
from flask_socketio import emit, join_room
import random
import string

jogo_bp = Blueprint("jogo", __name__, template_folder="templates", static_folder="static")

rooms: dict[str, dict[str, object]] = {}


@jogo_bp.route("/jogo")
def jogo() -> str:
    room_id = request.args.get("room")
    if not room_id:
        room_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return render_template("jogo.html", room_id=room_id)


def init_socketio(socketio) -> None:
    @socketio.on("join_room")
    def handle_join(data):  # type: ignore[no-redef]
        room = data["room"]
        join_room(room)
        if room not in rooms:
            rooms[room] = {
                "rows": [[1, 1, 1], [1, 1, 1], [1, 1, 1], [1, 1], [1, 1]],
                "turn": 0,
            }
        emit("state_update", rooms[room], to=room)

    @socketio.on("move")
    def handle_move(data):  # type: ignore[no-redef]
        room = data["room"]
        row = data["row"]
        indexes = data["indexes"]
        state = rooms.get(room)
        if not state:
            return

        # risca os pausinhos
        for i in indexes:
            if state["rows"][row][i] == 1:
                state["rows"][row][i] = 0

        # alterna turno
        state["turn"] = 1 - state["turn"]

        # checa fim de jogo
        if all(all(p == 0 for p in r) for r in state["rows"]):
            emit("state_update", state, to=room)
            emit("game_over", to=room)
            rooms.pop(room, None)
        else:
            emit("state_update", state, to=room)
