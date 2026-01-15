<script setup>
const emit = defineEmits(["input"]);

const handleClick = (value) => {
  emit("input", value);
};
</script>

<template>
  <div class="number-pad">
    <button v-for="num in 9" :key="num" @click="handleClick(num)">{{ num }}</button>
    <button class="button ghost" style="grid-column: span 3;" @click="handleClick(0)">Clear</button>
  </div>
</template>
