"""Data models and business logic for Taidi card game tracker."""

import pandas as pd
from uuid import uuid4
from datetime import datetime
from typing import Dict, List, Optional

import database as db
from config import DATETIME_FORMAT
from tracker import CardGameTracker


# ============== Player Management ==============

def get_all_players() -> Dict[str, Dict]:
    """Get all players from the database."""
    return db.get_all_players()


def add_player(name: str) -> str:
    """
    Add a new player or return existing player ID if name exists.
    Returns player_id.
    """
    name_clean = name.strip()
    if not name_clean:
        return ""
    
    # Check if player exists (case-insensitive)
    existing = db.get_player_by_name(name_clean)
    if existing:
        return existing["player_id"]
    
    # Create new player
    player_id = str(uuid4())
    created_at = datetime.now().strftime(DATETIME_FORMAT)
    db.add_player(player_id, name_clean, created_at)
    return player_id


def delete_player_by_name(name: str, active_players: set = None) -> bool:
    """
    Delete a player by name (case-insensitive).
    Returns True if deleted, False if player is in active game or not found.
    """
    player = db.get_player_by_name(name)
    if not player:
        return False
    
    # Don't allow deleting a player in an active game
    if active_players and name in active_players:
        return False
    
    return db.delete_player(player["player_id"])


def update_player_stats_from_archive(entry: Dict):
    """Update player lifetime stats from one archived game entry."""
    totals = entry.get("final_totals", {})
    round_history = entry.get("round_history", {})
    
    for name, net in totals.items():
        # Ensure player exists
        player_id = add_player(name)
        player = db.get_player_by_name(name)
        
        if not player:
            continue
        
        # Count wins/losses/ties from round history (round-based)
        round_wins = 0
        round_losses = 0
        round_ties = 0
        
        # If we have round history, use it
        if round_history and name in round_history:
            player_rounds = round_history[name]
            for round_result in player_rounds:
                if round_result > 0:
                    round_wins += 1
                elif round_result < 0:
                    round_losses += 1
                else:
                    round_ties += 1
        
        # Update stats
        stats = {
            "games_played": player["games_played"] + 1,
            "total_net": player["total_net"] + float(net),
            "avg_per_game": 0.0,
            "wins": player["wins"] + round_wins,
            "losses": player["losses"] + round_losses,
            "ties": player["ties"] + round_ties,
            "last_played": entry.get("created_at"),
        }
        
        # Calculate average
        if stats["games_played"] > 0:
            stats["avg_per_game"] = stats["total_net"] / stats["games_played"]
        
        db.update_player_stats(player_id, stats)


def recalculate_all_player_stats():
    """Recalculate all player statistics from scratch based on archived games."""
    # Get all players and reset their stats
    all_players = db.get_all_players()
    
    for player_id, player_data in all_players.items():
        reset_stats = {
            "games_played": 0,
            "total_net": 0.0,
            "avg_per_game": 0.0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "last_played": None,
        }
        db.update_player_stats(player_id, reset_stats)
    
    # Get all archived games and recalculate stats
    archived_games = db.get_all_archived_games()
    
    # Sort by created_at to get the correct last_played
    archived_games_sorted = sorted(archived_games, key=lambda x: x.get("created_at", ""))
    
    for entry in archived_games_sorted:
        totals = entry.get("final_totals", {})
        round_history = entry.get("round_history", {})
        
        for name, net in totals.items():
            # Ensure player exists
            player_id = add_player(name)
            player = db.get_player_by_name(name)
            
            if not player:
                continue
            
            # Count wins/losses/ties from round history (round-based)
            round_wins = 0
            round_losses = 0
            round_ties = 0
            
            # If we have round history, use it
            if round_history and name in round_history:
                player_rounds = round_history[name]
                for round_result in player_rounds:
                    if round_result > 0:
                        round_wins += 1
                    elif round_result < 0:
                        round_losses += 1
                    else:
                        round_ties += 1
            # Fallback for old games without round history
            else:
                # Can't determine round-by-round, so skip W/L/T for this game
                pass
            
            # Update stats
            stats = {
                "games_played": player["games_played"] + 1,
                "total_net": player["total_net"] + float(net),
                "avg_per_game": 0.0,
                "wins": player["wins"] + round_wins,
                "losses": player["losses"] + round_losses,
                "ties": player["ties"] + round_ties,
                "last_played": entry.get("created_at"),
            }
            
            # Calculate average
            if stats["games_played"] > 0:
                stats["avg_per_game"] = stats["total_net"] / stats["games_played"]
            
            db.update_player_stats(player_id, stats)


