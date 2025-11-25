"""Main Streamlit application for Taidi card game tracker."""

import streamlit as st
from uuid import uuid4
from datetime import datetime

import models
import auth
from tracker import CardGameTracker
from config import APP_TITLE, DEFAULT_CARD_VALUE, DATETIME_FORMAT, ENABLE_PASSWORD_PROTECTION
import ui_components as ui


# ============== Page Config ==============
st.set_page_config(page_title="Taidi Tracker", page_icon="🃏", layout="wide")

# ============== Authentication Check ==============
if ENABLE_PASSWORD_PROTECTION and not auth.check_authentication():
    st.title(APP_TITLE)
    auth.login_form()
    st.stop()  # Stop execution if not authenticated

# ============== Main App (only runs if authenticated) ==============
st.title(APP_TITLE)

# ============== Query Params Helpers ==============
def get_query_params():
    """Get query parameters (compatible with different Streamlit versions)."""
    try:
        return dict(st.query_params)
    except Exception:
        return dict(st.experimental_get_query_params())


def set_query_param_game_id(game_id: str):
    """Set game_id query parameter (compatible with different Streamlit versions)."""
    try:
        st.query_params["game_id"] = game_id
    except Exception:
        st.experimental_set_query_params(game_id=game_id)


# ============== Session State Initialization ==============
def init_session_state():
    """Initialize session state variables."""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        
        # Check for game_id in URL
        params = get_query_params()
        game_id = params.get("game_id", [None])[0] if isinstance(params.get("game_id"), list) else params.get("game_id")
        
        if game_id:
            # Try to load existing game
            snapshot = models.load_game_snapshot(game_id)
            if snapshot:
                tracker, round_num, card_value = models.restore_tracker_from_snapshot(snapshot)
                st.session_state.tracker = tracker
                st.session_state.round_num = round_num
                st.session_state.card_value = card_value
                st.session_state.game_id = game_id
                return
        
        # No existing game - initialize empty
        st.session_state.tracker = None
        st.session_state.round_num = 1
        st.session_state.card_value = DEFAULT_CARD_VALUE
        st.session_state.game_id = None


init_session_state()


