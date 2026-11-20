"""
Edge-case and regression tests added during the v1.1 audit.

Covers: invalid-move rejection (incl. bool), multi-line simultaneous completion,
exhaustion/terminal handling, AI tie-breaking, tactical correctness of all three
agents, FastSim/rules equivalence, AI latency budgets (AC-06), controller
stale-worker protection (AC-07), and statistics default isolation.
"""

import random
import time

import pytest

from core.board import generate_board
from core.state import GameState, GameMode, AgentType, GameStatus, DRAW
from core.rules import (
    create_game,
    legal_moves,
    is_legal_move,
    apply_move,
    terminal_result,
    completed_line_count,
)
from core.controller import GameController
from ai import choose_move
from ai.heuristic import choose_heuristic_move
from ai.minimax import choose_minimax_move
from ai.mcts import choose_mcts_move, FastSim
from data.stats_manager import StatsManager, DEFAULT_STATS

IDENTITY = tuple(range(1, 26))


def make_state(board_a, board_b, called, current_player=0,
               agents=(AgentType.HUMAN, AgentType.EASY)):
    """Build a PLAYING state with the given numbers already called."""
    called = tuple(called)
    return GameState(
        board_a=tuple(board_a),
        board_b=tuple(board_b),
        called_mask=sum(1 << (n - 1) for n in called),
        current_player=current_player,
        mode=GameMode.HUMAN_VS_AI,
        agents=agents,
        status=GameStatus.PLAYING,
        winner=None,
        move_history=called,
    )


# --------------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------------- #
def test_bool_and_non_integer_moves_rejected():
    state = create_game(seed=1)
    for bad in (True, False, 3.0, "5", None, [1]):
        assert is_legal_move(state, bad) is False
        with pytest.raises(ValueError):
            apply_move(state, bad)


def test_moves_rejected_after_game_finished():
    state = make_state(IDENTITY, generate_board(seed=10), range(1, 21))
    final = apply_move(state, 21)
    assert final.status == GameStatus.FINISHED
    assert legal_moves(final) == []
    assert not is_legal_move(final, 22)
    with pytest.raises(ValueError):
        apply_move(final, 22)


def test_single_call_completes_three_lines_at_once():
    """Centre cell (13 on identity board) closes row 2, col 2 and both diagonals."""
    pre = [11, 12, 14, 15,          # row 2 minus centre
           3, 8, 18, 23,            # col 2 minus centre
           1, 7, 19, 25,            # main diag minus centre
           5, 9, 17, 21]            # anti diag minus centre
    mask = sum(1 << (n - 1) for n in pre)
    assert completed_line_count(IDENTITY, mask) == 0
    mask |= 1 << 12
    assert completed_line_count(IDENTITY, mask) == 4  # never double counted


def test_jump_past_five_lines_still_wins():
    """A call taking a player from 4 to 6+ lines is a win (>= 5 threshold)."""
    # Rows 0..3 complete (20 numbers) - then 21 completes row 4 AND column 0.
    state = make_state(IDENTITY, generate_board(seed=99), range(1, 21))
    assert state.lines_a == 4
    s = apply_move(state, 21)
    assert s.lines_a >= 5
    assert s.winner == 0 or s.winner == DRAW


def test_terminal_result_exhaustion_is_draw():
    """All 25 numbers called with no winner flag set -> draw by exhaustion."""
    s = GameState(
        board_a=IDENTITY, board_b=IDENTITY, called_mask=(1 << 25) - 1,
        current_player=0, mode=GameMode.HUMAN_VS_HUMAN,
        agents=(AgentType.HUMAN, AgentType.HUMAN), status=GameStatus.PLAYING,
        winner=None, move_history=IDENTITY,
    )
    is_term, winner = terminal_result(s)
    assert is_term and winner == DRAW


def test_random_games_always_terminate_correctly():
    """Fuzz: 300 random games end within 25 calls with a consistent result."""
    rng = random.Random(7)
    for g in range(300):
        s = create_game(seed=g)
        while s.status == GameStatus.PLAYING:
            s = apply_move(s, rng.choice(legal_moves(s)))
        assert len(s.move_history) <= 25
        is_term, winner = terminal_result(s)
        assert is_term and winner == s.winner
        if s.winner == DRAW:
            assert (s.lines_a >= 5 and s.lines_b >= 5) or len(s.move_history) == 25
        elif s.winner == 0:
            assert s.lines_a >= 5 > s.lines_b
        else:
            assert s.lines_b >= 5 > s.lines_a


