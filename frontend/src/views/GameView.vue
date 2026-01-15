<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGameStore } from "../store/game";
import SudokuBoard from "../components/SudokuBoard.vue";
import NumberPad from "../components/NumberPad.vue";

const store = useGameStore();
const router = useRouter();
const route = useRoute();

const selected = ref(null);
const errorCells = ref([]);

const formatTime = (totalSeconds) => {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
};

const totalEmpty = computed(() => {
  if (!store.puzzle?.length) {
    return 0;
  }
  return store.puzzle.flat().filter((cell) => cell === 0).length;
});

const opponentProgressPercent = computed(() => {
  if (!totalEmpty.value) {
    return 0;
  }
  return Math.min(100, Math.round((store.opponent.progress / totalEmpty.value) * 100));
});

const handleSelect = (cell) => {
  selected.value = cell;
};

const handleInput = (value) => {
  if (!selected.value) {
    return;
  }
  store.sendFillCell(selected.value.row, selected.value.col, value);
};

const exitRoom = () => {
  store.leaveRoom();
  router.push("/");
};

watch(
  () => store.lastCellResult,
  (payload) => {
    if (!payload) {
      return;
    }
    const key = `${payload.row}-${payload.col}`;
    if (!payload.correct) {
      if (!errorCells.value.includes(key)) {
        errorCells.value = [...errorCells.value, key];
      }
      setTimeout(() => {
        errorCells.value = errorCells.value.filter((entry) => entry !== key);
      }, 900);
    } else {
      errorCells.value = errorCells.value.filter((entry) => entry !== key);
    }
  }
);

watch(
  () => store.status,
  (value) => {
    if (value === "finished") {
      router.push(`/room/${route.params.id}/result`);
    }
    if (value === "waiting") {
      router.push(`/room/${route.params.id}/waiting`);
    }
  }
);

onMounted(() => {
  if (!store.roomId) {
    router.push("/");
    return;
  }
  store.connectSocket();
  store.joinSocketRoom();
});
</script>

<template>
  <section class="page">
    <div class="game-layout">
      <div>
        <div class="status-pill" style="margin-bottom: 18px; display: grid; gap: 8px;">
          <div style="display: flex; justify-content: space-between; gap: 12px;">
            <div>
              <div class="section-title">You</div>
              <div>{{ store.nickname }}</div>
            </div>
            <div>
              <div class="section-title">Opponent</div>
              <div>{{ store.opponent.nickname || "Unknown" }}</div>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; gap: 12px;">
            <div>Time: {{ formatTime(store.selfTimer) }}</div>
            <div>Errors: {{ store.errors }}/3</div>
            <div>Opponent: {{ formatTime(store.opponentTimer) }}</div>
          </div>
          <div class="opponent-progress">
            <span :style="{ width: opponentProgressPercent + '%' }"></span>
          </div>
        </div>

        <SudokuBoard
          :puzzle="store.puzzle"
          :progress="store.progress"
          :selected="selected"
          :error-cells="errorCells"
          @select="handleSelect"
        />
      </div>

      <div class="card" style="display: grid; gap: 18px;">
        <div>
          <div class="section-title">Number pad</div>
          <p class="hero-subtitle">Pick a cell, then choose a number.</p>
        </div>
        <NumberPad @input="handleInput" />
        <button class="button ghost" @click="exitRoom">Exit room</button>
        <div v-if="store.status === 'paused'" class="alert">
          Opponent disconnected. Timer paused.
        </div>
        <div v-if="store.reconnectTimeout" class="alert">
          Opponent is away too long. You can restart or leave.
          <div style="display: flex; gap: 12px; margin-top: 12px;">
            <button class="button" @click="store.requestRestart()">Restart</button>
            <button class="button ghost" @click="exitRoom">Leave</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
