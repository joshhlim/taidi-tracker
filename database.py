"""Database operations for Taidi card game tracker."""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import streamlit as st

from config import DATABASE_PATH, DATETIME_FORMAT


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Initialize the database schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                games_played INTEGER DEFAULT 0,
                total_net REAL DEFAULT 0.0,
                avg_per_game REAL DEFAULT 0.0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                last_played TEXT
            )
        """)
        
        # Archived games table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archived_games (
                archive_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                game_id TEXT,
                players TEXT NOT NULL,
                rounds_played INTEGER NOT NULL,
                card_value REAL NOT NULL,
                final_totals TEXT NOT NULL,
                winner_order TEXT NOT NULL,
                round_history TEXT
            )
        """)
        
        # Active games table (for persistence across refreshes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_games (
                game_id TEXT PRIMARY KEY,
                snapshot TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)
        
        conn.commit()


# ============== Player Operations ==============

def get_all_players() -> Dict[str, Dict]:
    """Get all players from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players")
        rows = cursor.fetchall()
        
        players = {}
        for row in rows:
            players[row["player_id"]] = {
                "player_id": row["player_id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "games_played": row["games_played"],
                "total_net": row["total_net"],
                "avg_per_game": row["avg_per_game"],
                "wins": row["wins"],
                "losses": row["losses"],
                "ties": row["ties"],
                "last_played": row["last_played"],
            }
        return players


def add_player(player_id: str, name: str, created_at: str) -> bool:
    """Add a new player to the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO players (
                    player_id, name, created_at, games_played, 
                    total_net, avg_per_game, wins, losses, ties, last_played
                )
                VALUES (?, ?, ?, 0, 0.0, 0.0, 0, 0, 0, NULL)
            """, (player_id, name, created_at))
            return True
    except sqlite3.IntegrityError:
        return False


def get_player_by_name(name: str) -> Optional[Dict]:
    """Get a player by name (case-insensitive)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM players WHERE LOWER(name) = LOWER(?)",
            (name,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "player_id": row["player_id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "games_played": row["games_played"],
                "total_net": row["total_net"],
                "avg_per_game": row["avg_per_game"],
                "wins": row["wins"],
                "losses": row["losses"],
                "ties": row["ties"],
                "last_played": row["last_played"],
            }
        return None


def delete_player(player_id: str) -> bool:
    """Delete a player from the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM players WHERE player_id = ?", (player_id,))
            return cursor.rowcount > 0
    except Exception:
        return False


def update_player_stats(player_id: str, stats: Dict) -> bool:
    """Update player statistics."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE players
                SET games_played = ?,
                    total_net = ?,
                    avg_per_game = ?,
                    wins = ?,
                    losses = ?,
                    ties = ?,
                    last_played = ?
                WHERE player_id = ?
            """, (
                stats["games_played"],
                stats["total_net"],
                stats["avg_per_game"],
                stats["wins"],
                stats["losses"],
                stats["ties"],
                stats["last_played"],
                player_id
            ))
            return cursor.rowcount > 0
    except Exception:
        return False


def clear_all_players():
    """Delete all players from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM players")


# ============== Archived Games Operations ==============

def add_archived_game(entry: Dict) -> str:
    """Add an archived game to the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO archived_games (
                archive_id, created_at, game_id, players,
                rounds_played, card_value, final_totals, winner_order, round_history
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry["archive_id"],
            entry["created_at"],
            entry.get("game_id"),
            json.dumps(entry["players"]),
            entry["rounds_played"],
            entry["card_value"],
            json.dumps(entry["final_totals"]),
            json.dumps(entry["winner_order"]),
            json.dumps(entry.get("round_history", {})),
        ))
        return entry["archive_id"]


def get_all_archived_games() -> List[Dict]:
    """Get all archived games from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM archived_games ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        games = []
        for row in rows:
            game_dict = {
                "archive_id": row["archive_id"],
                "created_at": row["created_at"],
                "game_id": row["game_id"],
                "players": json.loads(row["players"]),
                "rounds_played": row["rounds_played"],
                "card_value": row["card_value"],
                "final_totals": json.loads(row["final_totals"]),
                "winner_order": json.loads(row["winner_order"]),
            }
            # Handle round_history which might not exist in older entries
            if row["round_history"]:
                game_dict["round_history"] = json.loads(row["round_history"])
            else:
                game_dict["round_history"] = {}
            games.append(game_dict)
        return games


def delete_archived_game(archive_id: str) -> bool:
    """Delete a specific archived game from the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM archived_games WHERE archive_id = ?", (archive_id,))
            return cursor.rowcount > 0
    except Exception:
        return False


def clear_all_archived_games():
    """Delete all archived games from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM archived_games")


# ============== Active Games Operations ==============

def save_active_game(game_id: str, snapshot: Dict):
    """Save or update an active game snapshot."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        last_updated = datetime.now().strftime(DATETIME_FORMAT)
        cursor.execute("""
            INSERT OR REPLACE INTO active_games (game_id, snapshot, last_updated)
            VALUES (?, ?, ?)
        """, (game_id, json.dumps(snapshot), last_updated))


def load_active_game(game_id: str) -> Optional[Dict]:
    """Load an active game snapshot."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT snapshot FROM active_games WHERE game_id = ?",
            (game_id,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["snapshot"])
        return None


def delete_active_game(game_id: str):
    """Delete an active game snapshot."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_games WHERE game_id = ?", (game_id,))


def clear_all_active_games():
    """Delete all active game snapshots."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_games")


# ============== Full Database Reset ==============

def full_database_reset():
    """Delete all data from all tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM players")
        cursor.execute("DELETE FROM archived_games")
        cursor.execute("DELETE FROM active_games")


# Initialize database on module import
init_database()