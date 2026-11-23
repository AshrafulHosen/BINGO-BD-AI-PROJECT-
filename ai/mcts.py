from __future__ import annotations
import math
import random
import time
from typing import Tuple, Dict, Any, Optional, List
from core.board import ALL_LINES
from core.state import GameState, GameStatus, DRAW
from core.rules import legal_moves

WIN_REWARD = 1.0
DRAW_REWARD = 0.5
LOSS_REWARD = 0.0

# Rollout policy weights indexed by "cells already marked in this line" (0..4).
# Index 4 means the call completes the line, which is by far the most valuable.
_POLICY_WEIGHTS = (1.0, 2.0, 4.0, 8.0, 40.0)


def _lines_by_number(board: Tuple[int, ...]) -> Tuple[Tuple[int, ...], ...]:
    """For each number 1..25 return the line indices (0..11) that contain it."""
    cell_lines: List[List[int]] = [[] for _ in range(25)]
    for li, line in enumerate(ALL_LINES):
        for cell in line:
            cell_lines[cell].append(li)
    out: List[Tuple[int, ...]] = [()] * 26
    for idx, val in enumerate(board):
        out[val] = tuple(cell_lines[idx])
    return tuple(out)


class FastSim:
    """
    Minimal mutable game simulator used inside the search.
    Mirrors core.rules.apply_move semantics exactly (shared marking, 5-line
    victory, simultaneous 5-line draw, exhaustion draw, turn alternation).
    """

    __slots__ = ("lines", "counts", "done", "remaining", "to_move", "winner", "n_called")

    def __init__(self, lines, counts, done, remaining, to_move, winner, n_called):
        self.lines = lines          # (lines_a_by_num, lines_b_by_num) - shared, read-only
        self.counts = counts        # [list[12], list[12]] marked cells per line
        self.done = done            # [completed_a, completed_b]
        self.remaining = remaining  # list of uncalled numbers
        self.to_move = to_move      # 0 / 1
        self.winner = winner        # None, 0, 1, DRAW
        self.n_called = n_called

    @classmethod
    def from_state(cls, state: GameState) -> "FastSim":
        lines = (_lines_by_number(state.board_a), _lines_by_number(state.board_b))
        counts = [[0] * 12, [0] * 12]
        for p, marked in ((0, state.marked_mask_a), (1, state.marked_mask_b)):
            for li, line in enumerate(ALL_LINES):
                counts[p][li] = sum(1 for c in line if (marked >> c) & 1)
        done = [sum(1 for c in counts[0] if c == 5), sum(1 for c in counts[1] if c == 5)]
        winner = state.winner if state.status == GameStatus.FINISHED else None
        return cls(lines, counts, done, legal_moves(state), state.current_player,
                   winner, len(state.move_history))

    def clone(self) -> "FastSim":
        return FastSim(self.lines, [self.counts[0][:], self.counts[1][:]], self.done[:],
                       self.remaining[:], self.to_move, self.winner, self.n_called)

    def play(self, number: int) -> None:
        """Apply a legal call in place."""
        self.remaining.remove(number)
        self.n_called += 1
        for p in (0, 1):
            cnt = self.counts[p]
            for li in self.lines[p][number]:
                cnt[li] += 1
                if cnt[li] == 5:
                    self.done[p] += 1
        da, db = self.done
        if da >= 5 and db >= 5:
            self.winner = DRAW
        elif da >= 5:
            self.winner = 0
        elif db >= 5:
            self.winner = 1
        elif not self.remaining:
            self.winner = DRAW
        else:
            self.to_move = 1 - self.to_move

    def policy_score(self, number: int, mover: int) -> float:
        """Greedy rollout score: own line progress minus opponent's progress."""
        opp = 1 - mover
        cm, co = self.counts[mover], self.counts[opp]
        s = 0.0
        for li in self.lines[mover][number]:
            s += _POLICY_WEIGHTS[cm[li]]
        for li in self.lines[opp][number]:
            s -= _POLICY_WEIGHTS[co[li]]
        return s

    def winning_moves(self) -> List[int]:
        """Calls that give the side to move an immediate (non-draw) victory."""
        mover = self.to_move
        out = []
        for n in self.remaining:
            probe = self.clone()
            probe.play(n)
            if probe.winner == mover:
                out.append(n)
        return out


def _reward_for(winner: Optional[int], player: int) -> float:
    if winner == player:
        return WIN_REWARD
    if winner is None or winner == DRAW:
        return DRAW_REWARD
    return LOSS_REWARD


def simulate_rollout(sim: FastSim, rng: random.Random, epsilon: float = 0.2) -> Optional[int]:
    """
    Plays ``sim`` (mutated in place) to a terminal state with an epsilon-greedy
    policy and returns the winner (0, 1 or DRAW).
    """
    rand = rng.random
    while sim.winner is None:
        rem = sim.remaining
        if rand() < epsilon:
            move = rem[int(rand() * len(rem))]
        else:
            mover = sim.to_move
            best = -1e9
            move = rem[0]
            for n in rem:
                sc = sim.policy_score(n, mover) + rand() * 0.01  # random tie-break
                if sc > best:
                    best = sc
                    move = n
        sim.play(move)
    return sim.winner


