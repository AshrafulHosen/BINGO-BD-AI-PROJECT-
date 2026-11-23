# BINGO-BD — Traditional Bangladeshi School Bingo with Strategic AI Opponents

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.6.1-green.svg)](https://www.pygame.org/)
[![Pytest](https://img.shields.io/badge/Pytest-9.2.0-yellow.svg)](https://docs.pytest.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

> A complete, professional, standalone desktop implementation of traditional Bangladeshi school Bingo, featuring pure-Python adversarial AI opponents (Heuristic, Minimax with Alpha-Beta Pruning, and UCT-based Monte Carlo Tree Search). Built strictly in accordance with the official BINGO-BD PRD v1.0 and visual UI concept sheet.

---

## 1. Project Introduction

In Bangladeshi schools, **Bingo** is a beloved pen-and-paper pastime played on 5×5 grids filled with numbers 1 through 25. Players alternate calling uncalled numbers; whenever a number is called, **every player crosses it out on their own board**. The first player to complete five distinct winning lines (rows, columns, or diagonals) spells **B-I-N-G-O** and wins the match.

**BINGO-BD** brings this nostalgic tradition to the desktop with a polished school-inspired graphical interface, multi-threaded responsive gameplay, local stats persistence, and three distinct AI algorithms implementing foundational concepts from Artificial Intelligence.

---

## 2. Official Game Rules & Core Mechanics

1. **Dual Independent Boards:**
   - Two 5×5 boards are generated with independent permutations of integers 1 through 25.
   - **No FREE center cell:** All 25 cells contain playable numbers (strictly following the PRD v1.0 authority).
2. **Turn-Based Calling & Shared Marking:**
   - Players alternate calling legal numbers (1–25 that have not been called previously).
   - Once called, the number is **automatically marked on BOTH boards** and added to the shared move history.
3. **12 Possible Winning Lines per Board:**
   - 5 horizontal rows
   - 5 vertical columns
   - 2 full diagonals (main diagonal and anti-diagonal)
4. **Scoring & Progress (B-I-N-G-O):**
   - Each completed line awards one letter: **B - I - N - G - O**.
   - Completed lines are counted strictly once (no double-counting).
   - Reaching 5 completed lines triggers victory.
5. **Terminal Outcomes & Draw Handling:**
   - If only one player reaches $\ge 5$ completed lines, that player wins immediately.
   - If **both players reach $\ge 5$ lines on the exact same call**, the match is declared a **DRAW**.
   - If all 25 numbers are called without either player reaching 5 lines, the match is declared a **DRAW**.

---

## 3. Technology Stack

- **Language:** Python 3.10+ (tested on Python 3.13)
- **GUI Framework:** Pygame 2.6.1
- **Testing Suite:** Pytest 9.2.0
- **AI Implementations:** Pure Python (standard library `math`, `random`, `time`, bitwise masks; zero external ML APIs or heavy frameworks)
- **Concurrency:** Python `threading` for background AI calculations with state-version validation
- **Persistence:** Local JSON (`data/statistics.json`, `data/settings.json`) with atomic file writes
- **Vector Graphics & Audio:** Procedural vector rendering and pure harmonic `.wav` generation

---

## 4. Repository Structure

```text
BINGO-BD/
│
├── main.py                     # Master desktop application entry point & event loop
├── requirements.txt            # Pinned dependencies (pygame, pytest)
├── pytest.ini                  # Pytest configuration
├── benchmark.py                # Automated AI tournament benchmarking suite
├── README.md                   # Full documentation & walkthrough
├── .gitignore                  # Keeps caches (__pycache__, .pytest_cache) out of git
│
├── docs/                       # Project documents (not loaded by the game)
│   ├── BINGO_BD_PRD_v1.0.pdf           # Product requirements
│   ├── BINGO-BD Game UI Concept Sheet.png  # Visual design reference
│   ├── BENCHMARK_REPORT.md             # AI evaluation report
│   ├── BINGO-BD_Final_Report.docx      # Final project report (print version)
│   ├── BINGO-BD_Presentation.pptx      # Presentation slides (videos embedded)
│   └── gameplay_videos/                # Sped-up gameplay recordings (.mp4)
│
├── core/                       # Pure-Python Game Engine (NO Pygame imports)
│   ├── __init__.py
│   ├── board.py                # 5x5 board permutations, line definitions, 25-bit masks
│   ├── state.py                # Immutable GameState dataclass, Enums, versioning
│   ├── rules.py                # Rule validation, transitions, line counter, terminal check
│   └── controller.py           # Threaded match manager, turn coordination, feedback modals
│
├── ai/                         # Strategic AI Algorithms (Pure Python)
│   ├── __init__.py             # Unified choose_move interface with error fallback
│   ├── evaluator.py            # Official evaluation formula & fast move heuristics
│   ├── heuristic.py            # Easy AI: 1-step greedy successor evaluation
│   ├── minimax.py              # Medium AI: Depth-limited Minimax with Alpha-Beta pruning
│   └── mcts.py                 # Hard AI: Monte Carlo Tree Search with UCT selection
│
├── ui/                         # Pygame Presentation Layer
│   ├── __init__.py
│   ├── theme.py                # Design tokens, DPI-aware renderer, AA shapes/icons, audio
│   ├── widgets.py              # Buttons, 5x5 tiles, letter badges, card containers
│   ├── menu.py                 # Screen 1: Main Menu & Title Screen
│   ├── modes.py                # Screen 2: Game Mode & Difficulty Selection
│   ├── game.py                 # Screen 3, 4, 5: Dual Boards, Calling Modal, Progress View
│   ├── results.py              # Screen 6: Game Over Screen (Victory, Defeat, Draw)
│   ├── settings_view.py        # Settings Screen (sound toggle, volume, AI speed)
│   └── stats_view.py           # Statistics Screen (records, win rates, safe reset)
│
├── data/                       # Persistence code + local JSON files
│   ├── settings_manager.py     # Load/save settings (atomic writes)
│   ├── stats_manager.py        # Load/save match statistics (atomic writes)
│   ├── statistics.json         # Cumulative win/loss records & match history
│   ├── settings.json           # User preferences
│   └── benchmark_results.json  # Tournament metrics output
│
├── assets/
│   └── sounds/                 # call / click / line / win / lose / draw .wav effects
│
└── tests/                      # Automated Test Suite (Pytest)
    ├── test_board.py           # 25-cell validation, seeds, line definitions
    ├── test_rules.py           # Move legality, line detection, 5-line win, draws
    ├── test_state.py           # State immutability, versioning, history tracking
    ├── test_heuristic.py       # Heuristic move validity, tie-breaking
    ├── test_minimax.py         # Minimax legal moves, alpha-beta cutoffs
    ├── test_mcts.py            # MCTS UCT rollouts, terminal backpropagation
    ├── test_game_modes.py      # Integration flow across modes 1, 2, 3 and stats
    └── test_edge_cases.py      # Audit edge cases: tactics, budgets, threading, fuzzing
```

---

## 5. Installation & Setup

### Prerequisites
Ensure Python 3.10 or higher is installed and accessible from your command line.

### Step 1: Clone or Open the Repository
```bash
cd "c:\Users\Ashraful\OneDrive\Desktop\AI final project"
```

### Step 2: Install Dependencies
Install the pinned dependencies using `pip`:
```bash
pip install -r requirements.txt
```

---

## 6. How to Run the Game

Launch the application by running `main.py`:
```bash
python main.py
```

---

## 7. Game Controls & UI Navigation

- **Calling a number (select → call):**
  - Click any uncalled number on **either** board (or on the *Called Numbers* sheet) to select it. It is highlighted in gold on both boards.
  - Click it again, press **Call Number**, or hit **Enter / Space** to call it. **Esc** clears the selection.
  - You can also type a number (e.g. `1` `7`) to select it.
- **Call popup:** after every call a short popup confirms the number (and any new lines). It closes by itself; any click or key closes it sooner. AI moves wait while it is shown.
- **Toolbar:** Menu, Restart (`Ctrl+R`), Progress (`P`) for the B-I-N-G-O progress view, and Sound (`M`).
- **AI vs AI:** Pause / Resume button (or Enter / Space).
- **Display:**
  - On Windows the app is per-monitor DPI aware, so it is never bitmap-stretched.
  - The default window size is picked from your desktop resolution and scaling (1280×720, 1600×900 or 1920×1080 design sizes × DPI).
  - The window is freely resizable (minimum 960×540) and **F11** / **Alt+Enter** toggles full screen.
  - Everything is drawn at the window's native pixel resolution inside a 16:9 viewport, so text and shapes stay sharp at 1080p, 1440p and 4K.

---

## 8. Game Modes

### Mode 1: Human vs AI
- The human player plays as Player 1 (Blue Board) against a strategic computer opponent (Red Board).
- The player selects an AI difficulty (Easy, Medium, or Hard) before starting.
- Human input is locked while the AI is calculating its move on a background thread.

### Mode 2: Human vs Human
- Two local players compete on the same computer.
- Both 5×5 boards remain visible.
- Turn alternation is indicated on the top status banner and active board highlights.

### Mode 3: AI vs AI
- Watch two automated AI agents compete head-to-head.
- Independent strategy selection for both Player 1 and Player 2 (e.g. Minimax vs MCTS).
- Includes **Pause / Resume** controls and configurable animation pacing ("Normal" 0.8s, "Fast" 0.2s).

---

## 9. AI Difficulty & Search Algorithms

### Easy: One-Step Heuristic Greedy Search
- Evaluates all legal uncalled numbers ($k \le 25$) with one-step lookahead.
- Uses the official PRD evaluation function:
  $$E = 100 \times (\text{completed}_{\text{ai}} - \text{completed}_{\text{opp}}) + 10 \times (\text{potential}_{\text{ai}} - \text{potential}_{\text{opp}})$$
  where potential for each incomplete line is $(\text{marked\_cells} / 5)^2$.
- Breaks ties deterministically using a seeded random selector.
- The centre cell lies on 4 lines (row, column, both diagonals), so it naturally scores highest on an empty board. A move that completes a line jumps the score by ≈ +94 (100 for the completed line minus its lost potential).
- **Average Decision Latency:** $\approx 0.20\text{ ms}$ (Target: $< 100\text{ ms}$).

### Medium: Depth-Limited Minimax with Alpha-Beta Pruning
- Formulates the match as a 2-player zero-sum adversarial game.
- Search depth: $d = 2$ plies (expandable to 3).
- Evaluates terminal states with dominant scores: $+100000 - \text{depth}$ for win, $-100000 + \text{depth}$ for loss, $0$ for draw.
- Leaf nodes are scored using the heuristic evaluation function.
- Implements **action ordering** by sorting moves based on potential gain to maximize alpha-beta branch cutoffs.
- If the time budget runs out, the search aborts cleanly and returns the best **fully evaluated** root move (PRD §6). It stops early as soon as a forced win is proven.
- **Average Decision Latency:** $\approx 1.70\text{ ms}$ (Target: $< 1000\text{ ms}$).

### Hard: Monte Carlo Tree Search (MCTS with UCT)
- Pure UCT with the four canonical phases:
  1. **Selection:** descends the tree, picking the child that maximises UCB1 ($c = \sqrt{2}$):
     $$\text{UCT}_i = \frac{W_i}{N_i} + c \sqrt{\frac{\ln N_p}{N_i}}$$
     Each node stores its reward from the perspective of the player who moved into it, so alternating objectives are handled by negamax-style sign adjustment.
  2. **Expansion:** expands one untried legal call.
  3. **Simulation:** plays an **epsilon-greedy** rollout to a terminal state. With probability $1-\varepsilon$ ($\varepsilon = 0.2$) the mover picks the call that helps its own lines most relative to the opponent's; otherwise it calls a random legal number. Victory is checked after every call.
  4. **Backpropagation:** win = 1, draw = 0.5, loss = 0.
- Rollouts run on a compact incremental bitboard simulator (`FastSim`), which a test verifies against the rules engine on 200 random games.
- A tactical guard plays an immediately winning call without searching.
- Selects the **most-visited** root child.
- Budget: 2000 rollouts, capped at 1.5 s wall-clock time.
- **Average Decision Latency:** ≈ 270 ms, p95 ≈ 600 ms (target < 2000 ms).

---

## 10. Automated Testing & Quality Assurance

Run the complete Pytest suite:
```bash
python -m pytest -v
```

All 55 automated unit and integration tests verify:
- Board permutations, uniqueness, and seed reproducibility.
- 12-line detection (5 rows, 5 columns, 2 diagonals) and overlapping line counting.
- 5-line immediate victory and simultaneous 5-line draws.
- State immutability, versioning, and turn alternation.
- AI legal action generation, heuristic selection, alpha-beta cutoffs, and MCTS rollouts.
- Fault-tolerant AI error fallback to heuristic.
- Local statistics persistence and atomic saving.
- (`test_edge_cases.py`) Bool/non-integer move rejection, moves after game end, 4-line simultaneous completion, the ≥ 5 threshold, a 300-game random fuzz of terminal consistency, and win-in-one detection by all three AIs. Also: Minimax never makes a "suicide" call that hands the opponent the win, seeded tie-breaking, search purity, FastSim ≡ rules engine, PRD latency budgets (AC-06), timeout behaviour, and stale-AI-worker rejection after restart (AC-07).

---

## 11. AI Benchmarking Suite

Execute the automated tournament comparison:
```bash
python benchmark.py
```
This runs 300 balanced matches (100 per pairing; change it with `--games N`) across all three pairings. It uses the same AI configs as the game, logs win rates and mean / p95 / max decision latencies, checks the PRD latency budgets, and updates `data/benchmark_results.json`. See [docs/BENCHMARK_REPORT.md](docs/BENCHMARK_REPORT.md) for full academic details.

---

## 12. Settings & Local Statistics

- **Settings Screen:**
  - Toggle sound effects on/off.
  - Adjust master volume.
  - Toggle AI move pacing between Normal (0.8s) and Fast (0.2s).
- **Statistics Screen:**
  - Tracks cumulative matches, human wins, AI wins, and draws.
  - Detailed breakdown of Human vs AI record by difficulty (Easy, Medium, Hard).
  - "Clear Stats" button with two-step confirmation.

---

## 13. Known Limitations & Architectural Notes

1. **Local Desktop Only:** Designed specifically for Windows/desktop single-process execution; online multiplayer and cloud saves were intentionally excluded per the PRD specification.
2. **Perfect Information Search:** Both boards are visible in Version 1.0, treating the game as a perfect-information turn-based adversarial search problem.
3. **MCTS Rollout Variance:** Every call marks both boards, so *uniform* random rollouts are very noisy. In v1.0 they made "Hard" weaker than "Easy". v1.1 uses the PRD-sanctioned heuristic-biased (epsilon-greedy) rollouts, which restore the intended Easy < Medium < Hard progression (see docs/BENCHMARK_REPORT.md).
