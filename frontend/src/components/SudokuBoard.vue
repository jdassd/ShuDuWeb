<script setup>
const props = defineProps({
  puzzle: { type: Array, default: () => [] },
  progress: { type: Array, default: () => [] },
  notes: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  errorCells: { type: Array, default: () => [] }
});

const emit = defineEmits(["select"]);

const cells = Array.from({ length: 81 }, (_, index) => ({
  row: Math.floor(index / 9),
  col: index % 9
}));

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
    <div class="sudoku-grid">
      <div
        v-for="cell in cells"
        :key="`cell-${cell.row}-${cell.col}`"
        class="cell"
        :class="[
          isPrefilled(cell.row, cell.col) ? 'prefilled' : 'editable',
          isSelected(cell.row, cell.col) ? 'selected' : '',
          isHighlighted(cell.row, cell.col) ? 'highlight' : '',
          isError(cell.row, cell.col) ? 'error' : '',
          cell.col % 3 === 2 ? 'thick-right' : '',
          cell.row % 3 === 2 ? 'thick-bottom' : ''
        ]"
        @click="selectCell(cell.row, cell.col)"
      >
        <span v-if="getValue(cell.row, cell.col)">{{ getValue(cell.row, cell.col) }}</span>
        <div v-else class="cell-notes">
          <span v-for="note in 9" :key="`note-${cell.row}-${cell.col}-${note}`">
            {{ getNotes(cell.row, cell.col).includes(note) ? note : "" }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
