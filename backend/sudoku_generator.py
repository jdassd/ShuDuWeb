import random
from copy import deepcopy
from typing import List, Optional, Tuple

Grid = List[List[int]]

DIFFICULTY_RANGES = {
    "easy": (40, 45),
    "medium": (35, 40),
    "hard": (30, 35),
    "very_hard": (25, 30),
    "extreme": (20, 25),
}


def normalize_difficulty(difficulty: str) -> str:
    key = (difficulty or "medium").lower().replace(" ", "_")
    if key not in DIFFICULTY_RANGES:
        return "medium"
    return key


def generate_puzzle(difficulty: str) -> Tuple[Grid, Grid, str]:
    key = normalize_difficulty(difficulty)
    solution = generate_full_board()
    puzzle = remove_numbers(solution, key)
    return puzzle, solution, key


def generate_full_board() -> Grid:
    board = [[0 for _ in range(9)] for _ in range(9)]
    _fill_board(board)
    return board


def _fill_board(board: Grid) -> bool:
    empty = _find_empty(board)
    if not empty:
        return True
    row, col = empty
    nums = list(range(1, 10))
    random.shuffle(nums)
    for num in nums:
        if _is_valid(board, row, col, num):
            board[row][col] = num
            if _fill_board(board):
                return True
            board[row][col] = 0
    return False


def remove_numbers(solution: Grid, difficulty: str) -> Grid:
    puzzle = deepcopy(solution)
    low, high = DIFFICULTY_RANGES[difficulty]
    target_givens = random.randint(low, high)
    givens = 81

    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)

    for row, col in cells:
        if givens <= target_givens:
            break
        temp = puzzle[row][col]
        puzzle[row][col] = 0
        if count_solutions(puzzle, limit=2) != 1:
            puzzle[row][col] = temp
            continue
        givens -= 1

    return puzzle


def count_solutions(board: Grid, limit: int = 2) -> int:
    copied = deepcopy(board)
    return _count_solutions_inplace(copied, limit)


def _count_solutions_inplace(board: Grid, limit: int) -> int:
    empty = _find_empty(board)
    if not empty:
        return 1
    row, col = empty
    count = 0
    for num in range(1, 10):
        if _is_valid(board, row, col, num):
            board[row][col] = num
            count += _count_solutions_inplace(board, limit)
            if count >= limit:
                board[row][col] = 0
                return count
            board[row][col] = 0
    return count


def _find_empty(board: Grid) -> Optional[Tuple[int, int]]:
    for row in range(9):
        for col in range(9):
            if board[row][col] == 0:
                return row, col
    return None


def _is_valid(board: Grid, row: int, col: int, num: int) -> bool:
    if num in board[row]:
        return False
    for r in range(9):
        if board[r][col] == num:
            return False
    start_row = (row // 3) * 3
    start_col = (col // 3) * 3
    for r in range(start_row, start_row + 3):
        for c in range(start_col, start_col + 3):
            if board[r][c] == num:
                return False
    return True
