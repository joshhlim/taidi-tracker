"""Database operations for Taidi card game tracker with Turso support."""

import json
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager

from config import USE_TURSO, DATETIME_FORMAT

if USE_TURSO:
    # Turso (cloud database) - using sync wrapper
    import asyncio
    from libsql_client import create_client
    from config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN
    
    # Create a global client that's reused
    _turso_client = None
    
    def get_turso_client():
        """Get or create Turso client."""
        global _turso_client
        if _turso_client is None:
            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            _turso_client = create_client(
                url=TURSO_DATABASE_URL,
                auth_token=TURSO_AUTH_TOKEN
            )
        return _turso_client
    
    @contextmanager
    def get_db_connection():
        """Context manager for Turso database connections."""
        client = get_turso_client()
        try:
            yield client
        except Exception as e:
            raise e
    
    # Turso query execution helpers
    def execute_query(client, query, params=None):
        """Execute a query on Turso."""
        if params:
            result = client.execute(query, params)
        else:
            result = client.execute(query)
        return result
    
    def fetchall(client, query, params=None):
        """Fetch all rows from Turso."""
        result = execute_query(client, query, params)
        return result.rows
    
    def fetchone(client, query, params=None):
        """Fetch one row from Turso."""
        result = execute_query(client, query, params)
        return result.rows[0] if result.rows else None

else:
    # SQLite (local database)
    import sqlite3
    from config import DATABASE_PATH
    
    @contextmanager
    def get_db_connection():
        """Context manager for SQLite database connections."""
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def execute_query(conn, query, params=None):
        """Execute a query on SQLite."""
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor
    
    def fetchall(conn, query, params=None):
        """Fetch all rows from SQLite."""
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()
    
    def fetchone(conn, query, params=None):
        """Fetch one row from SQLite."""
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchone()


