# BINGO-BD AI Benchmarking & Academic Evaluation Report

**Project Title:** BINGO-BD — Traditional Bangladeshi School Bingo with Strategic AI Opponents
**Course / Laboratory:** AI Lab Final Project
**Report version:** v1.1 (post-audit), 2026-11-20
**Platform:** Windows 11 (10.0.26200), Python 3.13.15, Intel64 Family 6 Model 186
**Dependencies:** `pygame==2.6.1`, `pytest==9.2.0` (the benchmark uses only the standard library)

**Evaluated agents (identical to the in-game defaults in `ai/__init__.py`):**

| Level | Algorithm | Configuration |
| :--- | :--- | :--- |
| Easy | 1-step greedy heuristic | ≤ 25 successor evaluations, seeded tie-break |
| Medium | Minimax + alpha-beta | depth 2, move ordering, 1.0 s cap |
| Hard | MCTS (UCT) | 2000 rollouts, 1.5 s cap, c = √2, ε-greedy rollouts (ε = 0.2) |

---

## 1. Executive Summary

The benchmark ran 300 matches: 100 per pairing, with matched board seeds and balanced first-player order (50 / 50). The three agents now show a clear, monotonic skill progression, **Easy < Medium < Hard**, and every agent meets its PRD latency budget with a wide margin.

The v1.1 audit found and fixed one significant issue. In v1.0, MCTS used uniform random rollouts, which made "Hard" the **weakest** agent: it won 4 % against Easy and 2 % against Medium. Section 4.2 explains the cause and the fix.

---

## 2. Experimental Setup

- **Board configuration:** 5×5, integers 1–25, no FREE cell. Every call marks both boards.
- **Winning criterion:** ≥ 5 distinct completed lines (rows, columns, diagonals). If both players reach 5 on the same call, the game is a draw.
- **Seeds:** Easy–Medium 1000–1049, Easy–Hard 2000–2049, Medium–Hard 3000–3049. Each seed is played twice with swapped turn order. Per-move AI seed = `seed + 31 × version`.
- **Reproduce:** `python benchmark.py` (or `--games N`). Raw output: `data/benchmark_results.json`.

---

## 3. Results

### 3.1 Head-to-head tournament matrix (100 games per pairing)

| Pairing (A vs B) | A wins | B wins | Draws | Avg calls / game |
| :--- | :---: | :---: | :---: | :---: |
| Heuristic (Easy) vs Minimax d=2 (Medium) | 8 (8 %) | **56 (56 %)** | 36 (36 %) | 20.05 |
| Heuristic (Easy) vs MCTS 2000 (Hard) | 2 (2 %) | **72 (72 %)** | 26 (26 %) | 19.98 |
| Minimax d=2 (Medium) vs MCTS 2000 (Hard) | 3 (3 %) | **36 (36 %)** | 61 (61 %) | 20.61 |

### 3.2 Decision latency vs PRD budget

| Agent | Mean | P95 | Worst observed | PRD budget | Result |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Heuristic (Easy) | 0.2–1.0 ms | 0.4–1.5 ms | 2.5 ms | < 100 ms | **PASS** |
| Minimax d=2 (Medium) | 1.9–7.6 ms | 3.6–13.9 ms | 31.4 ms | < 1000 ms | **PASS** |
| MCTS 2000 (Hard) | 269–278 ms | 583–598 ms | 856.8 ms | < 2000 ms | **PASS** |

Ranges cover the two pairings each agent appears in. Latency varies with the opponent because games reach different positions. All AI work runs on a background thread, so even the Hard agent never blocks rendering. The UI keeps repainting and animates a "thinking…" indicator.

### 3.3 Comparison with v1.0

| Pairing | v1.0 result (MCTS 150 uniform rollouts) | v1.1 result |
| :--- | :--- | :--- |
| Easy vs Hard | Easy 72 % – Hard 4 % | Easy 2 % – **Hard 72 %** |
| Medium vs Hard | Medium 64 % – Hard 2 % | Medium 3 % – **Hard 36 %** |

---

## 4. Discussion

### 4.1 Minimax vs one-step heuristic
Every call marks **both** boards, so a call that helps the caller can also complete a line for the opponent. Depth-2 Minimax sees the opponent's immediate reply. It therefore avoids "suicide" calls that leave the opponent a winning number, which the greedy agent cannot detect. A unit test (`test_minimax_avoids_handing_opponent_the_win`) checks this. Result: 56 % wins and only 8 % losses against Easy.

### 4.2 Why uniform MCTS failed, and the fix
With uniformly random rollouts, both boards fill at roughly the same rate whatever the first move was. Rollout outcomes are then almost independent of the root action, so the value estimates are dominated by noise. With only 150–500 playouts, UCT could not tell good calls from bad ones.

The PRD explicitly allows "legal random calls with optional heuristic bias". v1.1 therefore makes three changes:

1. **ε-greedy rollouts:** 80 % of the time the mover plays the call that maximises *own line progress − opponent line progress* (line weights 1, 2, 4, 8, 40 by cells already marked). Otherwise it plays a uniform random call. This keeps playouts realistic while preserving exploration.
2. **Incremental bitboard simulator (`FastSim`):** roughly 3× cheaper per simulation than the v1.0 object-based playouts (≈ 0.13 ms vs ≈ 0.4 ms measured), even though every playout move now scores its candidates. This lets 2000 rollouts fit in a ≈ 0.27 s average. A test checks it move-for-move against the rules engine on 200 random games.
3. **Correct UCB1 scaling:** rewards are in [0, 1] (win 1, draw 0.5, loss 0), so c = √2 is the textbook constant. Values are stored from the mover's perspective (negamax form). An exact immediate-win check precedes the search.

Final action selection is unchanged: the most-visited root child (PRD §6).

### 4.3 Draw frequency
Draws rise as agent strength converges: 26 % (Easy–Hard), 36 % (Easy–Medium), 61 % (Medium–Hard). Strong players both steer towards boards that complete together, and the simultaneous-five-lines rule (AC-05) turns those races into draws. This is a property of the game, not a defect.

### 4.4 Statistical caution
With 100 games per pairing, a 95 % confidence interval on a win rate is roughly ±10 percentage points. The ordering Easy < Medium < Hard is clear in every pairing, but small differences between configurations should not be over-interpreted (PRD §8).

---

## 5. Verification

- `python -m pytest -q` passes **55 tests**: rules, state, all three AIs, controller threading, persistence, and the audit edge cases in `tests/test_edge_cases.py`. These include a PRD latency-budget test for each agent (AC-06).
- `python benchmark.py` reproduces the tables above and prints a PASS / FAIL line per latency budget.
