import { defineStore } from "pinia";
import { io } from "socket.io-client";

const fallbackBase =
  typeof window !== "undefined"
    ? import.meta.env.DEV
      ? "http://localhost:8000"
      : window.location.origin
    : "http://localhost:8000";
const API_BASE = import.meta.env.VITE_API_BASE || fallbackBase;
const SOCKET_BASE = import.meta.env.VITE_SOCKET_BASE || API_BASE;

const emptyGrid = () => Array.from({ length: 9 }, () => Array(9).fill(0));
const emptyNotes = () => Array.from({ length: 9 }, () => Array.from({ length: 9 }, () => []));
const SESSION_KEY = "shudu_session";
let heartbeatTimer = null;

export const useGameStore = defineStore("game", {
  state: () => ({
    roomId: "",
    playerToken: "",
    playerId: "",
    nickname: "",
    role: "",
    difficulty: "medium",
    status: "idle",
    puzzleId: "",
    puzzle: [],
    progress: emptyGrid(),
    notes: emptyNotes(),
    errors: 0,
    opponent: { nickname: "", online: false, progress: 0, errors: 0 },
    timers: { host: 0, guest: 0 },
    result: null,
    reconnectTimeout: false,
    lastCellResult: null,
    socket: null,
    socketConnected: false
  }),
  getters: {
    selfTimer(state) {
      return state.role === "host" ? state.timers.host : state.timers.guest;
    },
    opponentTimer(state) {
      return state.role === "host" ? state.timers.guest : state.timers.host;
    }
  },
  actions: {
    async createRoom(nickname, difficulty) {
      const response = await fetch(`${API_BASE}/api/room/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_name: nickname, difficulty })
      });
      if (!response.ok) {
        throw new Error("create_failed");
      }
      const payload = await response.json();
      this.roomId = payload.room_id;
      this.playerToken = payload.player_token;
      this.playerId = payload.player_id;
      this.role = payload.role;
      this.nickname = nickname;
      this.difficulty = payload.difficulty;
      this.status = "waiting";
      this.saveSession();
    },
    async joinRoom(roomId, nickname) {
      const response = await fetch(`${API_BASE}/api/room/join`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room_id: roomId, player_name: nickname })
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "join_failed");
      }
      const payload = await response.json();
      this.roomId = payload.room_id;
      this.playerToken = payload.player_token;
      this.playerId = payload.player_id;
      this.role = payload.role;
      this.nickname = nickname;
      this.difficulty = payload.difficulty;
      this.status = "waiting";
      this.saveSession();
    },
    connectSocket() {
      if (this.socket) {
        return;
      }
      this.socket = io(SOCKET_BASE, { transports: ["websocket"] });
      this.socket.on("connect", () => {
        this.socketConnected = true;
        if (this.roomId && this.playerToken) {
          this.socket.emit("join_room", { room_id: this.roomId, player_token: this.playerToken });
        }
      });
      this.socket.on("disconnect", () => {
        this.socketConnected = false;
      });
      this.socket.on("player_joined", (payload) => {
        if (payload?.nickname && payload.nickname !== this.nickname) {
          this.opponent.nickname = payload.nickname;
          this.opponent.online = true;
        }
      });
      this.socket.on("player_ready", () => {
        if (this.status === "waiting") {
          this.status = "ready";
        }
      });
      this.socket.on("game_start", (payload) => {
        this.status = "playing";
        this.puzzleId = payload.puzzle_id || "";
        this.puzzle = payload.puzzle || [];
        this.progress = emptyGrid();
        this.notes = emptyNotes();
        this.errors = 0;
        this.reconnectTimeout = false;
        this.opponent.progress = 0;
      });
      this.socket.on("state_sync", (payload) => {
        this.status = payload.status;
        this.difficulty = payload.difficulty;
        if (payload.puzzle_id && payload.puzzle_id !== this.puzzleId) {
          this.notes = emptyNotes();
        }
        this.puzzleId = payload.puzzle_id || this.puzzleId;
        this.puzzle = payload.puzzle || [];
        this.progress = payload.progress || emptyGrid();
        this.errors = payload.errors || 0;
        this.timers = payload.timers || { host: 0, guest: 0 };
        this.opponent = payload.opponent || this.opponent;
      });
      this.socket.on("cell_result", (payload) => {
        const { row, col, value, correct, errors } = payload;
        if (correct) {
          this.progress[row][col] = value;
          if (value > 0) {
            this.notes[row][col] = [];
          }
        }
        this.errors = errors;
        this.lastCellResult = payload;
      });
      this.socket.on("opponent_progress", (payload) => {
        this.opponent.progress = payload.filled || 0;
      });
      this.socket.on("timer_update", (payload) => {
        this.timers = payload.timers || this.timers;
      });
      this.socket.on("player_disconnected", (payload) => {
        if (payload?.player_id && payload.player_id === this.playerId) {
          if (this.status === "playing") {
            this.status = "paused";
          }
          return;
        }
        this.opponent.online = false;
        if (this.status === "playing") {
          this.status = "paused";
        }
      });
      this.socket.on("player_reconnected", (payload) => {
        if (payload?.player_id && payload.player_id === this.playerId) {
          if (this.status === "paused" && this.opponent.online) {
            this.status = "playing";
          }
          return;
        }
        this.opponent.online = true;
        if (this.status === "paused") {
          this.status = "playing";
        }
      });
      this.socket.on("game_over", (payload) => {
        this.status = "finished";
        this.result = payload;
      });
      this.socket.on("room_reset", () => {
        this.status = "waiting";
        this.puzzleId = "";
        this.puzzle = [];
        this.progress = emptyGrid();
        this.notes = emptyNotes();
        this.errors = 0;
        this.result = null;
        this.reconnectTimeout = false;
      });
      this.socket.on("reconnect_timeout", () => {
        this.reconnectTimeout = true;
      });
      this.startHeartbeat();
    },
    joinSocketRoom() {
      if (!this.socket || !this.roomId || !this.playerToken) {
        return;
      }
      this.socket.emit("join_room", { room_id: this.roomId, player_token: this.playerToken });
    },
    sendReady() {
      if (!this.socket) {
        return;
      }
      this.socket.emit("ready", { player_token: this.playerToken });
    },
    sendFillCell(row, col, value) {
      if (!this.socket) {
        return;
      }
      this.socket.emit("fill_cell", { player_token: this.playerToken, row, col, value });
    },
    toggleNote(row, col, value) {
      if (!this.notes[row] || !this.notes[row][col]) {
        return;
      }
      if (value < 1 || value > 9) {
        return;
      }
      if ((this.puzzle[row] || [])[col] !== 0) {
        return;
      }
      if ((this.progress[row] || [])[col] !== 0) {
        return;
      }
      const cellNotes = this.notes[row][col];
      const index = cellNotes.indexOf(value);
      if (index >= 0) {
        cellNotes.splice(index, 1);
      } else {
        cellNotes.push(value);
        cellNotes.sort((a, b) => a - b);
      }
    },
    clearNotes(row, col) {
      if (!this.notes[row] || !this.notes[row][col]) {
        return;
      }
      this.notes[row][col] = [];
    },
    sendHeartbeat() {
      if (!this.socket || !this.playerToken) {
        return;
      }
      this.socket.emit("heartbeat", { player_token: this.playerToken });
    },
    startHeartbeat() {
      if (heartbeatTimer) {
        return;
      }
      heartbeatTimer = setInterval(() => {
        this.sendHeartbeat();
      }, 5000);
    },
    stopHeartbeat() {
      if (!heartbeatTimer) {
        return;
      }
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    },
    requestRestart() {
      if (!this.socket) {
        return;
      }
      this.socket.emit("restart_game", { player_token: this.playerToken });
    },
    leaveRoom() {
      this.stopHeartbeat();
      if (this.socket) {
        this.socket.disconnect();
      }
      this.socket = null;
      this.clearSession();
      this.$reset();
    },
    saveSession() {
      if (!this.roomId || !this.playerToken) {
        return;
      }
      const payload = {
        roomId: this.roomId,
        playerToken: this.playerToken,
        playerId: this.playerId,
        nickname: this.nickname,
        role: this.role,
        difficulty: this.difficulty
      };
      localStorage.setItem(SESSION_KEY, JSON.stringify(payload));
    },
    loadSession() {
      const raw = localStorage.getItem(SESSION_KEY);
      if (!raw) {
        return;
      }
      try {
        const payload = JSON.parse(raw);
        this.roomId = payload.roomId || "";
        this.playerToken = payload.playerToken || "";
        this.playerId = payload.playerId || "";
        this.nickname = payload.nickname || "";
        this.role = payload.role || "";
        this.difficulty = payload.difficulty || this.difficulty;
        if (this.roomId && this.playerToken) {
          this.status = "waiting";
        }
      } catch (error) {
        this.clearSession();
      }
    },
    clearSession() {
      localStorage.removeItem(SESSION_KEY);
    }
  }
});
