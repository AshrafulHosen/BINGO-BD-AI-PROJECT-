from __future__ import annotations
from typing import Tuple
from core.board import LINE_MASKS
from core.state import GameState, GameStatus, DRAW

# Terminal utility constants that dominate all heuristic evaluations
WIN_SCORE = 100000.0
LOSS_SCORE = -100000.0
DRAW_SCORE = 0.0


def evaluate_state(state: GameState, player: int) -> float:
    """
    Evaluates state from the perspective of `player` (0 or 1).
    Terminal states return massive dominant scores.
    Non-terminal states evaluate board line completion and potential.
    """
    opponent = 1 - player

    # Terminal check
    if state.status == GameStatus.FINISHED:
        if state.winner == player:
            return WIN_SCORE
        elif state.winner == opponent:
            return LOSS_SCORE
        elif state.winner == DRAW:
            return DRAW_SCORE

    marked_p = state.marked_mask_a if player == 0 else state.marked_mask_b
    marked_o = state.marked_mask_b if player == 0 else state.marked_mask_a

    completed_p = 0
    potential_p = 0.0
    for mask in LINE_MASKS:
        cnt = (marked_p & mask).bit_count()
        if cnt == 5:
            completed_p += 1
        else:
            potential_p += (cnt / 5.0) ** 2

    completed_o = 0
    potential_o = 0.0
    for mask in LINE_MASKS:
        cnt = (marked_o & mask).bit_count()
        if cnt == 5:
            completed_o += 1
        else:
            potential_o += (cnt / 5.0) ** 2

    e = 100.0 * (completed_p - completed_o) + 10.0 * (potential_p - potential_o)
    return e


def quick_move_score(state: GameState, number: int, player: int) -> float:
    """
    Lightweight heuristic score for a specific move candidate,
    used for action ordering in Minimax and MCTS prior guidance.
    """
    # Check impact on player's board and opponent's board
    lut_p = state._lut_a if player == 0 else state._lut_b
    lut_o = state._lut_b if player == 0 else state._lut_a

    idx_p = lut_p[number]
    idx_o = lut_o[number]

    bit_p = 1 << idx_p
    bit_o = 1 << idx_o

    marked_p = state.marked_mask_a if player == 0 else state.marked_mask_b
    marked_o = state.marked_mask_b if player == 0 else state.marked_mask_a

    score = 0.0
    for mask in LINE_MASKS:
        if mask & bit_p:
            current_cnt = (marked_p & mask).bit_count()
            if current_cnt == 4:
                score += 100.0  # Completes a line for player!
            else:
                score += ((current_cnt + 1) / 5.0) ** 2 - (current_cnt / 5.0) ** 2

        if mask & bit_o:
            current_cnt_o = (marked_o & mask).bit_count()
            if current_cnt_o == 4:
                score -= 80.0  # Danger: completes a line for opponent!
            else:
                score -= (((current_cnt_o + 1) / 5.0) ** 2 - (current_cnt_o / 5.0) ** 2) * 0.5

    return score
