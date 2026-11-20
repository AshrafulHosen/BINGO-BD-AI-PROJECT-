"""
BINGO-BD AI Benchmarking & Academic Evaluation Suite
Conducts controlled tournaments between Heuristic, Minimax, and MCTS agents.
Measures win rates, draw rates, mean decision latency, 95th percentile latency,
and average moves per game with matched board seeds and balanced turn orders.
"""

from __future__ import annotations
import argparse
import json
import math
import os
import platform
import statistics
import time
from typing import Dict, Any, List, Tuple
from core.state import GameMode, AgentType, GameStatus, DRAW
from core.rules import create_game, apply_move, legal_moves
from ai import choose_move


def _percentile(values: List[float], pct: float) -> float:
    """Linear-interpolated percentile (same definition as numpy's default)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return ordered[int(k)]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _mean(values: List[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def run_single_match(
    agent_0: AgentType,
    agent_1: AgentType,
    seed: int,
    config_0: Dict[str, Any],
    config_1: Dict[str, Any],
) -> Dict[str, Any]:
    """Runs a single head-to-head match and records latency and outcome."""
    state = create_game(
        mode=GameMode.AI_VS_AI,
        agents=(agent_0, agent_1),
        seed=seed,
    )

    latencies_0: List[float] = []
    latencies_1: List[float] = []

    while state.status == GameStatus.PLAYING:
        curr_p = state.current_player
        cfg = config_0 if curr_p == 0 else config_1
        # Set turn seed for reproducible tie breaking
        cfg_copy = dict(cfg)
        cfg_copy["seed"] = seed + state.version * 31

        t0 = time.perf_counter()
        move, diag = choose_move(state, curr_p, cfg_copy)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if curr_p == 0:
            latencies_0.append(elapsed_ms)
        else:
            latencies_1.append(elapsed_ms)

        state = apply_move(state, move)

    return {
        "winner": state.winner,
        "calls_count": len(state.move_history),
        "lines_0": state.lines_a,
        "lines_1": state.lines_b,
        "latencies_0": latencies_0,
        "latencies_1": latencies_1,
    }


def run_tournament(
    agent_a_name: str,
    agent_a_type: AgentType,
    config_a: Dict[str, Any],
    agent_b_name: str,
    agent_b_type: AgentType,
    config_b: Dict[str, Any],
    games_count: int = 50,
    base_seed: int = 1000,
) -> Dict[str, Any]:
    """
    Runs balanced tournament: half with A first, half with B first using matched seeds.
    """
    print(f"\n--- Tournament: {agent_a_name} vs {agent_b_name} ({games_count} matches) ---")

    wins_a = 0
    wins_b = 0
    draws = 0
    total_calls: List[int] = []
    all_latencies_a: List[float] = []
    all_latencies_b: List[float] = []

    half = games_count // 2

    # Round 1: Agent A plays as Player 0 (First)
    for i in range(half):
        seed = base_seed + i
        res = run_single_match(agent_a_type, agent_b_type, seed, config_a, config_b)
        w = res["winner"]
        if w == 0:
            wins_a += 1
        elif w == 1:
            wins_b += 1
        else:
            draws += 1
        total_calls.append(res["calls_count"])
        all_latencies_a.extend(res["latencies_0"])
        all_latencies_b.extend(res["latencies_1"])

    # Round 2: Agent B plays as Player 0 (First) with matched seeds
    for i in range(half):
        seed = base_seed + i
        res = run_single_match(agent_b_type, agent_a_type, seed, config_b, config_a)
        w = res["winner"]
        if w == 0:
            wins_b += 1
        elif w == 1:
            wins_a += 1
        else:
            draws += 1
        total_calls.append(res["calls_count"])
        all_latencies_b.extend(res["latencies_0"])
        all_latencies_a.extend(res["latencies_1"])

    summary = {
        "pairing": f"{agent_a_name} vs {agent_b_name}",
        "games_played": games_count,
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": draws,
        "win_rate_a_pct": round(wins_a / games_count * 100.0, 2),
        "win_rate_b_pct": round(wins_b / games_count * 100.0, 2),
        "draw_rate_pct": round(draws / games_count * 100.0, 2),
        "avg_calls_per_game": round(_mean(total_calls), 2),
        "latency_a_mean_ms": round(_mean(all_latencies_a), 3),
        "latency_a_p95_ms": round(_percentile(all_latencies_a, 95), 3),
        "latency_a_max_ms": round(max(all_latencies_a, default=0.0), 3),
        "latency_b_mean_ms": round(_mean(all_latencies_b), 3),
        "latency_b_p95_ms": round(_percentile(all_latencies_b, 95), 3),
        "latency_b_max_ms": round(max(all_latencies_b, default=0.0), 3),
    }

    print(f"Results: {agent_a_name} {wins_a}W ({summary['win_rate_a_pct']}%) | "
          f"{agent_b_name} {wins_b}W ({summary['win_rate_b_pct']}%) | Draws: {draws}")
    print(f"Latency {agent_a_name}: mean={summary['latency_a_mean_ms']}ms, p95={summary['latency_a_p95_ms']}ms")
    print(f"Latency {agent_b_name}: mean={summary['latency_b_mean_ms']}ms, p95={summary['latency_b_p95_ms']}ms")
    print(f"Avg Calls/Game: {summary['avg_calls_per_game']}")

    return summary


def run_full_benchmark(games_per_pairing: int = 100) -> Dict[str, Any]:
    """Runs all 3 head-to-head pairings and saves report."""
    os.makedirs("data", exist_ok=True)

    sys_info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Algorithm configurations - identical to the in-game defaults (ai/__init__.py)
    cfg_heuristic = {"difficulty": "EASY"}
    cfg_minimax = {"difficulty": "MEDIUM", "depth": 2, "time_limit_sec": 1.0}
    cfg_mcts = {"difficulty": "HARD", "rollouts": 2000, "time_limit_sec": 1.5}

    results = []

    # 1. Heuristic vs Minimax
    r1 = run_tournament(
        "Heuristic (Easy)", AgentType.EASY, cfg_heuristic,
        "Minimax d=2 (Medium)", AgentType.MEDIUM, cfg_minimax,
        games_count=games_per_pairing,
        base_seed=1000,
    )
    results.append(r1)

    # 2. Heuristic vs MCTS
    r2 = run_tournament(
        "Heuristic (Easy)", AgentType.EASY, cfg_heuristic,
        "MCTS 2000 (Hard)", AgentType.HARD, cfg_mcts,
        games_count=games_per_pairing,
        base_seed=2000,
    )
    results.append(r2)

    # 3. Minimax vs MCTS
    r3 = run_tournament(
        "Minimax d=2 (Medium)", AgentType.MEDIUM, cfg_minimax,
        "MCTS 2000 (Hard)", AgentType.HARD, cfg_mcts,
        games_count=games_per_pairing,
        base_seed=3000,
    )
    results.append(r3)

    budgets = {"heuristic": 100.0, "minimax": 1000.0, "mcts": 2000.0}
    worst = {
        "heuristic": max(r1["latency_a_max_ms"], r2["latency_a_max_ms"]),
        "minimax": max(r1["latency_b_max_ms"], r3["latency_a_max_ms"]),
        "mcts": max(r2["latency_b_max_ms"], r3["latency_b_max_ms"]),
    }
    compliance = {k: worst[k] < budgets[k] for k in budgets}
    print()
    print("Worst-case latency vs PRD budget:")
    for k in budgets:
        print(f"  {k:9s}: {worst[k]:8.2f} ms  (budget {budgets[k]:.0f} ms) -> "
              f"{'PASS' if compliance[k] else 'FAIL'}")

    output = {
        "system_info": sys_info,
        "games_per_pairing": games_per_pairing,
        "seeds": {"heuristic_vs_minimax": 1000, "heuristic_vs_mcts": 2000, "minimax_vs_mcts": 3000},
        "worst_case_latency_ms": worst,
        "latency_budget_ms": budgets,
        "latency_compliance": compliance,
        "configs": {
            "heuristic": cfg_heuristic,
            "minimax": cfg_minimax,
            "mcts": cfg_mcts,
        },
        "pairings": results,
    }

    with open("data/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print("\nBenchmark completed! Results saved to data/benchmark_results.json")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BINGO-BD AI tournament benchmark")
    parser.add_argument("--games", type=int, default=100,
                        help="matches per pairing (even number; PRD target >= 100)")
    args = parser.parse_args()
    run_full_benchmark(games_per_pairing=max(2, args.games - args.games % 2))
