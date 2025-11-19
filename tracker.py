"""Card game tracker logic."""

import pandas as pd
from datetime import datetime


def compute_payouts(card_counts: dict, card_value: float):
    """
    Given a dictionary of {player_name: #_cards_they_got},
    compute how much each player owes or is owed.
    Returns {player_name: payout_amount}.
    """
    total_cards = sum(card_counts.values())
    num_players = len(card_counts)
    
    if num_players == 0 or total_cards == 0:
        return {p: 0.0 for p in card_counts}
    
    avg = total_cards / num_players
    payouts = {}
    for player, count in card_counts.items():
        diff = count - avg
        payouts[player] = diff * card_value
    
    return payouts


class CardGameTracker:
    """Tracks card game rounds and calculates earnings."""
    
    def __init__(self, players: list[str]):
        self.players = players
        self.balances = {p: 0.0 for p in players}
        self.history = pd.DataFrame(index=players)
        self.tx_log = []
    
    def add_round(self, card_counts: dict, card_value: float):
        """
        Add a round given card counts for each player.
        card_counts: {player_name: number_of_cards}
        """
        payouts = compute_payouts(card_counts, card_value)
        
        for player in self.players:
            self.balances[player] += payouts.get(player, 0.0)
        
        round_num = self.history.shape[1] + 1
        col_name = f"R{round_num}"
        self.history[col_name] = pd.Series(payouts)
        
        tx = {
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "card_counts": card_counts.copy(),
            "card_value": card_value,
            "payouts": payouts.copy()
        }
        self.tx_log.append(tx)
    
    def undo_last_round(self):
        """Remove the last round from history."""
        if self.history.shape[1] == 0:
            return False
        
        last_col = self.history.columns[-1]
        last_payouts = self.history[last_col].to_dict()
        
        for player in self.players:
            self.balances[player] -= last_payouts.get(player, 0.0)
        
        self.history = self.history.iloc[:, :-1]
        
        if self.tx_log:
            self.tx_log.pop()
        
        return True
    
    def remove_round(self, round_number: int):
        """Remove a specific round from history by round number (1-indexed)."""
        if round_number < 1 or round_number > self.history.shape[1]:
            return False
        
        # Get the column name for this round
        col_name = f"R{round_number}"
        if col_name not in self.history.columns:
            return False
        
        # Get payouts for this round
        round_payouts = self.history[col_name].to_dict()
        
        # Subtract these payouts from balances
        for player in self.players:
            self.balances[player] -= round_payouts.get(player, 0.0)
        
        # Remove the column
        self.history = self.history.drop(columns=[col_name])
        
        # Rename remaining columns to be sequential
        new_columns = {}
        for i, old_col in enumerate(self.history.columns, start=1):
            new_columns[old_col] = f"R{i}"
        self.history = self.history.rename(columns=new_columns)
        
        # Remove from transaction log
        if self.tx_log and round_number <= len(self.tx_log):
            self.tx_log.pop(round_number - 1)
            # Update round numbers in remaining transactions
            for i in range(round_number - 1, len(self.tx_log)):
                self.tx_log[i]["round"] = i + 1
        
        return True
    
    def get_summary(self) -> pd.DataFrame:
        """Return a DataFrame with all round details plus a Total column."""
        summary = self.history.copy()
        summary['Total'] = summary.sum(axis=1)
        return summary
    
    def get_balances(self) -> dict:
        """Return current balances as a dictionary."""
        return self.balances.copy()