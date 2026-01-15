import asyncio
import time
from typing import Any, Dict

import socketio

from room_manager import Room, RoomManager


HEARTBEAT_TIMEOUT = 15
RECONNECT_TIMEOUT = 300


def progress_count(progress) -> int:
    return sum(1 for row in progress for cell in row if cell != 0)


def build_timer_payload(room: Room) -> Dict[str, int]:
    host_time = room.host.elapsed_seconds()
    guest_time = room.guest.elapsed_seconds() if room.guest else 0
    return {"host": host_time, "guest": guest_time}


def build_state_payload(room: Room, player_token: str) -> Dict[str, Any]:
    player = room.host if room.host.token == player_token else room.guest
    opponent = room.guest if player == room.host else room.host
    return {
        "room_id": room.room_id,
        "status": room.status,
        "difficulty": room.difficulty,
        "puzzle_id": room.puzzle_id,
        "puzzle": room.puzzle,
        "progress": player.progress if player else [],
        "errors": player.errors if player else 0,
        "timers": build_timer_payload(room),
        "opponent": {
            "nickname": opponent.nickname if opponent else "",
            "online": opponent.connection_status == "online" if opponent else False,
            "progress": progress_count(opponent.progress) if opponent else 0,
            "errors": opponent.errors if opponent else 0,
        },
    }


