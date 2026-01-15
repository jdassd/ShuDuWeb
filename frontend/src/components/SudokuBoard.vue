<script setup>
const props = defineProps({
  puzzle: { type: Array, default: () => [] },
  progress: { type: Array, default: () => [] },
  notes: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  errorCells: { type: Array, default: () => [] }
});

const emit = defineEmits(["select"]);

const getValue = (row, col) => {
  const puzzleRow = props.puzzle?.[row] || [];
  const progressRow = props.progress?.[row] || [];
  return puzzleRow[col] || progressRow[col] || "";
};

const isPrefilled = (row, col) => {
  return (props.puzzle?.[row] || [])[col] !== 0;
};

const isSelected = (row, col) => {
  return props.selected && props.selected.row === row && props.selected.col === col;
};

const isHighlighted = (row, col) => {
  return props.selected && (props.selected.row === row || props.selected.col === col);
};

const isError = (row, col) => {
  return props.errorCells.includes(`${row}-${col}`);
};

const getNotes = (row, col) => {
  return (props.notes?.[row] || [])[col] || [];
};

const selectCell = (row, col) => {
  if (isPrefilled(row, col)) {
    return;
  }
  emit("select", { row, col });
};
</script>

<template>
  <div class="sudoku-board">
    <div
      v-for="row in 9"
      :key="`row-${row}`"
      class="row"
      style="display: contents;"
    >
      <div
        v-for="col in 9"
        :key="`cell-${row}-${col}`"
        class="cell"
        :class="[
          isPrefilled(row - 1, col - 1) ? 'prefilled' : 'editable',
          isSelected(row - 1, col - 1) ? 'selected' : '',
          isHighlighted(row - 1, col - 1) ? 'highlight' : '',
          isError(row - 1, col - 1) ? 'error' : '',
          (col - 1) % 3 === 2 ? 'thick-right' : '',
          (row - 1) % 3 === 2 ? 'thick-bottom' : ''
        ]"
        @click="selectCell(row - 1, col - 1)"
      >
        <span v-if="getValue(row - 1, col - 1)">{{ getValue(row - 1, col - 1) }}</span>
        <div v-else class="cell-notes">
          <span v-for="note in 9" :key="`note-${row}-${col}-${note}`">
            {{ getNotes(row - 1, col - 1).includes(note) ? note : "" }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
