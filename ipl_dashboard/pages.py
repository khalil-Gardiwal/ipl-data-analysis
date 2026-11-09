"""The six dashboard views."""

import pandas as pd
import streamlit as st

from .analysis import (
    MIN_BAT_BALLS, MIN_BOWL_BALLS, MIN_DOT_BALLS, batting_summary, bowling_summary,
    divide, scoring_facts, team_summary, toss_summary,
)
from .ui import chart, hero, label, ranking, table


def counts(frame, *keys):
    return frame.groupby(list(keys), as_index=False).size().rename(columns={"size": "matches"})


def metric_row(items):
    for column, (title, value, detail) in zip(st.columns(len(items)), items):
        column.metric(title, value, help=detail)


def overview(matches, bat, bowl):
    hero("01  /  LEAGUE OVERVIEW", "IPL Analytics Dashboard",
         "Explore 17 seasons of Indian Premier League cricket, from league-wide trends to individual innings.")
    teams = team_summary(matches)
    metric_row([
        ("Match records", f"{len(matches):,}", "Includes matches with no result."),
        ("Seasons", matches["season"].nunique(), "Editions represented in the current filters."),
        ("Franchises", len(teams), "Historical franchise name variants are combined."),
        ("Venue labels", matches["venue"].nunique(), "Source venue names are retained."),
    ])
    left, right = st.columns([1.15, 1])
    with left:
        chart(counts(matches, "season"), "Matches across seasons", "season", "matches")
    with right:
        ranking(teams, "team", "wins", "Franchises by recorded wins", limit=8)
    if not matches.empty:
        st.subheader("In this selection")
        insights = [f"**{teams.iloc[0]['team']}** lead on recorded wins with **{teams.iloc[0]['wins']:,}**."
                    ] if teams["wins"].sum() else []
        for frame, name, value, noun in [
            (batting_summary(bat), "batter", "runs", "runs"),
            (bowling_summary(bowl), "bowler", "wickets", "credited wickets"),
        ]:
            if not frame.empty and frame[value].max() > 0:
                leader = frame.sort_values([value, name], ascending=[False, True]).iloc[0]
                insights.append(f"**{leader[name]}** leads with **{leader[value]:,} {noun}**.")
        if insights:
            st.markdown("\n".join(f"- {item}" for item in insights))
    st.caption("Use the sidebar to filter match scope across all six pages. Player statistics cover regulation innings.")


def teams(matches, overs):
    hero("02  /  FRANCHISES", "Team Performance",
         "Compare franchise records, toss conversion and scoring across seasons.")
    overall = team_summary(matches)
    chosen = st.multiselect("Teams to compare", sorted(overall["team"]),
                            placeholder="All teams", key="compare_teams")
    summary = overall.loc[overall["team"].isin(chosen)] if chosen else overall
    selected = summary["team"]
    season = team_summary(matches, ("season",))
    season = season.loc[season["team"].isin(selected)]
    overview_tab, season_tab, scoring_tab = st.tabs(["Overall record", "Season comparison", "Team scoring"])
    with overview_tab:
        metric = st.selectbox("Rank teams by", ["wins", "win_pct", "played", "toss_conversion_pct"],
                              format_func=label)
        ranking(summary, "team", metric, "Franchise rankings", limit=15)
        st.caption("Win rate divides wins by all match appearances. Toss conversion uses toss wins in matches with a recorded winner.")
        table(summary, "Team records", "team-records")
    with season_tab:
        trend = st.selectbox("Season metric", ["wins", "win_pct", "played"], format_func=label)
        focus = list(chosen) or list(summary.head(5)["team"])
        chart(season.loc[season["team"].isin(focus)], "Selected franchises by season",
              "season", trend, kind="line", group="team", percent=trend == "win_pct")
        st.caption("With no team selected, the chart displays the five franchises with the most wins in scope.")
        best = season.loc[season["win_pct"].eq(season.groupby("season")["win_pct"].transform("max"))]
        table(best.sort_values("season"), "Highest win rates by season", "season-leaders")
        table(season.sort_values(["season", "wins"], ascending=[True, False]), "Season records", "team-seasons")
    with scoring_tab:
        _, innings = scoring_facts(overs, matches)
        innings = innings.loc[innings["batting_team"].isin(selected)]
        scoring = innings.assign(innings_200_plus=innings["total_runs"].ge(200)).groupby(
            ["season", "batting_team"], as_index=False
        ).agg(total_runs=("total_runs", "sum"), average_score=("total_runs", "mean"),
              score_std=("total_runs", "std"), innings_200_plus=("innings_200_plus", "sum"),
              innings=("total_runs", "size"))
        stat = st.selectbox("Scoring metric", ["total_runs", "average_score", "innings_200_plus"], format_func=label)
        focus = list(chosen) or list(summary.head(5)["team"])
        chart(scoring.loc[scoring["batting_team"].isin(focus)], "Franchise scoring by season",
              "season", stat, kind="line", group="batting_team")
        st.caption("Team scoring uses regulation innings from matches with a recorded winner and no D/L flag. Standard deviation measures score spread in runs.")
        table(scoring, "Team scoring by season", "team-scoring")


