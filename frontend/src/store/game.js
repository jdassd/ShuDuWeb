import { defineStore } from "pinia";
import { io } from "socket.io-client";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const SOCKET_BASE = import.meta.env.VITE_SOCKET_BASE || "http://localhost:8000";

const emptyGrid = () => Array.from({ length: 9 }, () => Array(9).fill(0));
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
    puzzle: [],
    progress: emptyGrid(),
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
        this.puzzle = payload.puzzle || [];
        this.progress = emptyGrid();
        this.errors = 0;
        this.reconnectTimeout = false;
        this.opponent.progress = 0;
      });
      this.socket.on("state_sync", (payload) => {
        this.status = payload.status;
        this.difficulty = payload.difficulty;
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
      this.socket.on("player_disconnected", () => {
        this.opponent.online = false;
        if (this.status === "playing") {
          this.status = "paused";
        }
      });
      this.socket.on("player_reconnected", () => {
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
        this.puzzle = [];
        this.progress = emptyGrid();
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
      this.$reset();
    }
  }
});
