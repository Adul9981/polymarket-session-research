#!/usr/bin/env python3
"""Path-based paper backtest of 'buy first deep side' rules (BTC 5m).

Uses actual fills as the execution source (no order book depth, no fees).
Entry: first fill at price <= 0.20 on either side; buy 1 share at that price.
Exit rules are simulated on the held side's subsequent fill path.

Variants (each is a separate trade on the same entry):
  hold            buy and hold to settlement (baseline)
  stop10          exit at first fill <= 0.10 after entry, else hold
  stop_half       exit at first fill <= entry*0.5, else hold
  rec035_T240     hold if price reaches >=0.35; else exit at first fill
                  at/after elapsed 240s (or hold if no exit liquidity)
  rec030_T240     same with >=0.30
  combo_035       stop10 + rec035_T240
  combo_030       stop10 + rec030_T240

Outputs: backtest_deepwater_summary.json, backtest_deepwater_trades.csv
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

DEEP_LIMIT = 0.20
WINDOW_SECONDS = 300
DIR = Path(__file__).resolve().parent.parent / "btc5m-multiday"


def load_meta():
    meta = {}
    with (DIR / "windows_meta.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            meta[int(row["window_ts"])] = row["winner"]
    return meta


def simulate_window(winner, w, path_u, path_d):
    """Run all variants for one window; returns list of trade dicts."""
    merged = []
    for side, path in (("U", path_u), ("D", path_d)):
        for t, p in path:
            merged.append((t, side, p))
    merged.sort()

    entry = None
    for t, side, p in merged:
        if p <= DEEP_LIMIT:
            entry = (t, side, p)
            break
    if entry is None:
        return []
    t0, side0, p0 = entry
    held = path_u if side0 == "U" else path_d
    win = winner.startswith(side0)
    deep_u = any(p <= DEEP_LIMIT for _, p in path_u)
    deep_d = any(p <= DEEP_LIMIT for _, p in path_d)
    cls = "BOTH" if (deep_u and deep_d) else "ONE"
    t_abs_240 = w + 240

    trades = []

    def add(variant, result, exit_price=None, exit_ts=None, exit_type=""):
        if result == "hold":
            pnl = (1 - p0) if win else -p0
            pe = 1.0 if win else 0.0
            te = None
        else:
            pnl = exit_price - p0
            pe = exit_price
            te = exit_ts
        trades.append({
            "variant": variant,
            "window_ts": w,
            "class": cls,
            "side": side0,
            "entry_price": round(p0, 4),
            "entry_elapsed_s": t0 - w,
            "winner": winner,
            "win": win,
            "exit_type": exit_type,
            "exit_price": round(pe, 4),
            "exit_ts": te,
            "pnl_cents": round(pnl * 100, 4),
        })

    def first_fill_at_or_after(t_ref):
        for t, p in held:
            if t >= t_ref:
                return t, p
        return None

    add("hold", "hold")

    def sim_stop(variant, stop):
        for t, p in held:
            if t > t0 and p <= stop:
                add(variant, "exit", p, t, "stop")
                return
        add(variant, "hold")

    def sim_rec(variant, threshold):
        for t, p in held:
            if t <= t0:
                continue
            if p >= threshold:
                add(variant, "hold", exit_type="recovered")
                return
        hit = first_fill_at_or_after(max(t_abs_240, t0 + 1))
        if hit:
            add(variant, "exit", hit[1], hit[0], "timeout")
        else:
            add(variant, "hold", exit_type="no_exit_liquidity")

    def sim_combo(variant, stop, threshold):
        for t, p in held:
            if t <= t0:
                continue
            if p <= stop:
                add(variant, "exit", p, t, "stop")
                return
            if p >= threshold:
                add(variant, "hold", exit_type="recovered")
                return
        hit = first_fill_at_or_after(max(t_abs_240, t0 + 1))
        if hit:
            add(variant, "exit", hit[1], hit[0], "timeout")
        else:
            add(variant, "hold", exit_type="no_exit_liquidity")

    sim_stop("stop10", 0.10)
    sim_stop("stop_half", p0 * 0.5)
    sim_rec("rec035_T240", 0.35)
    sim_rec("rec030_T240", 0.30)
    sim_combo("combo_035", 0.10, 0.35)
    sim_combo("combo_030", 0.10, 0.30)
    return trades


def summarize(trades):
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for t in trades if t["win"])
    pnl = sum(t["pnl_cents"] for t in trades)
    losses = [t for t in trades if t["pnl_cents"] < 0]
    max_consec = 0
    cur = 0
    for t in trades:
        cur = cur + 1 if t["pnl_cents"] < 0 else 0
        max_consec = max(max_consec, cur)
    return {
        "n": n,
        "wins": wins,
        "win_rate": round(wins / n, 4),
        "pnl_cents_total": round(pnl, 2),
        "ev_cents_per_trade": round(pnl / n, 4),
        "avg_loss_cents": round(
            sum(t["pnl_cents"] for t in losses) / len(losses), 2) if losses else None,
        "max_consecutive_losses": max_consec,
    }


def main():
    meta = load_meta()
    all_trades = []
    windows_seen = set()
    for path in sorted(DIR.glob("fills_*.ndjson")):
        by_window = defaultdict(lambda: {"U": [], "D": []})
        with path.open() as handle:
            for line in handle:
                f = json.loads(line)
                by_window[f["w"]][f["side"]].append((f["t"], f["p"]))
        for w, sides in by_window.items():
            if w not in meta or w in windows_seen:
                continue
            windows_seen.add(w)
            all_trades.extend(simulate_window(
                meta[w], w, sorted(sides["U"]), sorted(sides["D"])))

    variants = ["hold", "stop10", "stop_half", "rec035_T240",
                "rec030_T240", "combo_035", "combo_030"]
    summary = {"trades": len(all_trades), "windows": len(windows_seen),
               "variants": {}}
    for variant in variants:
        trades = [t for t in all_trades if t["variant"] == variant]
        entry = summarize(trades)
        entry["BOTH"] = summarize([t for t in trades if t["class"] == "BOTH"])
        entry["ONE"] = summarize([t for t in trades if t["class"] == "ONE"])
        entry["entry_le240"] = summarize(
            [t for t in trades if t["entry_elapsed_s"] <= 240])
        entry["entry_le180"] = summarize(
            [t for t in trades if t["entry_elapsed_s"] <= 180])
        entry["exit_types"] = {}
        for t in trades:
            key = t["exit_type"] or "hold_to_settlement"
            entry["exit_types"][key] = entry["exit_types"].get(key, 0) + 1
        summary["variants"][variant] = entry

    with (DIR / "backtest_deepwater_summary.json").open("w") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    with (DIR / "backtest_deepwater_trades.csv").open("w", newline="") as handle:
        fields = list(all_trades[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_trades)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