BAT_METRICS = {
    "runs": ("Runs", None, 0, False),
    "fours": ("Fours", None, 0, False),
    "sixes": ("Sixes", None, 0, False),
    "strike_rate": ("Runs per 100 balls faced", "balls_faced", MIN_BAT_BALLS, False),
    "best": ("Highest innings score (runs)", None, 0, False),
    "fifty_plus": ("Innings with 50+ runs", None, 0, False),
    "runs_per_match": ("Runs per match batted", "matches_batted", 11, False),
    "sixes_per_match": ("Sixes per match batted", "matches_batted", 11, False),
    "runs_std": ("Standard deviation of match runs", "matches_batted", 50, True),
    "balls_faced": ("Balls faced", None, 0, False),
    "innings": ("Innings batted", None, 0, False),
}
BOWL_METRICS = {
    "wickets": ("Credited wickets", None, 0, False),
    "economy": ("Runs per six legal balls", "legal_balls", MIN_BOWL_BALLS, True),
    "average": ("Runs conceded per wicket", "legal_balls", MIN_BOWL_BALLS, True),
    "strike_rate": ("Legal balls per wicket", "legal_balls", MIN_BOWL_BALLS, True),
    "dots": ("Legal balls with zero team runs", None, 0, False),
    "dot_pct": ("Dot balls (% of legal balls)", "legal_balls", MIN_DOT_BALLS, False),
    "four_plus": ("Innings with 4+ wickets", None, 0, False),
    "five_plus": ("Innings with 5+ wickets", None, 0, False),
    "best": ("Most wickets in an innings", None, 0, False),
    "legal_balls": ("Legal balls", None, 0, False),
    "conceded": ("Runs charged to the bowler", None, 0, False),
}


def player_scope(frame, team, player):
    left, right = st.columns(2)
    selected_teams = left.multiselect(label(team), sorted(frame[team].unique()),
                                      placeholder="All teams", key=f"{player}_teams")
    if selected_teams:
        frame = frame.loc[frame[team].isin(selected_teams)]
    selected_players = right.multiselect(f"{label(player)} comparison", sorted(frame[player].unique()),
                                         placeholder="All players", key=f"{player}_players")
    if selected_players:
        frame = frame.loc[frame[player].isin(selected_players)]
    return frame, selected_players, selected_teams


def player_board(summary, player, metrics):
    metric = st.selectbox("Leaderboard metric", list(metrics), format_func=lambda key: metrics[key][0])
    unit, qualifier, minimum, ascending = metrics[metric]
    ranked = summary if qualifier is None else summary.loc[summary[qualifier].ge(minimum)]
    ranked = ranked.dropna(subset=[metric]).sort_values([metric, player], ascending=[ascending, True])
    if qualifier:
        st.caption(f"Qualification in the current selection · At least {minimum} {label(qualifier).lower()}.")
    ranking(ranked, player, metric, f"Leaders by {unit.lower()}", ascending=ascending, unit=unit)
    table(ranked, "Qualified player statistics" if qualifier else "Player statistics", f"{player}-leaderboard")