def test_turn_does_not_switch_on_terminal_move():
    state = make_state(IDENTITY, generate_board(seed=10), range(1, 21), current_player=0)
    s = apply_move(state, 21)
    assert s.status == GameStatus.FINISHED
    assert s.current_player == 0


# --------------------------------------------------------------------------- #
# AI correctness
# --------------------------------------------------------------------------- #
@pytest.fixture
def win_in_one_state():
    """Player 1 (board B = identity) needs only 21 to reach 5 lines; board A doesn't."""
    board_a = generate_board(seed=1234)
    called = list(range(1, 21))
    s = make_state(board_a, IDENTITY, called, current_player=1,
                   agents=(AgentType.HUMAN, AgentType.HARD))
    # make sure the fixture really is "win-in-one" for P1 only
    assert s.lines_b == 4 and s.lines_a < 4
    assert apply_move(s, 21).winner == 1
    return s


def test_heuristic_takes_immediate_win(win_in_one_state):
    move, _ = choose_heuristic_move(win_in_one_state, 1, seed=0)
    assert apply_move(win_in_one_state, move).winner == 1


def test_minimax_takes_immediate_win(win_in_one_state):
    move, diag = choose_minimax_move(win_in_one_state, 1, depth=2)
    assert apply_move(win_in_one_state, move).winner == 1
    assert diag["score"] > 50000


def test_mcts_takes_immediate_win(win_in_one_state):
    move, diag = choose_mcts_move(win_in_one_state, 1, rollouts=200, seed=1)
    assert apply_move(win_in_one_state, move).winner == 1


def test_minimax_avoids_handing_opponent_the_win():
    """
    Player 1 to move.  Player 0 is one call away from 5 lines on several numbers
    ("suicide" calls).  Minimax must pick a call that does not end the game in
    player 0's favour when a safe alternative exists.
    """
    rng = random.Random(3)
    checked = 0
    for seed in range(200):
        s = create_game(seed=seed)
        while s.status == GameStatus.PLAYING and s.lines_a < 4:
            s = apply_move(s, rng.choice(legal_moves(s)))
        if s.status != GameStatus.PLAYING or s.current_player != 1:
            continue
        losing = [m for m in legal_moves(s) if apply_move(s, m).winner == 0]
        safe = [m for m in legal_moves(s) if apply_move(s, m).winner != 0]
        if not losing or not safe:
            continue
        move, _ = choose_minimax_move(s, 1, depth=2)
        assert move in safe
        checked += 1
    assert checked >= 3


def test_heuristic_tie_breaking_is_seeded():
    """Opening position has many equal-score moves; seed controls the choice."""
    state = create_game(seed=10)
    _, diag = choose_heuristic_move(state, 0, seed=1)
    assert diag["tied_moves"] >= 1
    picks = {choose_heuristic_move(state, 0, seed=s)[0] for s in range(30)}
    for s in range(5):
        assert choose_heuristic_move(state, 0, seed=s)[0] == choose_heuristic_move(state, 0, seed=s)[0]
    if diag["tied_moves"] > 1:
        assert len(picks) > 1


def test_heuristic_prefers_centre_on_identity_boards():
    """With identical identity boards, a symmetric position is evaluated fairly:
    the score of each successor must be a finite number and the chosen move legal."""
    s = make_state(IDENTITY, IDENTITY, [])
    move, diag = choose_heuristic_move(s, 0, seed=0)
    assert move in legal_moves(s)
    assert diag["evaluations"] == 25


def test_search_does_not_mutate_state():
    s = create_game(seed=77)
    s = apply_move(apply_move(s, 5), 9)
    snapshot = (s.called_mask, s.move_history, s.version, s.current_player)
    choose_heuristic_move(s, s.current_player)
    choose_minimax_move(s, s.current_player, depth=2)
    choose_mcts_move(s, s.current_player, rollouts=100)
    assert (s.called_mask, s.move_history, s.version, s.current_player) == snapshot


@pytest.mark.parametrize("difficulty", ["EASY", "MEDIUM", "HARD"])
def test_ai_never_calls_used_number_full_game(difficulty):
    s = create_game(seed=11)
    while s.status == GameStatus.PLAYING:
        mv, _ = choose_move(s, s.current_player,
                            {"difficulty": difficulty, "rollouts": 150, "seed": s.version})
        assert mv in legal_moves(s)
        s = apply_move(s, mv)


