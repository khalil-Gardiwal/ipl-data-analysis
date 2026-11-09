"""Analytics at match, team, innings and player grain."""

import pandas as pd

MIN_BAT_BALLS = 500
MIN_BOWL_BALLS = 500
MIN_DOT_BALLS = 101


def divide(numerator, denominator, scale=1):
    return numerator.div(denominator.where(denominator.ne(0))) * scale


def team_summary(matches, dimensions=()):
    columns = [*dimensions, "id", "winner", "result", "toss_winner"]
    teams = pd.concat([
        matches[columns + [side]].rename(columns={side: "team"})
        for side in ["team1", "team2"]
    ], ignore_index=True)
    won = teams["team"].eq(teams["winner"])
    teams = teams.assign(
        wins=won, runs_wins=won & teams["result"].eq("runs"),
        wicket_wins=won & teams["result"].eq("wickets"),
        tiebreak_wins=won & teams["result"].eq("tie"),
        no_result=teams["winner"].isna(),
        decided_toss=teams["team"].eq(teams["toss_winner"]) & teams["winner"].notna(),
        toss_and_match=won & teams["team"].eq(teams["toss_winner"]),
    )
    result = teams.groupby([*dimensions, "team"], as_index=False).agg(
        played=("id", "size"), wins=("wins", "sum"),
        wins_by_runs=("runs_wins", "sum"), wins_by_wickets=("wicket_wins", "sum"),
        tiebreak_wins=("tiebreak_wins", "sum"), no_result=("no_result", "sum"),
        decided_toss_wins=("decided_toss", "sum"), toss_and_match_wins=("toss_and_match", "sum"),
    )
    result["win_pct"] = divide(result["wins"], result["played"], 100)
    result["toss_conversion_pct"] = divide(result["toss_and_match_wins"], result["decided_toss_wins"], 100)
    return result.sort_values(["wins", "team"], ascending=[False, True])


def toss_summary(matches):
    decided = matches.dropna(subset=["winner"])
    return (
        decided.assign(toss_won_match=decided["winner"].eq(decided["toss_winner"]))
        .groupby("toss_decision", as_index=False)
        .agg(decided=("id", "size"), won=("toss_won_match", "sum"), win_pct=("toss_won_match", "mean"))
        .assign(win_pct=lambda x: x["win_pct"] * 100)
    )


def batting_summary(innings, dimensions=()):
    keys = [*dimensions, "batter"]
    match_runs = innings.groupby(keys + ["match_id"], as_index=False)["runs"].sum()
    variability = match_runs.groupby(keys)["runs"].std().rename("runs_std")
    result = innings.assign(fifty_plus=innings["runs"].ge(50)).groupby(keys).agg(
        runs=("runs", "sum"), balls_faced=("balls_faced", "sum"), fours=("fours", "sum"),
        sixes=("sixes", "sum"), matches_batted=("match_id", "nunique"),
        innings=("match_id", "size"), best=("runs", "max"), fifty_plus=("fifty_plus", "sum"),
    ).join(variability).reset_index()
    result["strike_rate"] = divide(result["runs"], result["balls_faced"], 100)
    result["runs_per_match"] = divide(result["runs"], result["matches_batted"])
    result["sixes_per_match"] = divide(result["sixes"], result["matches_batted"])
    return result


def bowling_summary(innings, dimensions=()):
    keys = [*dimensions, "bowler"]
    result = innings.assign(
        four_plus=innings["wickets"].ge(4), five_plus=innings["wickets"].ge(5),
    ).groupby(keys, as_index=False).agg(
        wickets=("wickets", "sum"), conceded=("conceded", "sum"), legal_balls=("legal_balls", "sum"),
        dots=("dots", "sum"), four_plus=("four_plus", "sum"), five_plus=("five_plus", "sum"),
        best=("wickets", "max"), matches_bowled=("match_id", "nunique"),
    )
    result["economy"] = divide(result["conceded"], result["legal_balls"], 6)
    result["average"] = divide(result["conceded"], result["wickets"])
    result["strike_rate"] = divide(result["legal_balls"], result["wickets"])
    result["dot_pct"] = divide(result["dots"], result["legal_balls"], 100)
    return result


def scoring_facts(overs, matches):
    """Use the notebook's winner-recorded, non-D/L scope for team scores."""
    eligible = matches.loc[matches["winner"].notna() & matches["method"].isna()]
    selected = overs.loc[overs["match_id"].isin(eligible["id"])]
    innings = (
        selected.groupby(["match_id", "inning", "batting_team"], as_index=False)["total_runs"].sum()
        .merge(eligible[["id", "season", "date", "venue"]], left_on="match_id", right_on="id",
               validate="many_to_one")
        .drop(columns="id")
    )
    return selected, innings