def player_trend(frame, matches, selected, player, summarize, metric, units):
    if not selected:
        st.info("Select players in the comparison filter to plot their season records.")
        return
    seasons = matches.set_index("id")["season"]
    seasonal = summarize(frame.assign(season=frame["match_id"].map(seasons)), ("season",))
    chart(seasonal, "Selected players by season", "season", metric, kind="line", group=player,
          labels={metric: units})
    table(seasonal, "Player records by season", f"{player}-seasons")


def batting(matches, frame, overs):
    hero("03  /  AT THE CREASE", "Batting Analysis",
         "Explore run scoring, boundary hitting, individual innings and team scoring patterns.")
    frame, selected, chosen_teams = player_scope(frame, "batting_team", "batter")
    opposition = st.multiselect("Opposition bowling team", sorted(frame["bowling_team"].unique()),
                                placeholder="All opponents")
    if opposition:
        frame = frame.loc[frame["bowling_team"].isin(opposition)]
    summary = batting_summary(frame)
    leaders, individual, team_scores = st.tabs(["Player leaderboard", "Individual innings", "Team innings & overs"])
    with leaders:
        st.caption("Strike rate includes no-ball deliveries faced and excludes wides. Matches batted require a recorded striker appearance.")
        player_board(summary, "batter", BAT_METRICS)
        player_trend(frame, matches, selected, "batter", batting_summary, "runs", "Runs")
        if not frame.empty:
            boundaries = pd.DataFrame({
                "type": ["Fours", "Sixes"], "hits": [frame["fours"].sum(), frame["sixes"].sum()],
            })
            table(boundaries.assign(runs=boundaries["hits"] * [4, 6]), "Boundary contribution", "boundaries")
        with st.expander("Runs per match · 20-match qualification"):
            eligible = summary.loc[summary["matches_batted"].ge(20)]
            table(eligible.sort_values("runs_per_match", ascending=False), "20-match batting records", "batting-20-match")
    with individual:
        innings = frame.merge(matches[["id", "season", "date", "venue"]], left_on="match_id", right_on="id",
                              validate="many_to_one").drop(columns="id")
        innings["strike_rate"] = divide(innings["runs"], innings["balls_faced"], 100)
        table(innings.sort_values(["runs", "balls_faced"], ascending=[False, True]),
              "Highest individual innings", "individual-innings")
    with team_scores:
        st.caption("Team scores use the season, venue and batting-team filters. Player and opposition selections apply to the individual views.")
        scoring_view(matches, overs, chosen_teams)


def scoring_view(matches, overs, chosen_teams):
    overs, innings = scoring_facts(overs, matches)
    if chosen_teams:
        overs = overs.loc[overs["batting_team"].isin(chosen_teams)]
        innings = innings.loc[innings["batting_team"].isin(chosen_teams)]
    view = st.selectbox("Scoring view", ["Innings totals", "Over and phase scoring"])
    st.caption("Only regulation innings in matches with a recorded winner and no D/L flag are included.")
    if view == "Innings totals":
        by_order = innings.groupby("inning", as_index=False).agg(average_runs=("total_runs", "mean"))
        by_order["inning"] = by_order["inning"].map({1: "First innings", 2: "Second innings"})
        chart(by_order, "Average score by innings order", "inning", "average_runs")
        by_team = innings.assign(innings_200_plus=innings["total_runs"].ge(200)).groupby(
            "batting_team", as_index=False
        ).agg(innings=("total_runs", "size"), average_runs=("total_runs", "mean"),
              score_std=("total_runs", "std"), innings_200_plus=("innings_200_plus", "sum"))
        table(by_team.sort_values("average_runs", ascending=False), "Team scoring and consistency", "innings-team")
        order = st.radio("Innings order", ["Highest scores", "Lowest scores"], horizontal=True)
        table(innings.sort_values("total_runs", ascending=order == "Lowest scores"),
              "Team innings scores", "innings-scores")
    else:
        per_over = overs.groupby("over", as_index=False)["total_runs"].sum()
        chart(per_over, "Total runs by over number", "over", "total_runs")
        phases = overs.loc[overs["over"].le(6) | overs["over"].ge(16)].copy()
        phases["phase"] = phases["over"].le(6).map({True: "Overs 1–6", False: "Overs 16–20"})
        phases = phases.groupby(["match_id", "inning", "batting_team", "phase"], as_index=False)["total_runs"].sum()
        per_team = phases.groupby(["batting_team", "phase"], as_index=False).agg(
            average_runs=("total_runs", "mean"), innings_reaching_phase=("match_id", "size")
        )
        st.caption("Phase averages include innings that reached the phase, including partial phases. These are fixed over bands.")
        table(per_team, "Average runs per phase", "phase-scoring")
        table(overs.sort_values("total_runs", ascending=False), "Highest-scoring overs", "scoring-overs")


