"""Weekly paper-trading summary — system + Ava, side by side.

Every Friday after the close, this reads the two paper runs'
durable state and writes one plain-language page so Neko can see
"our numbers for the week":

- The SYSTEM live-paper run (``live_paper/state.json``): the
  $10,000 virtual pot, wide-6, one day at a time.
- AVA's daily paper run (``data/ava-daily/state.json`` plus the
  ``"run": "daily"`` records in ``data/ava-evidence.jsonl``):
  her own $100 pot, the same wide-6 rules with the MACD
  complement, one evidence record per trade, one lesson per
  closed trade.

Only DAILY evidence counts here: the 262 historical-window
records already in ``data/ava-evidence.jsonl`` (FRESH-1/2/3,
no ``"run"`` key) are simulations from Nov 9–10, not this
week's real days, and are excluded.

Paper only, always. Nothing here promises profits; the footer
says what a good week does and does not prove.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .ava.daily_trading import compute_summary as ava_compute_summary
from .ava.daily_trading import default_ava_daily_dir
from .ava.lessons import lessons_path
from .ava.paper_trading import evidence_path
from .live_paper_trading import compute_summary as system_compute_summary
from .live_paper_trading import default_live_dir

NY_TZ = ZoneInfo("America/New_York")
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

PAPER_ONLY_BANNER = (
    "PAPER ONLY — virtual money on both pots, no live brokerage, "
    "no real money. Trading involves substantial risk of loss. "
    "This weekly summary does not promise profits. Past performance "
    "does not guarantee future results."
)


def week_bounds(week_end: date | None = None) -> tuple[date, date]:
    """Monday and Friday of the week containing ``week_end``.

    Defaults to the most recent Friday on or before today
    (America/New_York) — so a Friday run reports the week just
    closed. A Monday–Friday week only; weekends are not trading
    days for this report.
    """
    if week_end is None:
        today = datetime.now(NY_TZ).date()
        # Friday = weekday 4. Walk back to the most recent Friday.
        days_back = (today.weekday() - 4) % 7
        week_end = today - timedelta(days=days_back)
    monday = week_end - timedelta(days=week_end.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _in_week(iso_date: str | None, monday: date, friday: date) -> bool:
    if not iso_date:
        return False
    try:
        d = date.fromisoformat(str(iso_date)[:10])
    except ValueError:
        return False
    return monday <= d <= friday


def _weekday_runs(run_history: list[dict], monday: date, friday: date) -> dict:
    """run_date -> run summary, for runs inside this week.

    A day can have more than one run (the first run opens trades,
    a second run the same day finds nothing new) — sum the
    opened/closed/P&L across them so the day's numbers are the
    day's numbers, and keep the last status."""
    out: dict[str, dict] = {}
    for run in run_history or []:
        if not _in_week(run.get("run_date"), monday, friday):
            continue
        day = run["run_date"]
        prev = out.get(day)
        if prev is None:
            out[day] = dict(run)
        else:
            prev["trades_opened"] = prev.get("trades_opened", 0) + run.get("trades_opened", 0)
            prev["trades_closed"] = prev.get("trades_closed", 0) + run.get("trades_closed", 0)
            prev["realised_pnl_usd"] = round(
                prev.get("realised_pnl_usd", 0.0) + run.get("realised_pnl_usd", 0.0), 2)
            # The day counts as "ok" if any run that day did real work.
            prev["status"] = "ok" if "ok" in (prev["status"], run.get("status")) \
                else run.get("status", prev["status"])
    return out


