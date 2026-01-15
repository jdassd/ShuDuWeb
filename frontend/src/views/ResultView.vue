<script setup>
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGameStore } from "../store/game";

const store = useGameStore();
const router = useRouter();
const route = useRoute();

const formatTime = (totalSeconds) => {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
};

const outcome = computed(() => {
  if (!store.result) {
    return "Game Over";
  }
  const winner = store.result.winner;
  const isWin = (store.role === "host" && winner === "host") ||
    (store.role === "guest" && winner === "guest");
  return isWin ? "Victory" : "Defeat";
});

const selfTime = computed(() => {
  if (!store.result) {
    return 0;
  }
  return store.role === "host" ? store.result.timers.host : store.result.timers.guest;
});

const opponentTime = computed(() => {
  if (!store.result) {
    return 0;
  }
  return store.role === "host" ? store.result.timers.guest : store.result.timers.host;
});

const handleRematch = () => {
  store.requestRestart();
  router.push(`/room/${route.params.id}/waiting`);
};

const exitRoom = () => {
  store.leaveRoom();
  router.push("/");
};

onMounted(() => {
  if (!store.roomId) {
    router.push("/");
  }
});
</script>

<template>
  <section class="page">
    <div class="result-banner">
      <h2 class="hero-title">{{ outcome }}</h2>
      <p class="hero-subtitle">{{ store.result?.reason === 'errors' ? 'Opponent forced a mistake.' : 'Puzzle completed.' }}</p>
      <div class="status-grid">
        <div class="status-pill">
          <div class="section-title">Your time</div>
          <div>{{ formatTime(selfTime) }}</div>
        </div>
        <div class="status-pill">
          <div class="section-title">Opponent time</div>
          <div>{{ formatTime(opponentTime) }}</div>
        </div>
      </div>
    </div>

    <div class="split">
      <button class="button" @click="handleRematch">Play again</button>
      <button class="button ghost" @click="exitRoom">Return home</button>
    </div>
  </section>
</template>
