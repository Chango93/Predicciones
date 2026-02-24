#!/usr/bin/env python3
"""
Build (or rebuild) data/liga_mx.db from data/inputs/Stats_liga_mx.json (TSV).

Usage:
    python scripts/build_db.py
"""

import csv
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TSV_PATH = REPO_ROOT / "data" / "inputs" / "Stats_liga_mx.json"
DB_PATH  = REPO_ROOT / "data" / "liga_mx.db"


def to_iso(date_str: str) -> str:
    """Convert DD/MM/YYYY → YYYY-MM-DD for chronological sorting."""
    dd, mm, yyyy = date_str.split("/")
    return f"{yyyy}-{mm}-{dd}"


def calc_result(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "H"
    elif away_goals > home_goals:
        return "A"
    return "D"


def build(tsv_path: Path = TSV_PATH, db_path: Path = DB_PATH) -> int:
    with open(tsv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS matches;
        CREATE TABLE matches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament  TEXT    NOT NULL,
            matchday    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            date_iso    TEXT    NOT NULL,
            home_team   TEXT    NOT NULL,
            away_team   TEXT    NOT NULL,
            home_goals  INTEGER NOT NULL,
            away_goals  INTEGER NOT NULL,
            result      TEXT    NOT NULL
        );
        CREATE INDEX idx_home  ON matches(home_team);
        CREATE INDEX idx_away  ON matches(away_team);
        CREATE INDEX idx_date  ON matches(date_iso);
        CREATE INDEX idx_tourn ON matches(tournament);
    """)

    cur.executemany(
        """INSERT INTO matches
               (tournament, matchday, date, date_iso,
                home_team, away_team, home_goals, away_goals, result)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [
            (
                r["tournament"],
                r["matchday"],
                r["date"],
                to_iso(r["date"]),
                r["home_team"],
                r["away_team"],
                int(r["home_goals"]),
                int(r["away_goals"]),
                calc_result(int(r["home_goals"]), int(r["away_goals"])),
            )
            for r in rows
        ],
    )

    con.commit()
    count = cur.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    con.close()
    return count


if __name__ == "__main__":
    n = build()
    print(f"liga_mx.db built — {n} matches loaded from {TSV_PATH.name}")