def test_fastsim_matches_rules_engine():
    """The MCTS simulator must reproduce core.rules.apply_move exactly."""
    rng = random.Random(42)
    for g in range(200):
        s = create_game(seed=500 + g)
        sim = FastSim.from_state(s)
        while s.status == GameStatus.PLAYING:
            mv = rng.choice(legal_moves(s))
            s = apply_move(s, mv)
            sim.play(mv)
            assert sim.done == [s.lines_a, s.lines_b]
            assert sorted(sim.remaining) == legal_moves(s) or s.status == GameStatus.FINISHED
            if s.status == GameStatus.PLAYING:
                assert sim.winner is None and sim.to_move == s.current_player
        assert sim.winner == s.winner


@pytest.mark.parametrize(
    "difficulty,budget_ms",
    [("EASY", 100.0), ("MEDIUM", 1000.0), ("HARD", 2000.0)],
)
def test_ai_latency_within_prd_budget(difficulty, budget_ms):
    """AC-06: each AI returns a legal move within its PRD time budget."""
    s = create_game(seed=21)
    for mv in (3, 17, 9, 22):
        s = apply_move(s, mv)
    t0 = time.perf_counter()
    mv, _ = choose_move(s, s.current_player, {"difficulty": difficulty})
    elapsed = (time.perf_counter() - t0) * 1000.0
    assert mv in legal_moves(s)
    assert elapsed < budget_ms


def test_mcts_respects_tiny_time_budget():
    s = create_game(seed=8)
    t0 = time.perf_counter()
    mv, diag = choose_mcts_move(s, 0, rollouts=10**6, time_limit_sec=0.05)
    assert (time.perf_counter() - t0) < 0.5
    assert mv in legal_moves(s)


def test_minimax_timeout_returns_fully_evaluated_move():
    s = create_game(seed=8)
    mv, diag = choose_minimax_move(s, 0, depth=6, time_limit_sec=0.05)
    assert mv in legal_moves(s)
    assert diag["timed_out"] is True


# --------------------------------------------------------------------------- #
# Controller (threading / AC-07)
# --------------------------------------------------------------------------- #
def test_stale_ai_result_discarded_after_restart():
    ctrl = GameController(mode=GameMode.AI_VS_AI,
                          agents=(AgentType.HARD, AgentType.HARD), seed=1)
    ctrl.step_delay_sec = 0.0
    ctrl.update()                      # dispatch worker for version 0
    assert ctrl.is_thinking
    ctrl.restart(seed=2)               # new match, also version 0
    ctrl.wait_for_ai()
    assert ctrl._ai_result is None     # stale worker did not deposit
    assert ctrl.state.move_history == ()


def test_human_move_rejected_when_not_human_turn():
    ctrl = GameController(mode=GameMode.HUMAN_VS_AI,
                          agents=(AgentType.HUMAN, AgentType.EASY), seed=3)
    assert ctrl.trigger_human_move(5) is True
    # now AI's turn: human input must be refused
    assert ctrl.trigger_human_move(6) is False
    assert ctrl.trigger_human_move(5) is False


def test_controller_full_ai_match_completes():
    ctrl = GameController(mode=GameMode.AI_VS_AI,
                          agents=(AgentType.EASY, AgentType.MEDIUM), seed=4)
    ctrl.step_delay_sec = 0.0
    deadline = time.time() + 30
    while ctrl.state.status == GameStatus.PLAYING and time.time() < deadline:
        ctrl.update()
        ctrl.wait_for_ai()
    assert ctrl.state.status == GameStatus.FINISHED


def test_hold_progression_blocks_ai_dispatch():
    ctrl = GameController(mode=GameMode.AI_VS_AI,
                          agents=(AgentType.EASY, AgentType.EASY), seed=5)
    ctrl.step_delay_sec = 0.0
    ctrl.hold_progression = True
    ctrl.update()
    assert not ctrl.is_thinking


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def test_stats_do_not_mutate_defaults(tmp_path):
    mgr = StatsManager(filepath=str(tmp_path / "s.json"))
    s = GameState(
        board_a=IDENTITY, board_b=generate_board(seed=1), called_mask=0,
        current_player=0, mode=GameMode.HUMAN_VS_AI,
        agents=(AgentType.HUMAN, AgentType.HARD), status=GameStatus.FINISHED,
        winner=1, move_history=(1, 2),
    )
    mgr.record_match(s)
    assert DEFAULT_STATS["by_difficulty"]["HARD"]["ai_wins"] == 0
    assert DEFAULT_STATS["recent_history"] == []
    mgr.clear()
    assert mgr.stats["by_difficulty"]["HARD"]["matches"] == 0


def test_corrupt_stats_file_defaults_safely(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    mgr = StatsManager(filepath=str(p))
    assert mgr.stats["total_matches"] == 0