def _system_week(state: dict | None, monday: date, friday: date) -> dict:
    """System side of the week, from durable state only."""
    if state is None:
        return {"started": False}
    closed_week = [t for t in state.get("closed_trades", [])
                   if _in_week(t.get("exit_date"), monday, friday)]
    wins = [t for t in closed_week if t["pnl_usd"] > 0]
    runs = _weekday_runs(state.get("run_history", []), monday, friday)
    totals = system_compute_summary(state)
    return {
        "started": True,
        "starting_cash_usd": state.get("starting_cash_usd", 10_000.0),
        "cash_usd": totals["cash_usd"],
        "portfolio_value_usd": totals["portfolio_value_usd"],
        "opened_week": sum(r.get("trades_opened", 0) for r in runs.values()),
        "closed_week": len(closed_week),
        "wins_week": len(wins),
        "win_rate_pct": round(len(wins) / len(closed_week) * 100, 1) if closed_week else 0.0,
        "pnl_week_usd": round(sum(t["pnl_usd"] for t in closed_week), 2),
        "expectancy_usd": round(sum(t["pnl_usd"] for t in closed_week) / len(closed_week), 2)
        if closed_week else 0.0,
        "open_positions": state.get("open_positions", []),
        "closed_week_trades": closed_week,
        "runs": runs,
        "lifetime": totals,
    }


def _ava_week(state: dict | None, evidence: list[dict], lessons: list[dict],
              monday: date, friday: date) -> dict:
    """Ava's side of the week: daily evidence records only."""
    daily = [r for r in evidence if r.get("run") == "daily"]
    placed = [r for r in daily
              if r.get("status") == "placed" and _in_week(r.get("run_date"), monday, friday)]
    closed = [r for r in daily
              if r.get("status") == "closed" and _in_week(r.get("run_date"), monday, friday)]
    wins = [r for r in closed if r.get("won")]
    # Lessons are counted only when they match a DAILY trade closed
    # this week (same symbol + same P&L to the cent). The 262
    # lessons from the Nov 9–10 historical-window simulations were
    # written on Nov 10, inside this week by date — counting by
    # date alone would credit them to the week. One lesson per
    # close, so this also caps at the week's closed trades.
    closed_keys = {(r.get("symbol"), round(r.get("pnl_usd", 0.0), 2)) for r in closed}
    lessons_week = [row for row in lessons
                    if (row.get("symbol"), round(row.get("pnl", 0.0) or 0.0, 2)) in closed_keys]
    runs = _weekday_runs(state.get("run_history", []) if state else [], monday, friday)
    totals = ava_compute_summary(state) if state is not None else None
    return {
        "started": state is not None,
        "starting_cash_usd": state.get("starting_cash_usd", 100.0) if state else 100.0,
        "cash_usd": totals["cash_usd"] if totals else None,
        "portfolio_value_usd": totals["portfolio_value_usd"] if totals else None,
        "opened_week": len(placed),
        "closed_week": len(closed),
        "wins_week": len(wins),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
        "pnl_week_usd": round(sum(r.get("pnl_usd", 0.0) for r in closed), 2),
        "expectancy_usd": round(sum(r.get("pnl_usd", 0.0) for r in closed) / len(closed), 2)
        if closed else 0.0,
        "lessons_week": len(lessons_week),
        "open_positions": state.get("open_positions", []) if state else [],
        "closed_week_trades": closed,
        "runs": runs,
        "lifetime": totals,
    }


def _money(value: float | None, signed: bool = False) -> str:
    """Dollar formatting. P&L gets a +/− sign; balances do not."""
    if value is None:
        return "—"
    sign = "+" if (signed and value > 0) else ""
    return f"${sign}{value:,.2f}"