def get_players_table_df() -> pd.DataFrame:
    """Get players table as a DataFrame for display."""
    players = db.get_all_players()
    
    if not players:
        return pd.DataFrame(columns=[
            "Player", "Games", "Total", "Avg/Game", "W", "L", "T", "Last Played"
        ])
    
    rows = []
    for pdata in players.values():
        rows.append({
            "Player": pdata["name"],
            "Games": pdata["games_played"],
            "Total": pdata["total_net"],
            "Avg/Game": pdata["avg_per_game"],
            "W": pdata["wins"],
            "L": pdata["losses"],
            "T": pdata["ties"],
            "Last Played": pdata["last_played"] or "-",
        })
    
    df = pd.DataFrame(rows).sort_values(["Total", "Games"], ascending=[False, False])
    return df


def get_player_game_history_df(player_name: str) -> pd.DataFrame:
    """Build per-game history for one player from archived games."""
    archived_games = db.get_all_archived_games()
    
    rows = []
    for entry in archived_games:
        totals = entry.get("final_totals", {})
        if player_name in totals:
            rows.append({
                "When": entry.get("created_at", ""),
                "Rounds": entry.get("rounds_played", 0),
                "Card Value": entry.get("card_value", 0.0),
                "Net": float(totals[player_name])
            })
    
    if not rows:
        return pd.DataFrame(columns=["When", "Rounds", "Card Value", "Net"])
    
    df = pd.DataFrame(rows).sort_values("When", ascending=False)
    return df


def clear_all_players():
    """Delete all players from the database."""
    db.clear_all_players()


# ============== Archived Games Management ==============

def add_archived_game(entry: Dict) -> str:
    """Add an archived game to the database and update player stats."""
    # Ensure archive_id exists
    if "archive_id" not in entry:
        entry["archive_id"] = str(uuid4())
    
    # Add to database
    archive_id = db.add_archived_game(entry)
    
    # Update player stats
    update_player_stats_from_archive(entry)
    
    return archive_id


def get_all_archived_games() -> List[Dict]:
    """Get all archived games from the database."""
    return db.get_all_archived_games()


def delete_archived_game(archive_id: str) -> bool:
    """Delete a specific archived game from the database and recalculate player stats."""
    success = db.delete_archived_game(archive_id)
    
    if success:
        # Recalculate all player statistics from remaining archived games
        recalculate_all_player_stats()
    
    return success


def clear_all_archived_games():
    """Delete all archived games from the database and reset player stats."""
    db.clear_all_archived_games()
    # Reset all player stats since there are no archived games
    recalculate_all_player_stats()


# ============== Active Game Persistence ==============

def save_game_snapshot(game_id: str, tracker: CardGameTracker, round_num: int, card_value: float):
    """Save the current game state to the database."""
    snapshot = {
        "players": tracker.players,
        "balances": tracker.balances,
        "history": tracker.history.to_dict(orient="split"),
        "round_num": round_num,
        "card_value": card_value,
        "tx_log": getattr(tracker, "tx_log", []),
    }
    db.save_active_game(game_id, snapshot)


def load_game_snapshot(game_id: str) -> Optional[Dict]:
    """Load a game snapshot from the database."""
    return db.load_active_game(game_id)


def restore_tracker_from_snapshot(snapshot: Dict) -> tuple[CardGameTracker, int, float]:
    """Restore a CardGameTracker from a snapshot."""
    players = snapshot["players"]
    tracker = CardGameTracker(players)
    tracker.balances = snapshot["balances"]
    
    hist = snapshot["history"]
    tracker.history = pd.DataFrame(
        data=hist["data"], 
        index=hist["index"], 
        columns=hist["columns"]
    )
    tracker.tx_log = snapshot.get("tx_log", [])
    
    round_num = snapshot["round_num"]
    card_value = snapshot["card_value"]
    
    return tracker, round_num, card_value


def delete_game_snapshot(game_id: str):
    """Delete an active game snapshot from the database."""
    db.delete_active_game(game_id)


# ============== Factory Reset ==============

def full_factory_reset():
    """Delete all data from the database."""
    db.full_database_reset()