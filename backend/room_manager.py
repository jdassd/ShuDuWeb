import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from sudoku_generator import generate_puzzle

Grid = List[List[int]]


def empty_progress() -> Grid:
    return [[0 for _ in range(9)] for _ in range(9)]



def generate_room_id(existing: Dict[str, "Room"]) -> str:
    while True:
        room_id = "".join(random.choice("0123456789") for _ in range(6))
        if room_id not in existing:
            return room_id


@dataclass
class Player:
    player_id: str
    nickname: str
    token: str
    sid: Optional[str] = None
    connection_status: str = "online"
    timer: int = 0
    last_start: Optional[float] = None
    errors: int = 0
    progress: Grid = field(default_factory=empty_progress)
    completed: bool = False
    ready: bool = False
    last_seen: float = field(default_factory=time.time)
    disconnected_at: Optional[float] = None

    def elapsed_seconds(self) -> int:
        elapsed = self.timer
        if self.last_start is not None:
            elapsed += int(time.time() - self.last_start)
        return int(elapsed)


@dataclass
class Room:
    room_id: str
    host: Player
    difficulty: str
    guest: Optional[Player] = None
    puzzle_id: Optional[str] = None
    puzzle: Optional[Grid] = None
    solution: Optional[Grid] = None
    status: str = "waiting"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    paused_at: Optional[float] = None
    timer_task: Optional[object] = None

    def players(self) -> List[Player]:
        return [p for p in [self.host, self.guest] if p is not None]


class RoomManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, Room] = {}
        self.token_index: Dict[str, str] = {}

    def create_room(self, nickname: str, difficulty: str) -> Tuple[Room, Player]:
        room_id = generate_room_id(self.rooms)
        host = Player(player_id=str(uuid.uuid4()), nickname=nickname, token=str(uuid.uuid4()))
        room = Room(room_id=room_id, host=host, difficulty=difficulty)
        self.rooms[room_id] = room
        self.token_index[host.token] = room_id
        return room, host

    def join_room(self, room_id: str, nickname: str) -> Tuple[Room, Player]:
        room = self.rooms.get(room_id)
        if not room:
            raise ValueError("room_not_found")
        if room.guest is not None:
            raise ValueError("room_full")
        guest = Player(player_id=str(uuid.uuid4()), nickname=nickname, token=str(uuid.uuid4()))
        room.guest = guest
        self.token_index[guest.token] = room_id
        return room, guest

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def get_room_by_token(self, token: str) -> Optional[Room]:
        room_id = self.token_index.get(token)
        if not room_id:
            return None
        return self.rooms.get(room_id)

    def get_player(self, room: Room, token: str) -> Optional[Player]:
        if room.host.token == token:
            return room.host
        if room.guest and room.guest.token == token:
            return room.guest
        return None

    def get_opponent(self, room: Room, token: str) -> Optional[Player]:
        if room.host.token == token:
            return room.guest
        if room.guest and room.guest.token == token:
            return room.host
        return None

    def start_game(self, room: Room) -> None:
        puzzle, solution, difficulty = generate_puzzle(room.difficulty)
        room.difficulty = difficulty
        room.puzzle_id = str(uuid.uuid4())
        room.puzzle = puzzle
        room.solution = solution
        room.status = "playing"
        room.started_at = time.time()
        room.paused_at = None
        for player in room.players():
            player.progress = empty_progress()
            player.errors = 0
            player.completed = False
            player.timer = 0
            player.last_start = time.time()
            player.ready = False

    def pause_room(self, room: Room) -> None:
        if room.status != "playing":
            return
        room.status = "paused"
        room.paused_at = time.time()
        for player in room.players():
            if player.last_start is not None:
                player.timer = player.elapsed_seconds()
                player.last_start = None

    def resume_room(self, room: Room) -> None:
        if room.status != "paused":
            return
        room.status = "playing"
        room.paused_at = None
        now = time.time()
        for player in room.players():
            player.last_start = now

    def is_ready(self, room: Room) -> bool:
        if not room.guest:
            return False
        return room.host.ready and room.guest.ready

    def is_completed(self, room: Room, player: Player) -> bool:
        if not room.puzzle:
            return False
        empty_cells = sum(1 for row in room.puzzle for cell in row if cell == 0)
        filled = sum(1 for row in player.progress for cell in row if cell != 0)
        return filled >= empty_cells