def render_weekly_report(monday: date, friday: date,
                         system: dict, ava: dict) -> str:
    """One plain-language page: the week's numbers, side by side."""
    lines = [
        f"# VaultTec — Weekly Paper Trading, {monday.isoformat()} to {friday.isoformat()}",
        "",
        f"> **{PAPER_ONLY_BANNER}**",
        "",
        "## The week in one line",
        "",
    ]
    if not system["started"] and not ava["started"]:
        lines += [
            "Neither paper run has started yet — no trades this week. "
            "The system run and Ava's daily run both start the first "
            "weekday they are scheduled.",
            "",
        ]
    else:
        if system["started"]:
            lines += [
                f"- **System** (${system['starting_cash_usd']:,.0f} pot): "
                f"{system['opened_week']} trade(s) opened, "
                f"{system['closed_week']} closed, {system['wins_week']} win(s), "
                f"paper P&L **{_money(system['pnl_week_usd'], signed=True)}** this week.",
            ]
        else:
            lines.append("- **System** — hasn't started yet, no trades this week.")
        if ava["started"]:
            lines += [
                f"- **Ava** (${ava['starting_cash_usd']:,.0f} pot): "
                f"{ava['opened_week']} trade(s) opened, "
                f"{ava['closed_week']} closed, {ava['wins_week']} win(s), "
                f"paper P&L **{_money(ava['pnl_week_usd'], signed=True)}** this week, "
                f"{ava['lessons_week']} lesson(s) learned.",
            ]
        else:
            lines.append("- **Ava** — hasn't started her daily run yet, "
                         "no trades this week.")
        lines += [
            "",
            "A $100 pot moves by dollars, not hundreds — that is what "
            "the small pot is for: proving the rules work, one day at "
            "a time. The $10,000 pot shows the same rules at scale.",
            "",
        ]
    lines += [
        "## Side by side — this week",
        "",
        "|  | System ($10,000 pot) | Ava ($100 pot) |",
        "|---|---:|---:|",
        f"| Trades opened | {system.get('opened_week', '—')} | {ava.get('opened_week', '—')} |",
        f"| Trades closed | {system.get('closed_week', '—')} | {ava.get('closed_week', '—')} |",
        f"| Wins | {system.get('wins_week', '—')} | {ava.get('wins_week', '—')} |",
        f"| Win rate | {system.get('win_rate_pct', '—')}% | {ava.get('win_rate_pct', '—')}% |",
        f"| Paper P&L this week | {_money(system.get('pnl_week_usd'), signed=True)} | {_money(ava.get('pnl_week_usd'), signed=True)} |",
        f"| Expectancy per trade | {_money(system.get('expectancy_usd'), signed=True)} | {_money(ava.get('expectancy_usd'), signed=True)} |",
        f"| Virtual cash now | {_money(system.get('cash_usd'))} | {_money(ava.get('cash_usd'))} |",
        f"| Portfolio value now | {_money(system.get('portfolio_value_usd'))} | {_money(ava.get('portfolio_value_usd'))} |",
        f"| Open positions | {len(system.get('open_positions', []))} | {len(ava.get('open_positions', []))} |",
        f"| Lessons learned | — | {ava.get('lessons_week', '—')} |",
        "",
    ]
    lines += ["## Day by day", ""]
    day = monday
    while day <= friday:
        label = f"{WEEKDAYS[day.weekday()]} {day.isoformat()}"
        s_run = system.get("runs", {}).get(day.isoformat())
        a_run = ava.get("runs", {}).get(day.isoformat())
        if s_run is None and a_run is None:
            lines.append(f"- **{label}** — no run recorded (market closed, "
                         f"holiday, or no data).")
        else:
            s_txt = ("no run" if s_run is None else
                     f"system opened {s_run.get('trades_opened', 0)}, "
                     f"closed {s_run.get('trades_closed', 0)}, "
                     f"P&L {_money(s_run.get('realised_pnl_usd', 0.0), signed=True)} "
                     f"({s_run.get('status', '')})")
            a_txt = ("no run" if a_run is None else
                     f"Ava opened {a_run.get('trades_opened', 0)}, "
                     f"closed {a_run.get('trades_closed', 0)}, "
                     f"P&L {_money(a_run.get('realised_pnl_usd', 0.0), signed=True)} "
                     f"({a_run.get('status', '')})")
            lines.append(f"- **{label}** — {s_txt}; {a_txt}.")
        day += timedelta(days=1)
    lines.append("")
    for name, side in (("System", system), ("Ava", ava)):
        positions = side.get("open_positions", [])
        lines += [f"## Open positions — {name}", ""]
        if not positions:
            lines.append("None open at the end of the week.")
        else:
            for p in positions:
                lines.append(
                    f"- {p['symbol']} ({p['strategy']}): entered "
                    f"${p['entry_price']:,.2f} on {p['entry_date']}, "
                    f"{p['quantity']} shares, stop ${p['stop_loss']:,.2f}, "
                    f"target ${p['take_profit']:,.2f}, held {p['bars_held']} day(s).")
        lines.append("")
    lines += [
        "## What this does and does not prove",
        "",
        "One week of paper trades is practice, not proof — a good "
        "week does not promise next week, and a bad week does not "
        "condemn the rules. What the week does show is whether the "
        "rules are being followed (every trade with a stop, one "
        "lesson per close, no invented prices) and whether the two "
        "pots are behaving the same way. A compliance/legal review "
        "is still required before any real money is considered. "
        "Past performance does not guarantee future results.",
        "",
    ]
    return "\n".join(lines)