class MCTSNode:
    """Node in the MCTS tree storing statistics and tree topology."""

    __slots__ = ("parent", "action", "mover", "children", "untried_moves",
                 "visits", "value_sum", "terminal_winner")

    def __init__(
        self,
        sim: FastSim,
        parent: Optional["MCTSNode"] = None,
        action: Optional[int] = None,
        mover: Optional[int] = None,
        rng: Optional[random.Random] = None,
    ):
        self.parent = parent
        self.action = action
        self.mover = mover                  # player who made `action`
        self.children: Dict[int, MCTSNode] = {}
        self.visits = 0
        self.value_sum = 0.0                # reward for `mover`
        self.terminal_winner = sim.winner
        if sim.winner is None:
            moves = sim.remaining[:]
            if rng is not None:
                rng.shuffle(moves)
            self.untried_moves: List[int] = moves
        else:
            self.untried_moves = []

    def is_fully_expanded(self) -> bool:
        return not self.untried_moves

    def is_terminal(self) -> bool:
        return self.terminal_winner is not None

    def best_uct_child(self, c_param: float = math.sqrt(2)) -> "MCTSNode":
        """Child maximising UCB1 from the perspective of the player to move here."""
        log_n = math.log(max(1, self.visits))
        best_child = None
        best_score = -float("inf")
        for child in self.children.values():
            if child.visits == 0:
                return child
            score = child.value_sum / child.visits + c_param * math.sqrt(log_n / child.visits)
            if score > best_score:
                best_score = score
                best_child = child
        return best_child  # type: ignore[return-value]


def choose_mcts_move(
    state: GameState,
    player: int,
    rollouts: int = 2000,
    time_limit_sec: float = 1.5,
    c_param: float = math.sqrt(2),
    seed: Optional[int] = None,
    epsilon: float = 0.2,
) -> Tuple[int, Dict[str, Any]]:
    """
    Selects a move using UCT-based Monte Carlo Tree Search.
    Bounded by a rollout budget AND a wall-clock deadline.
    """
    start_time = time.perf_counter()
    deadline = start_time + max(0.0, time_limit_sec)
    moves = legal_moves(state)
    if not moves:
        raise ValueError("Cannot choose move from terminal or empty state.")

    def _diag(move: int, sims: int, visits: int, win_rate: float, note: str = "") -> Dict[str, Any]:
        d = {
            "algorithm": "MCTS (Hard)",
            "selected_move": move,
            "simulations": sims,
            "visits": visits,
            "win_rate": round(win_rate, 3),
            "latency_ms": round((time.perf_counter() - start_time) * 1000.0, 2),
        }
        if note:
            d["note"] = note
        return d

    if len(moves) == 1:
        return moves[0], _diag(moves[0], 0, 1, 0.5, "only legal call")

    root_sim = FastSim.from_state(state)
    root_sim.to_move = player
    rng = random.Random(seed if seed is not None else 10007 + state.version)

    # Tactical guard: an immediately winning call is always correct.  (UCT would
    # find it too, but this makes the behaviour exact rather than statistical.)
    wins_now = root_sim.winning_moves()
    if wins_now:
        mv = min(wins_now)
        return mv, _diag(mv, 0, 1, 1.0, "immediate win")

    root = MCTSNode(root_sim, rng=rng)
    simulations = 0
    check_every = 16

    while simulations < rollouts:
        if simulations % check_every == 0 and time.perf_counter() >= deadline:
            break

        node = root
        sim = root_sim.clone()

        # 1. Selection
        while node.is_fully_expanded() and not node.is_terminal() and node.children:
            node = node.best_uct_child(c_param)
            sim.play(node.action)  # type: ignore[arg-type]

        # 2. Expansion
        if not node.is_terminal() and node.untried_moves:
            action = node.untried_moves.pop()
            mover = sim.to_move
            sim.play(action)
            child = MCTSNode(sim, parent=node, action=action, mover=mover, rng=rng)
            node.children[action] = child
            node = child

        # 3. Simulation
        winner = simulate_rollout(sim, rng, epsilon) if sim.winner is None else sim.winner

        # 4. Backpropagation (reward relative to each node's mover)
        curr: Optional[MCTSNode] = node
        while curr is not None:
            curr.visits += 1
            if curr.mover is not None:
                curr.value_sum += _reward_for(winner, curr.mover)
            curr = curr.parent

        simulations += 1

    if not root.children:
        chosen = rng.choice(moves)
        return chosen, _diag(chosen, simulations, 0, 0.5, "budget exhausted before expansion")

    best_child = max(root.children.values(), key=lambda c: (c.visits, c.value_sum))
    win_rate = best_child.value_sum / max(1, best_child.visits)
    return int(best_child.action), _diag(  # type: ignore[arg-type]
        int(best_child.action), simulations, best_child.visits, win_rate  # type: ignore[arg-type]
    )
