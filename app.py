"""Streamlit entry point. Run with python -m streamlit run app.py."""

from pathlib import Path

import streamlit as st

from ipl_dashboard import data
from ipl_dashboard.pages import batting, bowling, matches_page, overview, teams, venues

st.set_page_config(page_title="IPL Analytics", page_icon="🏏", layout="wide")
st.html(Path(__file__).parent / "ipl_dashboard" / "style.css")


@st.cache_data(show_spinner="Preparing IPL match and innings data…")
def cached_data(source_versions):
    matches, balls = data.load_data()
    return matches, data.build_facts(balls)


try:
    versions = tuple((data.DATA_DIR / name).stat().st_mtime_ns for name in ("matches.csv", "deliveries.csv"))
    all_matches, (all_batting, all_bowling, all_overs) = cached_data(versions)
except (OSError, ValueError, KeyError) as error:
    st.error(f"Could not prepare the IPL data. Check the two files in the data folder. {error}")
    st.stop()

st.sidebar.html('<div class="brand">IPL / DATA ANALYTICS</div>')


def overview_page():
    overview(matches, bat, bowl)


def team_page():
    teams(matches, overs)


def batting_page():
    batting(matches, bat, overs)


def bowling_page():
    bowling(matches, bowl)


def match_page():
    matches_page(matches)


def venue_page():
    venues(matches, overs)


page = st.navigation([
    st.Page(overview_page, title="IPL Overview", icon=":material/space_dashboard:", default=True),
    st.Page(team_page, title="Team Performance", icon=":material/groups:", url_path="teams"),
    st.Page(batting_page, title="Batting Analysis", icon=":material/sports_cricket:", url_path="batting"),
    st.Page(bowling_page, title="Bowling Analysis", icon=":material/adjust:", url_path="bowling"),
    st.Page(match_page, title="Match Insights", icon=":material/insights:", url_path="matches"),
    st.Page(venue_page, title="Venue & Season", icon=":material/stadium:", url_path="venues"),
])

st.sidebar.divider()
st.sidebar.markdown("**Match filters**")
seasons = st.sidebar.multiselect("Seasons", sorted(all_matches["season"].unique()),
                                 placeholder="All seasons", help="Leave empty to include every season.")
grounds = st.sidebar.multiselect("Venues", sorted(all_matches["venue"].unique()),
                                 placeholder="All venues", help="Venue names follow the source file.")
matches = all_matches
if seasons:
    matches = matches.loc[matches["season"].isin(seasons)]
if grounds:
    matches = matches.loc[matches["venue"].isin(grounds)]
st.sidebar.caption(f"{len(matches):,} of {len(all_matches):,} match records in scope")
st.sidebar.caption("Indian Premier League · 2008–2024")

bat, bowl, overs = (frame.loc[frame["match_id"].isin(matches["id"])] for frame in
                    (all_batting, all_bowling, all_overs))
page.run()