def generate_weekly_summary(week_end: date | None = None,
                            project_root: str | Path | None = None,
                            out_path: str | Path | None = None,
                            live_state_path: str | Path | None = None,
                            ava_state_path: str | Path | None = None,
                            evidence_file: str | Path | None = None,
                            lessons_file: str | Path | None = None) -> dict:
    """Build the weekly report and write it to validation/.

    ``live_state_path`` / ``ava_state_path`` / ``evidence_file`` /
    ``lessons_file`` default to the real project files; tests pass
    tmp paths. Returns a dict with the week bounds, the rendered
    text, the output path, and the side-by-side numbers, so a cron
    can deliver the numbers without re-reading the file.
    """
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    monday, friday = week_bounds(week_end)
    system_state = _load_json(Path(live_state_path) if live_state_path
                              else default_live_dir() / "state.json")
    ava_state = _load_json(Path(ava_state_path) if ava_state_path
                           else default_ava_daily_dir() / "state.json")
    evidence = _read_jsonl(Path(evidence_file) if evidence_file else evidence_path())
    lessons = _read_jsonl(Path(lessons_file) if lessons_file else lessons_path())
    system = _system_week(system_state, monday, friday)
    ava = _ava_week(ava_state, evidence, lessons, monday, friday)
    text = render_weekly_report(monday, friday, system, ava)
    out = Path(out_path) if out_path else (
        root / "validation" / f"weekly-paper-report-{friday.isoformat()}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return {
        "week_monday": monday.isoformat(),
        "week_friday": friday.isoformat(),
        "output_path": str(out),
        "text": text,
        "system": system,
        "ava": ava,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VaultTec weekly paper summary — system + Ava, "
                    "side by side. Paper only.")
    parser.add_argument("--week-end", default=None,
                        help="Friday of the week, YYYY-MM-DD; default: "
                             "most recent Friday on or before today")
    parser.add_argument("--out", default=None,
                        help="output markdown path (default: "
                             "validation/weekly-paper-report-<friday>.md)")
    args = parser.parse_args(argv)
    week_end = date.fromisoformat(args.week_end) if args.week_end else None
    result = generate_weekly_summary(week_end=week_end,
                                     out_path=args.out)
    sys_ = result["system"]
    ava = result["ava"]
    print(f"PAPER ONLY — weekly summary {result['week_monday']} to "
          f"{result['week_friday']}")
    print(f"System: opened {sys_.get('opened_week', '—')}, closed "
          f"{sys_.get('closed_week', '—')}, P&L "
          f"{_money(sys_.get('pnl_week_usd'), signed=True)}")
    print(f"Ava: opened {ava.get('opened_week', '—')}, closed "
          f"{ava.get('closed_week', '—')}, P&L "
          f"{_money(ava.get('pnl_week_usd'), signed=True)}, lessons "
          f"{ava.get('lessons_week', '—')}")
    print(f"Report: {result['output_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
