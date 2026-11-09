#!/usr/bin/env python3
"""BTC 5m deep-water fills vs first-touch strategy linkage analysis.

Inputs (same directory):
  fills_top40_285k.json   actual fills for top-40 volume windows
  windows_12h.json        144 window metadata (12h snapshot)

Outputs:
  deepwater_link_summary.json        machine-readable results
  deepwater_link_top_addresses.csv   per-address behavior table
  printed console report

Read-only: never modifies fills/windows inputs.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

DIR = Path(__file__).resolve().parent
DEEP_LIMIT = 0.20  # 20 cents, matching first-touch 20c tier


def load(name):
    with (DIR / name).open() as handle:
        return json.load(handle)


def wilson_low(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    half = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5
    return (center - half) / denom


def main():
    fills = load("fills_top40_285k.json")
    windows = load("windows_12h.json")

    # --- window winner map (fills already carry window_winner) ---
    win_map = {w["ts"]: w["winner"] for w in windows if w.get("winner")}

    # Per-window per-side deep-fill stats (price <= 0.20)
    by_win = defaultdict(lambda: {"Up": [], "Down": []})
    for f in fills:
        side = "Up" if f["outcome"] == "Up" else "Down"
        if f["price"] <= DEEP_LIMIT:
            by_win[f["window_ts"]][side].append(f)

    classes = defaultdict(int)
    first_deep_rows = []   # one row per window with >=1 deep fill
    for ts, sides in sorted(by_win.items()):
        winner = win_map.get(ts) or (fills and next(
            (f["window_winner"] for f in fills if f["window_ts"] == ts), None))
        up, down = sides["Up"], sides["Down"]
        if up and down:
            cls = "BOTH"
        elif up or down:
            cls = "ONE"
        else:
            cls = "NONE"
        classes[cls] += 1
        if cls == "NONE":
            continue
        deep = sorted(up + down, key=lambda f: f["timestamp"])
        first = deep[0]
        first_side = "Up" if first["outcome"] == "Up" else "Down"
        first_deep_rows.append({
            "window_ts": ts,
            "class": cls,
            "winner": winner,
            "first_side": first_side,
            "first_deep_price": first["price"],
            "first_deep_ts": first["timestamp"],
            "up_deep_buys": sum(f["size"] for f in up if f["side"] == "BUY"),
            "down_deep_buys": sum(f["size"] for f in down if f["side"] == "BUY"),
        })

    def win_rate(rows, pred):
        wins = sum(1 for r in rows
                   if pred(r) and r["winner"].upper() == r["first_side"].upper())
        n = sum(1 for r in rows if pred(r))
        return wins, n

    all_rows = first_deep_rows
    both_rows = [r for r in all_rows if r["class"] == "BOTH"]
    one_rows = [r for r in all_rows if r["class"] == "ONE"]

    w_all, n_all = win_rate(all_rows, lambda r: True)
    w_both, n_both = win_rate(both_rows, lambda r: True)
    w_one, n_one = win_rate(one_rows, lambda r: True)

    # One-share EV per trigger: buy at first deep price, hold to settlement.
    def ev_per_trigger(rows):
        vals = []
        for r in rows:
            stake = r["first_deep_price"]
            vals.append((1 - stake)
                        if r["winner"].upper() == r["first_side"].upper()
                        else -stake)
        return sum(vals), len(vals)

    ev_all, _ = ev_per_trigger(all_rows)
    ev_both, n_ev_both = ev_per_trigger(both_rows)
    ev_one, n_ev_one = ev_per_trigger(one_rows)

    # Realized P&L on actual deep BUY fills (buy & hold to settlement)
    deep_buys = [f for f in fills if f["side"] == "BUY" and f["price"] <= DEEP_LIMIT]
    invested = sum(f["size"] * f["price"] for f in deep_buys)
    pnl = 0.0
    win_pnl_by_window = defaultdict(float)
    for f in deep_buys:
        win = f["outcome"].upper() == f["window_winner"].upper()
        f_pnl = f["size"] * (1 - f["price"]) if win else -f["size"] * f["price"]
        pnl += f_pnl
        win_pnl_by_window[f["window_ts"]] += f_pnl

    window_pnls = sorted(
        ((ts, p) for ts, p in win_pnl_by_window.items()),
        key=lambda x: -x[1])
    top3_share = sum(p for _, p in window_pnls[:3]) / pnl if pnl else None
    positive_windows = sum(1 for _, p in window_pnls if p > 0)

    # --- per-address behavior ---
    addr = defaultdict(lambda: {
        "wallet": "", "name": "", "fills": 0, "buys": 0, "sells": 0, "buy_usd": 0.0,
        "sell_usd": 0.0, "deep_buys": 0, "deep_buy_usd": 0.0,
        "pre_window_buys": 0, "windows": set(), "pnl_all": 0.0,
        "pnl_deep": 0.0, "deep_wins": 0,
    })
    for f in fills:
        a = addr[f["proxyWallet"]]
        a["wallet"] = f["proxyWallet"]
        a["name"] = f.get("name") or f.get("pseudonym") or ""
        a["fills"] += 1
        a["windows"].add(f["window_ts"])
        win = f["outcome"].upper() == f["window_winner"].upper()
        if f["side"] == "BUY":
            a["buys"] += 1
            a["buy_usd"] += f["size"] * f["price"]
            a["pnl_all"] += f["size"] * (1 - f["price"]) if win else -f["size"] * f["price"]
            if f["timestamp"] < f["window_ts"]:
                a["pre_window_buys"] += 1
            if f["price"] <= DEEP_LIMIT:
                a["deep_buys"] += 1
                a["deep_buy_usd"] += f["size"] * f["price"]
                a["pnl_deep"] += f["size"] * (1 - f["price"]) if win else -f["size"] * f["price"]
                if win:
                    a["deep_wins"] += 1
        else:
            a["sells"] += 1
            a["sell_usd"] += f["size"] * f["price"]

    # --- first-touch reference from crypto repo (BTC 20c, no filter) ---
    # quoted in final doc from analyze_all_assets_first_touch.py output.

    top = sorted(addr.values(), key=lambda a: -a["pnl_all"])[:20]
    with (DIR / "deepwater_link_top_addresses.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "wallet", "name", "fills", "windows", "buys", "sells",
            "buy_usd", "sell_usd", "pre_window_buys", "deep_buys",
            "deep_buy_usd", "pnl_all_usd", "pnl_deep_usd", "deep_win_rate",
        ])
        for a in top:
            writer.writerow([
                a["wallet"], a["name"], a["fills"], len(a["windows"]),
                a["buys"], a["sells"],
                round(a["buy_usd"], 2), round(a["sell_usd"], 2),
                a["pre_window_buys"], a["deep_buys"],
                round(a["deep_buy_usd"], 2), round(a["pnl_all"], 2),
                round(a["pnl_deep"], 2),
                round(a["deep_wins"] / a["deep_buys"], 4) if a["deep_buys"] else "",
            ])

    # Per-window detail CSV
    with (DIR / "deepwater_link_windows.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "window_ts", "utc", "class", "winner", "first_deep_side",
            "first_deep_price", "up_deep_buy_usd", "down_deep_buy_usd",
        ])
        for r in sorted(first_deep_rows, key=lambda x: x["window_ts"]):
            from datetime import datetime, timezone
            utc = datetime.fromtimestamp(r["window_ts"], timezone.utc).isoformat()
            writer.writerow([
                r["window_ts"], utc, r["class"], r["winner"], r["first_side"],
                r["first_deep_price"],
                round(r["up_deep_buys"], 2), round(r["down_deep_buys"], 2),
            ])

    # --- cross-validation vs first-touch events (BTC 20c) ---
    summary = {}
    cross = None
    if len(sys.argv) > 1:
        ft_path = Path(sys.argv[1])
        ft_rows = []
        with ft_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                if row["asset"] == "BTC" and int(row["limit_c"]) == 20:
                    ft_rows.append(row)
        ft_by_win = {int(r["ts_window"]): r for r in ft_rows}
        joined = []
        for r in first_deep_rows:
            ft = ft_by_win.get(r["window_ts"])
            if not ft:
                continue
            ft_side = ft.get("first_side") or "no_touch"
            win = r["winner"].upper()
            joined.append({
                "window_ts": r["window_ts"],
                "class": r["class"],
                "winner": win,
                "ask_first_side": ft_side,
                "fill_first_deep_side": r["first_side"].upper(),
                "ask_first_wins": ft_side.upper() == win,
                "fill_first_deep_wins": r["first_side"].upper() == win,
            })
        if joined:
            def rates(rows, key):
                return sum(1 for x in rows if x[key]), len(rows)
            cross = {
                "n_windows_joined": len(joined),
                "ask_touch_first_side": {
                    "wins": rates(joined, "ask_first_wins")[0],
                    "n": rates(joined, "ask_first_wins")[1],
                },
                "fill_deep_first_side": {
                    "wins": rates(joined, "fill_first_deep_wins")[0],
                    "n": rates(joined, "fill_first_deep_wins")[1],
                },
                "same_first_side": sum(
                    1 for x in joined
                    if x["ask_first_side"] == x["fill_first_deep_side"]),
            }
            with (DIR / "deepwater_link_cross_first_touch.csv").open(
                    "w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(joined[0].keys()))
                writer.writeheader()
                writer.writerows(joined)
            summary["cross_first_touch_btc_20c"] = cross

    summary.update({
        "data": {
            "fills": len(fills),
            "windows_in_fills": len(by_win),
            "deep_limit_cents": int(DEEP_LIMIT * 100),
        },
        "classes": dict(classes),
        "first_deep_side_win_rates": {
            "all": {"wins": w_all, "n": n_all,
                    "rate": round(w_all / n_all, 4) if n_all else None,
                    "wilson_low": round(wilson_low(w_all, n_all), 4) if n_all else None},
            "both_sides": {"wins": w_both, "n": n_both,
                           "rate": round(w_both / n_both, 4) if n_both else None,
                           "wilson_low": round(wilson_low(w_both, n_both), 4) if n_both else None},
            "one_side": {"wins": w_one, "n": n_one,
                         "rate": round(w_one / n_one, 4) if n_one else None,
                         "wilson_low": round(wilson_low(w_one, n_one), 4) if n_one else None},
        },
        "one_share_ev_cents_per_trigger": {
            "all": round(ev_all / len(all_rows) * 100, 2) if all_rows else None,
            "both_sides": round(ev_both / n_ev_both * 100, 2) if n_ev_both else None,
            "one_side": round(ev_one / n_ev_one * 100, 2) if n_ev_one else None,
        },
        "realized_deep_buy_hold": {
            "fills": len(deep_buys),
            "invested_usd": round(invested, 2),
            "pnl_usd": round(pnl, 2),
            "return_pct": round(pnl / invested * 100, 2) if invested else None,
            "windows_with_deep_buys": len(window_pnls),
            "positive_windows": positive_windows,
            "top3_windows_pnl_share": round(top3_share, 4) if top3_share else None,
            "top3_windows": [
                {"window_ts": ts, "pnl_usd": round(p, 2)} for ts, p in window_pnls[:3]
            ],
        },
    })
    with (DIR / "deepwater_link_summary.json").open("w") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    # console report
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
