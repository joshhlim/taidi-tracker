"""Reusable UI components for Taidi card game tracker."""

import streamlit as st
import pandas as pd
from datetime import datetime

from config import DATETIME_DISPLAY_FORMAT


def highlight_total_col(s):
    """Style function to highlight the Total column."""
    return [
        'background-color: #FFD700; color: black; font-weight: bold' 
        if col == 'Total' else ''
        for col in s.index
    ]


def display_summary_table(tracker):
    """Display the earnings summary table with Total column highlighted."""
    summary_df = tracker.get_summary()
    st.dataframe(
        summary_df.style.apply(highlight_total_col, axis=1).format("${:.2f}"),
        use_container_width=True
    )


def display_archived_game(entry: dict, on_delete_callback=None):
    """Display a single archived game in an expander with delete option."""
    title = (
        f"🗂️ {entry['created_at']} — "
        f"{len(entry.get('players', []))} players, "
        f"{entry.get('rounds_played', 0)} rounds @ ${entry.get('card_value', 0):.2f}/card"
    )
    
    with st.expander(title, expanded=False):
        totals = pd.Series(entry["final_totals"], name="Total").sort_values(ascending=False)
        st.dataframe(
            totals.to_frame().style.format("${:.2f}"),
            use_container_width=True
        )
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            csv_df = totals.reset_index()
            csv_df.columns = ["Player", "Total"]
            st.download_button(
                "Download CSV",
                data=csv_df.to_csv(index=False),
                file_name=f"taidi_final_standings_{entry['created_at'].replace(' ','_').replace(':','-')}.csv",
                mime="text/csv",
                key=f"download_{entry['archive_id']}"
            )
        
        with col2:
            if st.button("🗑️ Delete", key=f"delete_{entry['archive_id']}", type="secondary", use_container_width=True):
                if on_delete_callback:
                    on_delete_callback(entry['archive_id'])


def display_player_profile(player_name: str, hist_df: pd.DataFrame):
    """Display player profile with stats and trend chart."""
    games = len(hist_df)
    total = float(hist_df["Net"].sum()) if games else 0.0
    wins = int((hist_df["Net"] > 0).sum())
    losses = int((hist_df["Net"] < 0).sum())
    ties = int((hist_df["Net"] == 0).sum())
    winrate = (wins / games * 100.0) if games else 0.0
    
    # Metrics row
    c1, c2, c3 = st.columns(3)
    c1.metric("Overall Profit / Loss", f"${total:,.2f}")
    c2.metric("Overall Win Rate", f"{winrate:.1f}%")
    c3.metric("Games Played", f"{games}")
    
    # Trend chart
    st.markdown("### Profit/Loss Trend")
    if hist_df.empty:
        st.caption("No archived games for this player yet.")
    else:
        trend = hist_df.copy()
        trend["When"] = pd.to_datetime(trend["When"], errors="coerce")
        trend = trend.dropna(subset=["When"]).sort_values("When")
        trend["Cumulative Net"] = trend["Net"].cumsum()
        
        with st.expander("Show per-game results", expanded=False):
            st.dataframe(
                trend.assign(
                    **{
                        "When": trend["When"].dt.strftime(DATETIME_DISPLAY_FORMAT),
                        "Card Value": trend["Card Value"].map(lambda x: f"${x:,.2f}"),
                        "Net": trend["Net"].map(lambda x: f"${x:,.2f}"),
                        "Cumulative Net": trend["Cumulative Net"].map(lambda x: f"${x:,.2f}"),
                    }
                )[["When", "Rounds", "Card Value", "Net", "Cumulative Net"]],
                use_container_width=True
            )
        
        st.line_chart(
            data=trend.set_index("When")[["Cumulative Net"]],
            use_container_width=True
        )


def format_players_table(df: pd.DataFrame):
    """Format and display the players table."""
    if df.empty:
        st.caption("No players in registry.")
    else:
        st.dataframe(
            df.style.format({"Total": "${:,.2f}", "Avg/Game": "${:,.2f}"}),
            use_container_width=True
        )