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
const notesMode = ref(false);

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
  if (notesMode.value) {
    if (value === 0) {
      store.clearNotes(selected.value.row, selected.value.col);
    } else {
      store.toggleNote(selected.value.row, selected.value.col, value);
    }
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
    <div class="game-stage">
      <div class="game-layout" :class="{ 'is-paused': store.status === 'paused' }">
      <div>
        <div class="status-pill status-card">
          <div class="status-row">
            <div>
              <div class="section-title">You</div>
              <div>{{ store.nickname }}</div>
            </div>
            <div>
              <div class="section-title">Opponent</div>
              <div>{{ store.opponent.nickname || "Unknown" }}</div>
            </div>
          </div>
          <div class="status-row status-row--meta">
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
          :notes="store.notes"
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
        <button :class="['button', notesMode ? 'secondary' : 'ghost']" @click="notesMode = !notesMode">
          {{ notesMode ? "Notes mode: On" : "Notes mode: Off" }}
        </button>
        <NumberPad @input="handleInput" />
        <button class="button ghost" @click="exitRoom">Exit room</button>
      </div>
    </div>
    <transition name="fade">
      <div v-if="store.status === 'paused'" class="game-mask">
        <div class="game-mask-card">
          <div class="section-title">Match paused</div>
          <div class="hero-subtitle">
            Opponent disconnected. The board is locked until they return.
          </div>
          <div class="mask-actions">
            <button v-if="store.reconnectTimeout" class="button" @click="store.requestRestart()">
              Restart
            </button>
            <button class="button ghost" @click="exitRoom">Leave</button>
          </div>
        </div>
      </div>
    </transition>
    </div>
  </section>
</template>