# ============== Sidebar: Game Setup ==============
with st.sidebar:
    st.header("⚙️ Game Setup")
    
    # Show logout button if authenticated
    auth.show_logout_button()
    
    # Get all registered players
    all_players = models.get_all_players()
    player_names = sorted([p["name"] for p in all_players.values()])
    
    if not player_names:
        st.warning("⚠️ No players registered. Go to **Player Management** tab to add players.")
    
    selected_players = st.multiselect(
        "Select players for this game",
        options=player_names,
        default=st.session_state.tracker.players if st.session_state.tracker else []
    )
    
    card_val_input = st.number_input(
        "Value per card ($)",
        min_value=0.01,
        value=st.session_state.card_value,
        step=0.01,
        format="%.2f"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start / Update Game", type="primary", use_container_width=True):
            if not selected_players:
                st.error("Select at least one player!")
            else:
                # Create new game or update existing
                st.session_state.tracker = CardGameTracker(selected_players)
                st.session_state.round_num = 1
                st.session_state.card_value = card_val_input
                st.session_state.game_id = str(uuid4())
                st.session_state.pop("archived_this_game", None)
                
                # Save to database
                models.save_game_snapshot(
                    st.session_state.game_id,
                    st.session_state.tracker,
                    st.session_state.round_num,
                    st.session_state.card_value
                )
                
                # Update URL
                set_query_param_game_id(st.session_state.game_id)
                st.success("Game started!")
                st.rerun()
    
    with col2:
        if st.button("Reset Game", type="secondary", use_container_width=True):
            # Delete from database if exists
            if st.session_state.game_id:
                models.delete_game_snapshot(st.session_state.game_id)
            
            # Clear session state
            st.session_state.tracker = None
            st.session_state.round_num = 1
            st.session_state.card_value = DEFAULT_CARD_VALUE
            st.session_state.game_id = None
            st.session_state.pop("archived_this_game", None)
            
            # Clear URL
            try:
                st.query_params.clear()
            except Exception:
                st.experimental_set_query_params()
            
            st.rerun()


# ============== Main Content: Tabs ==============
tab1, tab2, tab3, tab4 = st.tabs([
    "🎮 Current Game",
    "📚 History Log",
    "👥 Players",
    "⚙️ Player Management"
])

# ====== Tab 1: Current Game ======
with tab1:
    tracker = st.session_state.tracker
    
    if tracker is None:
        st.info("👈 Use the sidebar to select players and start a game!")
    else:
        # Round input section
        st.subheader(f"Round {st.session_state.round_num}")
        
        # Card counts input
        st.markdown("**Card Counts**")
        cols = st.columns(len(tracker.players))
        card_counts = {}
        
        for idx, player in enumerate(tracker.players):
            with cols[idx]:
                count = st.number_input(
                    f"{player}",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"round_{st.session_state.round_num}_{player}_cards"
                )
                card_counts[player] = count
        
        # Special hands input
        st.markdown("**Special Hands** *(optional - each special hand = 5 cards worth from everyone)*")
        cols_special = st.columns(len(tracker.players))
        special_hands = {}
        
        for idx, player in enumerate(tracker.players):
            with cols_special[idx]:
                special_count = st.number_input(
                    f"{player}",
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"round_{st.session_state.round_num}_{player}_special",
                    label_visibility="collapsed"
                )
                if special_count > 0:
                    special_hands[player] = special_count
        
        # Bao player selector
        st.markdown("**Bao (包)** *(optional - select one player to pay for everyone's losses, excluding special hands)*")
        col_bao1, col_bao2 = st.columns([1, 3])
        with col_bao1:
            bao_player = st.selectbox(
                "Bao player",
                options=["None"] + tracker.players,
                key=f"round_{st.session_state.round_num}_bao",
                label_visibility="collapsed"
            )
            if bao_player == "None":
                bao_player = None
        with col_bao2:
            if bao_player:
                st.caption(f"🎯 {bao_player} will pay for everyone's losses this round (special hands still apply normally)")
            else:
                st.caption("Select a player to 'bao' if someone wants to pay for everyone")
        
        col_a, col_b, col_c = st.columns([1, 1, 2])
        with col_a:
            if st.button("➕ Add Round", type="primary", use_container_width=True):
                if sum(card_counts.values()) == 0:
                    st.warning("Enter card counts first!")
                else:
                    tracker.add_round(card_counts, st.session_state.card_value, special_hands, bao_player)
                    st.session_state.round_num += 1
                    
                    # Save to database
                    models.save_game_snapshot(
                        st.session_state.game_id,
                        tracker,
                        st.session_state.round_num,
                        st.session_state.card_value
                    )
                    st.rerun()
        
        with col_b:
            undo_disabled = tracker.history.shape[1] == 0
            if st.button("↩️ Undo Last Round", disabled=undo_disabled, use_container_width=True):
                if tracker.undo_last_round():
                    st.session_state.round_num -= 1
                    
                    # Save to database
                    models.save_game_snapshot(
                        st.session_state.game_id,
                        tracker,
                        st.session_state.round_num,
                        st.session_state.card_value
                    )
                    st.rerun()
        
        with col_c:
            st.caption(f"Total rounds played: {tracker.history.shape[1]}")
        
        st.markdown("---")
        
        # Add to History Log section
        st.subheader("🏁 Finish Game")
        colh1, colh2 = st.columns([1, 2])
        
        with colh1:
            add_disabled = tracker.history.shape[1] == 0 or st.session_state.get("archived_this_game", False)
            add_label = "Add to Log" if not st.session_state.get("archived_this_game") else "Added ✔"
            
            if st.button(add_label, disabled=add_disabled, use_container_width=True):
                final_totals = tracker.get_summary()["Total"].to_dict()
                
                # Build round history for each player (list of round results)
                round_history = {}
                for player in tracker.players:
                    player_rounds = []
                    for col in tracker.history.columns:
                        round_result = tracker.history.loc[player, col]
                        player_rounds.append(float(round_result))
                    round_history[player] = player_rounds
                
                archive_entry = {
                    "archive_id": str(uuid4()),
                    "created_at": datetime.now().strftime(DATETIME_FORMAT),
                    "game_id": st.session_state.game_id,
                    "players": tracker.players,
                    "rounds_played": tracker.history.shape[1],
                    "card_value": st.session_state.card_value,
                    "final_totals": final_totals,
                    "winner_order": [p for p, _ in sorted(final_totals.items(), key=lambda x: x[1], reverse=True)],
                    "round_history": round_history,
                }
                
                # Add to archive and update player stats
                models.add_archived_game(archive_entry)
                st.session_state["archived_this_game"] = True
                st.success("Game added to History Log and Player Profiles updated!")
        
        with colh2:
            st.caption("Click **Add to Log** when you finish your game to save final standings and update player stats.")
        
        # Earnings summary table
        st.subheader("Earnings Summary")
        ui.display_summary_table(tracker)
        
        # Remove specific rounds section
        if tracker.history.shape[1] > 0:
            st.markdown("---")
            st.subheader("🗑️ Remove Specific Round")
            
            col_r1, col_r2, col_r3 = st.columns([2, 1, 2])
            
            with col_r1:
                round_to_remove = st.number_input(
                    "Round number to remove",
                    min_value=1,
                    max_value=tracker.history.shape[1],
                    value=1,
                    step=1,
                    key="round_to_remove"
                )
            
            with col_r2:
                if st.button("Remove Round", type="secondary", use_container_width=True):
                    if tracker.remove_round(round_to_remove):
                        # Adjust round counter if we removed a round
                        if round_to_remove < st.session_state.round_num:
                            st.session_state.round_num -= 1
                        
                        # Save to database
                        models.save_game_snapshot(
                            st.session_state.game_id,
                            tracker,
                            st.session_state.round_num,
                            st.session_state.card_value
                        )
                        st.success(f"Round {round_to_remove} removed!")
                        st.rerun()
                    else:
                        st.error("Failed to remove round!")
            
            with col_r3:
                st.caption(f"Removes the selected round and renumbers remaining rounds sequentially.")


# ====== Tab 2: History Log (Archived Games) ======
with tab2:
    st.subheader("Archived Games")
    archived_games = models.get_all_archived_games()
    
    if not archived_games:
        st.caption("No archived games yet. Finish a game and click **Add to Log** to store it here.")
    else:
        # Define delete callback
        def delete_game(archive_id: str):
            if models.delete_archived_game(archive_id):
                st.success("Game deleted from history and player statistics updated!")
                st.rerun()
            else:
                st.error("Failed to delete game!")
        
        for entry in archived_games:
            ui.display_archived_game(entry, on_delete_callback=delete_game)


# ====== Tab 3: Players (Profiles & Lifetime view) ======
with tab3:
    st.subheader("Player Profiles")
    
    all_players = models.get_all_players()
    
    if not all_players:
        st.caption("No players yet. Add players in the **Player Management** tab.")
    else:
        # Player selector
        player_names = sorted([p["name"] for p in all_players.values()])
        selected_name = st.selectbox("Select a player", options=player_names)
        
        # Get player history
        hist_df = models.get_player_game_history_df(selected_name)
        
        # Display profile
        ui.display_player_profile(selected_name, hist_df)


# ====== Tab 4: Player Management (Add/Remove + Danger Zone) ======
with tab4:
    st.subheader("Player Management")
    
    # Add a single player
    st.markdown("**Add a player**")
    col_ap1, col_ap2 = st.columns([3, 1])
    with col_ap1:
        new_player = st.text_input("Player name", key="pm_add_single")
    with col_ap2:
        if st.button("Add", key="pm_add_single_btn", use_container_width=True):
            if new_player.strip():
                models.add_player(new_player.strip())
                st.success(f"Added player: {new_player.strip()}")
                st.rerun()
            else:
                st.warning("Enter a name first.")
    
    # Add multiple players
    st.markdown("**Add multiple players (comma-separated)**")
    col_apm1, col_apm2 = st.columns([3, 1])
    with col_apm1:
        new_players_csv = st.text_input("e.g. Alice, Bob, Charlie", key="pm_add_multi")
    with col_apm2:
        if st.button("Add All", key="pm_add_multi_btn", use_container_width=True):
            names = [n.strip() for n in new_players_csv.split(",") if n.strip()]
            if names:
                for n in names:
                    models.add_player(n)
                st.success(f"Added: {', '.join(names)}")
                st.rerun()
            else:
                st.warning("Enter at least one name.")
    
    st.markdown("---")
    
    # Remove players
    st.markdown("**Remove players**")
    all_players = models.get_all_players()
    reg_names = sorted([p["name"] for p in all_players.values()])
    
    if not reg_names:
        st.caption("No players to remove.")
    else:
        del_select = st.multiselect("Select players to remove", options=reg_names, key="pm_remove_select")
        st.caption("You cannot remove a player currently in an active game.")
        
        if st.button("Remove Selected", type="secondary", key="pm_remove_btn"):
            if not del_select:
                st.warning("Select at least one player to remove.")
            else:
                removed, blocked = [], []
                active_players = set(st.session_state.tracker.players) if st.session_state.tracker else set()
                
                for name in del_select:
                    if name in active_players:
                        blocked.append(name)
                        continue
                    ok = models.delete_player_by_name(name, active_players)
                    if ok:
                        removed.append(name)
                    else:
                        blocked.append(name)
                
                if removed:
                    st.success(f"Removed: {', '.join(removed)}")
                if blocked:
                    st.warning(f"Could not remove (in active game or not found): {', '.join(blocked)}")
                
                if removed:
                    st.rerun()
    
    st.markdown("---")
    st.markdown("**Registered players**")
    reg_df = models.get_players_table_df()
    ui.format_players_table(reg_df)
    
    # ----- Excel Export -----
    st.markdown("---")
    st.markdown("**📊 Export Data**")
    
    col_export1, col_export2 = st.columns([1, 2])
    with col_export1:
        if st.button("📥 Download Excel Report", type="primary", use_container_width=True):
            try:
                import pandas as pd
                from io import BytesIO
                from datetime import datetime
                
                # Create Excel file in memory
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Sheet 1: Player Statistics
                    players_df = models.get_players_table_df()
                    if not players_df.empty:
                        players_df.to_excel(writer, sheet_name='Player Statistics', index=False)
                    
                    # Sheet 2: Archived Games
                    archived_games = models.get_all_archived_games()
                    if archived_games:
                        games_data = []
                        for game in archived_games:
                            games_data.append({
                                'Date': game['created_at'],
                                'Players': ', '.join(game['players']),
                                'Rounds': game['rounds_played'],
                                'Card Value': game['card_value'],
                                'Winner': game['winner_order'][0] if game['winner_order'] else 'N/A'
                            })
                        games_df = pd.DataFrame(games_data)
                        games_df.to_excel(writer, sheet_name='Archived Games', index=False)
                    
                    # Sheet 3: Detailed Game Results
                    if archived_games:
                        detailed_data = []
                        for game in archived_games:
                            for player, total in game['final_totals'].items():
                                detailed_data.append({
                                    'Date': game['created_at'],
                                    'Player': player,
                                    'Final Total': total,
                                    'Rounds': game['rounds_played'],
                                    'Card Value': game['card_value']
                                })
                        detailed_df = pd.DataFrame(detailed_data)
                        detailed_df.to_excel(writer, sheet_name='Detailed Results', index=False)
                
                # Get the Excel file
                excel_data = output.getvalue()
                
                # Generate filename with timestamp
                filename = f"taidi_tracker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                st.download_button(
                    label="💾 Save Excel File",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Error creating Excel file: {str(e)}")
    
    with col_export2:
        st.caption("Download all your data as an Excel file with multiple sheets: Player Statistics, Archived Games, and Detailed Results.")
    
    # ----- Danger Zone -----
    st.markdown("---")
    with st.expander("🧨 Danger Zone", expanded=False):
        st.caption("These actions are permanent. Use them after testing.")
        
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            if st.button("Clear Archived Games", type="secondary", use_container_width=True):
                models.clear_all_archived_games()
                st.success("Archived games cleared.")
                st.rerun()
        
        with c2:
            if st.button("Clear Player Registry", type="secondary", use_container_width=True):
                models.clear_all_players()
                st.success("Player registry cleared.")
                st.rerun()
        
        with c3:
            sure = st.checkbox("I understand this will delete ALL data", key="confirm_factory_reset")
            if st.button("Full Factory Reset", type="primary", use_container_width=True, disabled=not sure):
                models.full_factory_reset()
                
                # Clear session state
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                
                # Clear URL
                try:
                    st.query_params.clear()
                except Exception:
                    st.experimental_set_query_params()
                
                st.success("Full factory reset complete!")
                st.rerun()