"""Card game tracker logic."""

import pandas as pd
from datetime import datetime


def compute_payouts(card_counts: dict, card_value: float):
    """
    Compute Taidi game payouts based on card differences.
    
    Rules:
    - Each player pays players with fewer cards (difference × card_value)
    - Multipliers based on number of players:
      * 4 players: 2× at 10+ cards, 3× at 13+ cards
      * 3 players: 2× at 12+ cards, 3× at 15+ cards
    - Everyone pays the winner (0 cards) an extra 2 cards worth
    
    Args:
        card_counts: {player_name: number_of_cards}
        card_value: dollar value per card
    
    Returns:
        {player_name: net_payout} (positive = won, negative = lost)
    """
    num_players = len(card_counts)
    
    if num_players == 0:
        return {}
    
    # Initialize payouts (positive = earnings, negative = payments)
    payouts = {player: 0.0 for player in card_counts}
    
    # Determine multiplier thresholds based on number of players
    if num_players == 4:
        double_threshold = 10
        triple_threshold = 13
    elif num_players == 3:
        double_threshold = 12
        triple_threshold = 15
    else:
        # For other player counts, use 4-player rules as default
        double_threshold = 10
        triple_threshold = 13
    
    # Step 1: Calculate pairwise payments based on card differences
    players = list(card_counts.keys())
    for i, payer in enumerate(players):
        payer_cards = card_counts[payer]
        
        # Determine multiplier for this player
        if payer_cards >= triple_threshold:
            multiplier = 3
        elif payer_cards >= double_threshold:
            multiplier = 2
        else:
            multiplier = 1
        
        # Pay each player who has fewer cards
        for j, receiver in enumerate(players):
            if i == j:
                continue
            
            receiver_cards = card_counts[receiver]
            
            # Only pay if receiver has fewer cards
            if payer_cards > receiver_cards:
                card_diff = payer_cards - receiver_cards
                payment = card_diff * card_value * multiplier
                
                payouts[payer] -= payment
                payouts[receiver] += payment
    
    # Step 2: Everyone pays the winner (0 cards) an extra 2 cards
    winners = [player for player, cards in card_counts.items() if cards == 0]
    
    if winners:
        # If there are multiple winners (multiple people with 0 cards), split the bonus
        winner_bonus_per_payer = 2 * card_value
        
        for winner in winners:
            for player in players:
                if player != winner:
                    payouts[player] -= winner_bonus_per_payer
                    payouts[winner] += winner_bonus_per_payer
    
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