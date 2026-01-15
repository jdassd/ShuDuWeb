import asyncio
import uuid
from pathlib import Path
import socketio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from room_manager import RoomManager
from sudoku_generator import generate_puzzle
from websocket_handler import heartbeat_monitor, register_socket_handlers


class CreateRoomRequest(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=20)
    difficulty: str = "medium"


class JoinRoomRequest(BaseModel):
    room_id: str = Field(..., min_length=6, max_length=6)
    player_name: str = Field(..., min_length=1, max_length=20)


class PuzzleRequest(BaseModel):
    difficulty: str = "medium"


app = FastAPI(title="ShuDuWeb", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

room_manager = RoomManager()

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
register_socket_handlers(sio, room_manager)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@app.on_event("startup")
async def start_heartbeat_monitor() -> None:
    asyncio.create_task(heartbeat_monitor(sio, room_manager))


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.post("/api/room/create")
async def create_room(request: CreateRoomRequest) -> dict:
    room, player = room_manager.create_room(request.player_name, request.difficulty)
    return {
        "room_id": room.room_id,
        "player_id": player.player_id,
        "player_token": player.token,
        "role": "host",
        "difficulty": room.difficulty,
    }


@app.post("/api/room/join")
async def join_room(request: JoinRoomRequest) -> dict:
    try:
        room, player = room_manager.join_room(request.room_id, request.player_name)
    except ValueError as exc:
        if str(exc) == "room_not_found":
            raise HTTPException(status_code=404, detail="room_not_found")
        if str(exc) == "room_full":
            raise HTTPException(status_code=400, detail="room_full")
        raise
    return {
        "room_id": room.room_id,
        "player_id": player.player_id,
        "player_token": player.token,
        "role": "guest",
        "difficulty": room.difficulty,
    }


@app.get("/api/room/info")
async def room_info(room_id: str) -> dict:
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="room_not_found")
    return {
        "room_id": room.room_id,
        "status": room.status,
        "difficulty": room.difficulty,
        "host": {
            "nickname": room.host.nickname,
            "online": room.host.connection_status == "online",
        },
        "guest": {
            "nickname": room.guest.nickname if room.guest else "",
            "online": room.guest.connection_status == "online" if room.guest else False,
        }
        if room.guest
        else None,
        "puzzle_id": room.puzzle_id,
        "puzzle": room.puzzle if room.status in ("playing", "paused", "finished") else None,
    }


@app.post("/api/puzzle/generate")
async def puzzle_generate(request: PuzzleRequest) -> dict:
    puzzle, _, difficulty = generate_puzzle(request.difficulty)
    return {"puzzle": puzzle, "difficulty": difficulty, "puzzle_id": str(uuid.uuid4())}


asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)


if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        if full_path.startswith("api") or full_path.startswith("socket.io"):
            raise HTTPException(status_code=404, detail="not_found")
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index_path = STATIC_DIR / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="not_found")
