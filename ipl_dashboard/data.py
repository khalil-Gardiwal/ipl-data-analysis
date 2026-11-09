"""Read the source CSVs and build reusable, filterable cricket facts."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TEAM_NAMES = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Rising Pune Supergiant": "Rising Pune Supergiants",
}
BOWLER_DISMISSALS = {
    "bowled", "caught", "caught and bowled", "lbw", "stumped", "hit wicket",
}


def load_data(directory=DATA_DIR):
    matches = pd.read_csv(directory / "matches.csv", dtype={"season": str})
    balls = pd.read_csv(directory / "deliveries.csv")
    if matches["id"].duplicated().any() or balls.duplicated(
        ["match_id", "inning", "over", "ball"]
    ).any():
        raise ValueError("Duplicate match IDs or delivery keys in the input files.")
    if not balls["match_id"].isin(matches["id"]).all():
        raise ValueError("Some deliveries reference an unknown match ID.")

    matches["date"] = pd.to_datetime(matches["date"], errors="raise")
    matches["season_label"] = matches["season"]
    # One edition per source label, ordered by its first match.
    editions = matches.groupby("season")["date"].min().dt.year
    matches["season"] = matches["season"].map(editions)
    match_teams = ["team1", "team2", "winner", "toss_winner"]
    matches[match_teams] = matches[match_teams].replace(TEAM_NAMES)
    matches["city"] = matches["city"].replace({"Bangalore": "Bengaluru"}).fillna("Unknown city")
    delivery_teams = ["batting_team", "bowling_team"]
    balls[delivery_teams] = balls[delivery_teams].replace(TEAM_NAMES)

    # Attach the batting order at match grain. A toss-based fallback covers
    # future records without a first innings.
    first = balls.loc[balls["inning"].eq(1)].groupby("match_id")["batting_team"].first()
    other = matches["team1"].where(matches["team1"].ne(matches["toss_winner"]), matches["team2"])
    expected = matches["toss_winner"].where(matches["toss_decision"].eq("bat"), other)
    matches["batting_first"] = matches["id"].map(first).fillna(expected)
    return matches, balls


def build_facts(balls):
    regular = balls.loc[balls["inning"].isin([1, 2])].copy()
    extras = regular["extras_type"]
    regular["balls_faced"] = ~extras.eq("wides").fillna(False)
    regular["legal_balls"] = ~extras.isin(["wides", "noballs"])
    regular["fours"] = regular["batsman_runs"].eq(4)
    regular["sixes"] = regular["batsman_runs"].eq(6)
    regular["wickets"] = regular["is_wicket"].eq(1) & regular["dismissal_kind"].isin(BOWLER_DISMISSALS)
    regular["dots"] = regular["legal_balls"] & regular["total_runs"].eq(0)
    regular["conceded"] = regular["batsman_runs"] + regular["extra_runs"].where(
        extras.isin(["wides", "noballs"]), 0
    )
    innings = ["match_id", "inning"]
    batting = regular.groupby(innings + ["batting_team", "bowling_team", "batter"], as_index=False).agg(
        runs=("batsman_runs", "sum"), balls_faced=("balls_faced", "sum"),
        fours=("fours", "sum"), sixes=("sixes", "sum"),
    )
    bowling = regular.groupby(innings + ["bowling_team", "bowler"], as_index=False)[
        ["wickets", "legal_balls", "dots", "conceded"]
    ].sum()
    overs = regular.groupby(innings + ["batting_team", "over"], as_index=False)["total_runs"].sum()
    overs["over"] += 1
    return batting, bowling, overs
