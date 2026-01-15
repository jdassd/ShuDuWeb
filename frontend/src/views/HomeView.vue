<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../store/game";

const router = useRouter();
const store = useGameStore();

const createName = ref("");
const joinName = ref("");
const joinRoomId = ref("");
const difficulty = ref("medium");
const errorMessage = ref("");
const loading = ref(false);

const difficulties = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
  { value: "very_hard", label: "Very Hard" },
  { value: "extreme", label: "Extreme" }
];

const handleCreate = async () => {
  if (!createName.value.trim()) {
    errorMessage.value = "Enter a nickname to create a room.";
    return;
  }
  errorMessage.value = "";
  loading.value = true;
  try {
    await store.createRoom(createName.value.trim(), difficulty.value);
    store.connectSocket();
    store.joinSocketRoom();
    router.push(`/room/${store.roomId}/waiting`);
  } catch (error) {
    errorMessage.value = "Could not create room.";
  } finally {
    loading.value = false;
  }
};

const handleJoin = async () => {
  if (!joinName.value.trim() || !joinRoomId.value.trim()) {
    errorMessage.value = "Enter a nickname and room code.";
    return;
  }
  errorMessage.value = "";
  loading.value = true;
  try {
    await store.joinRoom(joinRoomId.value.trim(), joinName.value.trim());
    store.connectSocket();
    store.joinSocketRoom();
    router.push(`/room/${store.roomId}/waiting`);
  } catch (error) {
    errorMessage.value = "Could not join room.";
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <section class="page">
    <div class="card">
      <h2 class="section-title">Start a duel</h2>
      <p class="hero-subtitle">Choose a difficulty and invite a friend to race through the same puzzle.</p>
      <div class="inline-form">
        <input v-model="createName" class="input" placeholder="Nickname" />
        <select v-model="difficulty" class="select">
          <option v-for="diff in difficulties" :key="diff.value" :value="diff.value">
            {{ diff.label }}
          </option>
        </select>
        <button class="button" :disabled="loading" @click="handleCreate">Create room</button>
      </div>
    </div>

    <div class="card">
      <h2 class="section-title">Join an existing room</h2>
      <p class="hero-subtitle">Use the 6-digit room code your friend shares with you.</p>
      <div class="inline-form">
        <input v-model="joinName" class="input" placeholder="Nickname" />
        <input v-model="joinRoomId" class="input" placeholder="Room code" maxlength="6" />
        <button class="button secondary" :disabled="loading" @click="handleJoin">Join room</button>
      </div>
    </div>

    <div v-if="errorMessage" class="alert">{{ errorMessage }}</div>
  </section>
</template>
