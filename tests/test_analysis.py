"""Regression checks for the data reconciliation and filter grain."""

import unittest

from ipl_dashboard.analysis import batting_summary, bowling_summary, scoring_facts, team_summary, toss_summary
from ipl_dashboard.data import build_facts, load_data


class IPLDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matches, cls.deliveries = load_data()
        cls.batting, cls.bowling, cls.overs = build_facts(cls.deliveries)

    def test_match_grain_and_toss(self):
        matches = self.matches
        self.assertEqual((len(matches), matches["season"].nunique(), matches["venue"].nunique()), (1095, 17, 58))
        teams = team_summary(matches).set_index("team")
        self.assertEqual(len(teams), 15)
        self.assertEqual(teams["played"].sum(), 2 * len(matches))
        self.assertEqual(teams.loc["Mumbai Indians", "wins"], 144)
        self.assertEqual(teams["wins"].sum(), 1090)
        self.assertEqual(matches["super_over"].eq("Y").sum(), 14)
        self.assertEqual(matches["method"].eq("D/L").sum(), 21)
        toss = toss_summary(matches).set_index("toss_decision")
        self.assertEqual(tuple(toss.loc["bat", ["won", "decided"]]), (177, 390))
        self.assertEqual(tuple(toss.loc["field", ["won", "decided"]]), (377, 700))

    def test_player_rules(self):
        batting = batting_summary(self.batting).set_index("batter")
        self.assertEqual(batting.loc["V Kohli", "runs"], 8004)
        self.assertAlmostEqual(batting.loc["V Kohli", "strike_rate"], 100 * 8004 / 6065)
        self.assertEqual(batting.loc["CH Gayle", "best"], 175)
        self.assertEqual(batting.loc["CH Gayle", "sixes"], 357)
        bowling = bowling_summary(self.bowling).set_index("bowler")
        self.assertEqual(bowling.loc["YS Chahal", "wickets"], 205)
        self.assertEqual(bowling.loc["SL Malinga", "conceded"], 3364)
        self.assertAlmostEqual(bowling.loc["YS Chahal", "dot_pct"], 100 * 1194 / 3521)
        self.assertEqual(bowling.loc["A Kumble", "four_plus"], 3)
        self.assertEqual(bowling.loc["A Kumble", "five_plus"], 1)

    def test_team_scores_and_filtering(self):
        _, innings = scoring_facts(self.overs, self.matches)
        self.assertEqual((len(innings), innings["total_runs"].max(), innings["total_runs"].min()), (2138, 287, 49))
        scoped = self.matches.loc[self.matches["season"].eq(2024) & self.matches["venue"].eq("Eden Gardens, Kolkata")]
        self.assertEqual(len(scoped), 7)
        facts = self.batting.loc[self.batting["match_id"].isin(scoped["id"])]
        kkr = facts.loc[facts["batting_team"].eq("Kolkata Knight Riders")]
        self.assertEqual(batting_summary(kkr).set_index("batter").loc["SP Narine", "runs"], 213)
        self.assertTrue(team_summary(scoped.iloc[:0]).empty)