def bowling(matches, frame):
    hero("04  /  WITH THE BALL", "Bowling Analysis",
         "Compare wicket-taking, run control, dot balls and standout spells.")
    frame, selected, _ = player_scope(frame, "bowling_team", "bowler")
    leaders, spells = st.tabs(["Bowler leaderboard", "Bowling figures"])
    with leaders:
        st.caption("Economy, average and strike rate require 500 legal balls for rankings. Dot-ball percentage requires more than 100 legal balls.")
        player_board(bowling_summary(frame), "bowler", BOWL_METRICS)
        player_trend(frame, matches, selected, "bowler", bowling_summary, "wickets", "Credited wickets")
    with spells:
        st.caption("Four-plus includes five-plus hauls. A dot ball is a legal delivery with zero team runs.")
        figures = frame.merge(matches[["id", "season", "date", "venue"]], left_on="match_id", right_on="id",
                               validate="many_to_one").drop(columns="id")
        table(figures.sort_values(["wickets", "conceded", "bowler"], ascending=[False, True, True]),
              "Bowling figures by innings", "bowling-figures")


def matches_page(matches):
    hero("05  /  MATCH DYNAMICS", "Match Insights",
         "See how matches were decided, what captains chose at the toss and where special conditions applied.")
    chosen = st.multiselect("Participating teams", sorted(team_summary(matches)["team"]),
                            placeholder="All teams", key="match_teams")
    if chosen:
        matches = matches.loc[matches["team1"].isin(chosen) | matches["team2"].isin(chosen)]
    decided = matches.dropna(subset=["winner"])
    toss = toss_summary(matches)
    toss_wins = int(toss["won"].sum())
    converted = f"{toss_wins / len(decided):.1%}" if len(decided) else "—"
    super_overs = matches["super_over"].eq("Y")
    revised = matches["method"].eq("D/L").fillna(False)
    metric_row([
        ("Toss winners also won", converted, f"{toss_wins:,} of {len(decided):,} matches with a recorded winner."),
        ("Super Over matches", int(super_overs.sum()), "Match records with the Super Over flag."),
        ("D/L-flagged matches", int(revised.sum()), "Source match method is recorded as D/L."),
    ])
    toss_tab, outcome_tab, special_tab = st.tabs(["Toss & batting order", "Results & margins", "Special conditions"])
    with toss_tab:
        chart(counts(matches, "season", "toss_decision"), "Toss decisions by season", "season",
              "matches", group="toss_decision")
        table(toss, "Toss conversion by decision", "toss-conversion")
        regulation = decided.loc[~decided["super_over"].eq("Y") & decided["result"].isin(["runs", "wickets"])]
        order = regulation["winner"].eq(regulation["batting_first"]).map({True: "Batting first", False: "Chasing"})
        chart(counts(regulation.assign(winning_side=order), "winning_side"), "Wins by batting order",
              "winning_side", "matches")
        st.caption("Batting order comes from innings 1. The split includes D/L results with a runs or wickets outcome. Toss comparisons are descriptive.")
    with outcome_tab:
        chart(counts(matches, "season", "result"), "Result types by season", "season", "matches", group="result")
        results = counts(matches, "result")
        results["share_pct"] = results["matches"] * 100 / max(len(matches), 1)
        table(results, "Result distribution", "result-distribution")
        margins = matches.loc[matches["result"].isin(["runs", "wickets"])].copy()
        margins["close"] = (
            (margins["result"].eq("runs") & margins["result_margin"].le(5))
            | (margins["result"].eq("wickets") & margins["result_margin"].le(2))
        )
        margin_stats = margins.groupby("result", as_index=False).agg(
            matches=("id", "size"), close_matches=("close", "sum"), mean_margin=("result_margin", "mean"),
            median_margin=("result_margin", "median"), max_margin=("result_margin", "max"),
        )
        st.caption("Close wins are by five runs or fewer, or two wickets or fewer. Margins use the units in the result column.")
        table(margin_stats, "Win margins", "win-margins")
        table(counts(matches, "season", "match_type"), "Match stages by season", "match-stages")
        awards = matches.dropna(subset=["player_of_match"])
        table(counts(awards, "player_of_match").sort_values("matches", ascending=False),
              "Player-of-match awards", "match-awards")
    with special_tab:
        flags = pd.concat([
            matches.loc[super_overs].assign(condition="Super Over"),
            matches.loc[revised].assign(condition="D/L"),
        ])
        chart(counts(flags, "season", "condition"), "Special conditions by season", "season", "matches", group="condition")
        columns = ["id", "date", "venue", "team1", "team2", "winner", "result", "target_runs", "target_overs", "condition"]
        table(flags[columns].sort_values("date"), "Special-condition match records", "special-matches")
        st.caption("Targets and over limits are source fields. The method flag identifies D/L matches in this file.")