def init_database():
    """Initialize the database schema."""
    with get_db_connection() as conn:
        # Players table
        execute_query(conn, """
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
        execute_query(conn, """
            CREATE TABLE IF NOT EXISTS archived_games (
                archive_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                game_id TEXT,
                players TEXT NOT NULL,
                rounds_played INTEGER NOT NULL,
                card_value REAL DEFAULT 0.0,
                final_totals TEXT NOT NULL,
                winner_order TEXT NOT NULL,
                round_history TEXT
            )
        """)
        
        # Active games table
        execute_query(conn, """
            CREATE TABLE IF NOT EXISTS active_games (
                game_id TEXT PRIMARY KEY,
                snapshot TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)


# ============== Player Operations ==============

def get_all_players() -> Dict[str, Dict]:
    """Get all players from the database."""
    with get_db_connection() as conn:
        rows = fetchall(conn, "SELECT * FROM players")
        
        players = {}
        for row in rows:
            if USE_TURSO:
                players[row['player_id']] = {
                    "player_id": row['player_id'],
                    "name": row['name'],
                    "created_at": row['created_at'],
                    "games_played": row['games_played'],
                    "total_net": row['total_net'],
                    "avg_per_game": row['avg_per_game'],
                    "wins": row['wins'],
                    "losses": row['losses'],
                    "ties": row['ties'],
                    "last_played": row['last_played'],
                }
            else:
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
            execute_query(conn, """
                INSERT INTO players (
                    player_id, name, created_at, games_played, 
                    total_net, avg_per_game, wins, losses, ties, last_played
                )
                VALUES (?, ?, ?, 0, 0.0, 0.0, 0, 0, 0, NULL)
            """, (player_id, name, created_at))
            return True
    except Exception:
        return False


def get_player_by_name(name: str) -> Optional[Dict]:
    """Get a player by name (case-insensitive)."""
    with get_db_connection() as conn:
        row = fetchone(conn,
            "SELECT * FROM players WHERE LOWER(name) = LOWER(?)",
            (name,)
        )
        if row:
            if USE_TURSO:
                return {
                    "player_id": row['player_id'],
                    "name": row['name'],
                    "created_at": row['created_at'],
                    "games_played": row['games_played'],
                    "total_net": row['total_net'],
                    "avg_per_game": row['avg_per_game'],
                    "wins": row['wins'],
                    "losses": row['losses'],
                    "ties": row['ties'],
                    "last_played": row['last_played'],
                }
            else:
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
            cursor = execute_query(conn, "DELETE FROM players WHERE player_id = ?", (player_id,))
            return (cursor.rowcount if not USE_TURSO else cursor.rows_affected) > 0
    except Exception:
        return False


def update_player_stats(player_id: str, stats: Dict) -> bool:
    """Update player statistics."""
    try:
        with get_db_connection() as conn:
            execute_query(conn, """
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
            return True
    except Exception:
        return False


def clear_all_players():
    """Delete all players from the database."""
    with get_db_connection() as conn:
        execute_query(conn, "DELETE FROM players")


# ============== Archived Games Operations ==============

def add_archived_game(entry: Dict) -> str:
    """Add an archived game to the database."""
    with get_db_connection() as conn:
        execute_query(conn, """
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
        rows = fetchall(conn, "SELECT * FROM archived_games ORDER BY created_at DESC")
        
        games = []
        for row in rows:
            game_dict = {
                "archive_id": row['archive_id'] if USE_TURSO else row["archive_id"],
                "created_at": row['created_at'] if USE_TURSO else row["created_at"],
                "game_id": row['game_id'] if USE_TURSO else row["game_id"],
                "players": json.loads(row['players'] if USE_TURSO else row["players"]),
                "rounds_played": row['rounds_played'] if USE_TURSO else row["rounds_played"],
                "card_value": row['card_value'] if USE_TURSO else row["card_value"],
                "final_totals": json.loads(row['final_totals'] if USE_TURSO else row["final_totals"]),
                "winner_order": json.loads(row['winner_order'] if USE_TURSO else row["winner_order"]),
            }
            # Handle round_history which might not exist in older entries
            round_hist = row['round_history'] if USE_TURSO else row["round_history"]
            if round_hist:
                game_dict["round_history"] = json.loads(round_hist)
            else:
                game_dict["round_history"] = {}
            games.append(game_dict)
        return games


def delete_archived_game(archive_id: str) -> bool:
    """Delete a specific archived game from the database."""
    try:
        with get_db_connection() as conn:
            cursor = execute_query(conn, "DELETE FROM archived_games WHERE archive_id = ?", (archive_id,))
            return (cursor.rowcount if not USE_TURSO else cursor.rows_affected) > 0
    except Exception:
        return False


def clear_all_archived_games():
    """Delete all archived games from the database."""
    with get_db_connection() as conn:
        execute_query(conn, "DELETE FROM archived_games")


# ============== Active Games Operations ==============

def save_active_game(game_id: str, snapshot: Dict):
    """Save or update an active game snapshot."""
    with get_db_connection() as conn:
        last_updated = datetime.now().strftime(DATETIME_FORMAT)
        execute_query(conn, """
            INSERT OR REPLACE INTO active_games (game_id, snapshot, last_updated)
            VALUES (?, ?, ?)
        """, (game_id, json.dumps(snapshot), last_updated))


def load_active_game(game_id: str) -> Optional[Dict]:
    """Load an active game snapshot."""
    with get_db_connection() as conn:
        row = fetchone(conn,
            "SELECT snapshot FROM active_games WHERE game_id = ?",
            (game_id,)
        )
        if row:
            return json.loads(row['snapshot'] if USE_TURSO else row["snapshot"])
        return None


def delete_active_game(game_id: str):
    """Delete an active game snapshot."""
    with get_db_connection() as conn:
        execute_query(conn, "DELETE FROM active_games WHERE game_id = ?", (game_id,))


def clear_all_active_games():
    """Delete all active game snapshots."""
    with get_db_connection() as conn:
        execute_query(conn, "DELETE FROM active_games")


# ============== Full Database Reset ==============

def full_database_reset():
    """Delete all data from all tables."""
    with get_db_connection() as conn:
        execute_query(conn, "DELETE FROM players")
        execute_query(conn, "DELETE FROM archived_games")
        execute_query(conn, "DELETE FROM active_games")


# Initialize database (deferred to avoid async issues at import time)
if not USE_TURSO:
    # SQLite can initialize immediately
    init_database()
# Turso initialization will happen on first connection