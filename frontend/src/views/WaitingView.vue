<script setup>
import { onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useGameStore } from "../store/game";

const route = useRoute();
const router = useRouter();
const store = useGameStore();

const readyUp = () => {
  store.sendReady();
};

const exitRoom = () => {
  store.leaveRoom();
  router.push("/");
};

onMounted(() => {
  if (!store.roomId) {
    router.push("/");
    return;
  }
  store.connectSocket();
  store.joinSocketRoom();
});

watch(
  () => store.status,
  (value) => {
    if (value === "playing") {
      router.push(`/room/${route.params.id}/game`);
    }
  }
);
</script>

<template>
  <section class="page">
    <div class="card">
      <div class="badge">Room Code</div>
      <div class="room-code">{{ store.roomId }}</div>
      <p class="hero-subtitle">Share this code to bring your opponent into the arena.</p>
    </div>

    <div class="status-grid">
      <div class="status-pill">
        <div class="section-title">You</div>
        <div>{{ store.nickname }}</div>
        <div class="hero-subtitle">Role: {{ store.role }}</div>
      </div>
      <div class="status-pill">
        <div class="section-title">Opponent</div>
        <div>{{ store.opponent.nickname || "Waiting..." }}</div>
        <div class="hero-subtitle">
          {{ store.opponent.online ? "Online" : "Offline" }}
        </div>
      </div>
    </div>

    <div class="card">
      <h2 class="section-title">Ready to start?</h2>
      <p class="hero-subtitle">When both players are ready, the puzzle begins immediately.</p>
      <div class="action-row">
        <button class="button" @click="readyUp">Ready</button>
        <button class="button ghost" @click="exitRoom">Leave room</button>
      </div>
    </div>
  </section>
</template>