def register_socket_handlers(sio: socketio.AsyncServer, manager: RoomManager) -> None:
    sid_to_token: Dict[str, str] = {}

    async def _start_timer_task(room: Room) -> None:
        if room.timer_task and not getattr(room.timer_task, "done", lambda: True)():
            return

        async def _loop() -> None:
            while True:
                current = manager.get_room(room.room_id)
                if not current or current.status != "playing":
                    return
                await sio.emit("timer_update", {"timers": build_timer_payload(current)}, room=current.room_id)
                await asyncio.sleep(1)

        room.timer_task = asyncio.create_task(_loop())

    async def _handle_game_over(room: Room, winner_token: str, reason: str) -> None:
        room.status = "finished"
        for player in room.players():
            if player.last_start is not None:
                player.timer = player.elapsed_seconds()
                player.last_start = None
        payload = {
            "winner": "host" if room.host.token == winner_token else "guest",
            "reason": reason,
            "timers": build_timer_payload(room),
        }
        await sio.emit("game_over", payload, room=room.room_id)

    @sio.event
    async def connect(sid, environ):
        await sio.emit("connected", {"ok": True}, to=sid)

    @sio.event
    async def join_room(sid, data):
        room_id = data.get("room_id")
        token = data.get("player_token")
        if not room_id or not token:
            return
        room = manager.get_room(room_id)
        if not room:
            await sio.emit("error", {"message": "room_not_found"}, to=sid)
            return
        player = manager.get_player(room, token)
        if not player:
            await sio.emit("error", {"message": "invalid_token"}, to=sid)
            return
        player.sid = sid
        player.connection_status = "online"
        player.disconnected_at = None
        player.last_seen = time.time()
        sid_to_token[sid] = token
        await sio.enter_room(sid, room_id)
        await sio.emit(
            "player_joined",
            {"player_id": player.player_id, "nickname": player.nickname},
            room=room_id,
        )
        if room.status in ("playing", "paused", "finished"):
            await sio.emit("state_sync", build_state_payload(room, token), to=sid)

    @sio.event
    async def ready(sid, data):
        token = data.get("player_token")
        if not token:
            return
        room = manager.get_room_by_token(token)
        if not room:
            return
        player = manager.get_player(room, token)
        if not player:
            return
        player.ready = True
        await sio.emit("player_ready", {"player_id": player.player_id}, room=room.room_id)
        if manager.is_ready(room):
            manager.start_game(room)
            await sio.emit(
                "game_start",
                {
                    "room_id": room.room_id,
                    "difficulty": room.difficulty,
                    "puzzle_id": room.puzzle_id,
                    "puzzle": room.puzzle,
                },
                room=room.room_id,
            )
            await _start_timer_task(room)

    @sio.event
    async def fill_cell(sid, data):
        token = data.get("player_token")
        if not token:
            return
        room = manager.get_room_by_token(token)
        if not room or room.status != "playing":
            return
        player = manager.get_player(room, token)
        opponent = manager.get_opponent(room, token)
        if not player or not room.puzzle or not room.solution:
            return
        try:
            row = int(data.get("row"))
            col = int(data.get("col"))
            value = int(data.get("value"))
        except (TypeError, ValueError):
            return
        if row < 0 or row > 8 or col < 0 or col > 8:
            return
        if value < 0 or value > 9:
            return
        if room.puzzle[row][col] != 0:
            return

        if value == 0:
            if player.progress[row][col] != 0:
                player.progress[row][col] = 0
                if opponent and opponent.sid:
                    await sio.emit(
                        "opponent_progress",
                        {"filled": progress_count(player.progress)},
                        to=opponent.sid,
                    )
            await sio.emit(
                "cell_result",
                {
                    "row": row,
                    "col": col,
                    "value": 0,
                    "correct": True,
                    "errors": player.errors,
                    "filled": progress_count(player.progress),
                },
                to=player.sid,
            )
            return

        if room.solution[row][col] == value:
            player.progress[row][col] = value
            await sio.emit(
                "cell_result",
                {
                    "row": row,
                    "col": col,
                    "value": value,
                    "correct": True,
                    "errors": player.errors,
                    "filled": progress_count(player.progress),
                },
                to=player.sid,
            )
            if opponent and opponent.sid:
                await sio.emit(
                    "opponent_progress",
                    {"filled": progress_count(player.progress)},
                    to=opponent.sid,
                )
            if manager.is_completed(room, player):
                await _handle_game_over(room, token, "completed")
            return

        player.errors += 1
        await sio.emit(
            "cell_result",
            {
                "row": row,
                "col": col,
                "value": value,
                "correct": False,
                "errors": player.errors,
                "filled": progress_count(player.progress),
            },
            to=player.sid,
        )
        if player.errors >= 3 and opponent:
            await _handle_game_over(room, opponent.token, "errors")

    @sio.event
    async def heartbeat(sid, data):
        token = data.get("player_token") if isinstance(data, dict) else None
        if not token:
            return
        room = manager.get_room_by_token(token)
        if not room:
            return
        player = manager.get_player(room, token)
        if not player:
            return
        player.last_seen = time.time()

    @sio.event
    async def reconnect(sid, data):
        token = data.get("player_token")
        if not token:
            return
        room = manager.get_room_by_token(token)
        if not room:
            await sio.emit("error", {"message": "room_not_found"}, to=sid)
            return
        player = manager.get_player(room, token)
        if not player:
            await sio.emit("error", {"message": "invalid_token"}, to=sid)
            return
        player.sid = sid
        player.connection_status = "online"
        player.disconnected_at = None
        player.last_seen = time.time()
        sid_to_token[sid] = token
        await sio.enter_room(sid, room.room_id)
        await sio.emit("player_reconnected", {"player_id": player.player_id}, room=room.room_id)
        await sio.emit("state_sync", build_state_payload(room, token), to=sid)
        if room.status == "paused":
            if room.guest and room.host.connection_status == "online" and room.guest.connection_status == "online":
                manager.resume_room(room)
                await _start_timer_task(room)

    @sio.event
    async def restart_game(sid, data):
        token = data.get("player_token")
        if not token:
            return
        room = manager.get_room_by_token(token)
        if not room:
            return
        room.status = "waiting"
        room.puzzle = None
        room.solution = None
        room.puzzle_id = None
        room.started_at = None
        room.paused_at = None
        for player in room.players():
            player.ready = False
            player.progress = [[0 for _ in range(9)] for _ in range(9)]
            player.errors = 0
            player.timer = 0
            player.last_start = None
            player.completed = False
        await sio.emit("room_reset", {"room_id": room.room_id}, room=room.room_id)

    @sio.event
    async def disconnect(sid):
        token = sid_to_token.pop(sid, None)
        if not token:
            return
        room = manager.get_room_by_token(token)
        if not room:
            return
        player = manager.get_player(room, token)
        if not player:
            return
        player.connection_status = "offline"
        player.disconnected_at = time.time()
        if room.status == "playing":
            manager.pause_room(room)
        await sio.emit(
            "player_disconnected",
            {"player_id": player.player_id},
            room=room.room_id,
        )

        async def _timeout_check() -> None:
            await asyncio.sleep(RECONNECT_TIMEOUT)
            refreshed = manager.get_room(room.room_id)
            if not refreshed:
                return
            refreshed_player = manager.get_player(refreshed, token)
            if not refreshed_player or refreshed_player.connection_status == "online":
                return
            opponent = manager.get_opponent(refreshed, token)
            if opponent and opponent.sid:
                await sio.emit(
                    "reconnect_timeout",
                    {"player_id": refreshed_player.player_id},
                    to=opponent.sid,
                )

        asyncio.create_task(_timeout_check())


async def heartbeat_monitor(sio: socketio.AsyncServer, manager: RoomManager) -> None:
    while True:
        await asyncio.sleep(5)
        now = time.time()
        for room in list(manager.rooms.values()):
            for player in room.players():
                if player.connection_status == "online" and now - player.last_seen > HEARTBEAT_TIMEOUT:
                    player.connection_status = "offline"
                    player.disconnected_at = now
                    if room.status == "playing":
                        manager.pause_room(room)
                    await sio.emit(
                        "player_disconnected",
                        {"player_id": player.player_id},
                        room=room.room_id,
                    )