def venues(matches, overs):
    hero("06  /  GROUNDS & EDITIONS", "Venue & Season Analysis",
         "Explore where the IPL has played, how venue use changed and how teams performed at each ground.")
    locations, seasons, ground_records = st.tabs(["Venues & cities", "Season trends", "Ground records"])
    with locations:
        venue = matches.groupby("venue", as_index=False).agg(matches=("id", "size"), seasons=("season", "nunique"))
        venue["match_share_pct"] = venue["matches"] * 100 / max(len(matches), 1)
        city = counts(matches, "city")
        left, right = st.columns(2)
        with left:
            ranking(venue, "venue", "matches", "Most-used venue labels")
        with right:
            ranking(city, "city", "matches", "Matches by city")
        st.caption("Venue names follow the source labels. Bengaluru combines both city spellings. Missing cities appear as Unknown city.")
        table(venue.sort_values("matches", ascending=False), "Venue usage and match share", "venue-usage")
        table(city.sort_values("matches", ascending=False), "City match counts", "city-matches")
    with seasons:
        chart(counts(matches, "season"), "Match volume by season", "season", "matches")
        venue_seasons = counts(matches, "season", "venue")
        leaders = venue_seasons.loc[venue_seasons["matches"].eq(venue_seasons.groupby("season")["matches"].transform("max"))]
        table(leaders, "Most-used venue labels by season", "season-venues")
        place = st.selectbox("Season location breakdown", ["city", "venue"], format_func=label)
        table(counts(matches, "season", place), f"Matches by {place} and season", f"season-{place}-counts")
        _, innings = scoring_facts(overs, matches)
        trend = innings.groupby("season", as_index=False).agg(
            average_score=("total_runs", "mean"), highest_score=("total_runs", "max")
        ).melt(id_vars="season", var_name="statistic", value_name="runs")
        trend["statistic"] = trend["statistic"].map(label)
        chart(trend, "Average and highest team innings scores", "season", "runs", kind="line", group="statistic")
        st.caption("Scoring includes regulation innings in matches with a recorded winner and no D/L flag.")
    with ground_records:
        ground = st.selectbox("Ground to inspect", ["All selected venues", *sorted(matches["venue"].unique())])
        scope = matches if ground == "All selected venues" else matches.loc[matches["venue"].eq(ground)]
        table(team_summary(scope, ("venue",)), "Franchise records by ground", "venue-team-records")
        margins = scope.loc[scope["result"].isin(["runs", "wickets"])]
        margins = margins.groupby(["venue", "result"], as_index=False).agg(
            matches=("id", "size"), average_margin=("result_margin", "mean"))
        table(margins, "Average winning margins by ground and result unit", "venue-margins")
        table(counts(scope.loc[scope["match_type"].eq("Final")], "venue"), "Finals hosted", "finals-by-venue")
