import copy
from enum import Enum, auto
from random import uniform

from millify import millify

#from TwitchChannelPointsMiner.utils import char_decision_as_index, float_round
from TwitchChannelPointsMiner.utils import float_round


class Strategy(Enum):
    MOST_VOTED = auto()
    HIGH_ODDS = auto()
    PERCENTAGE = auto()
    SMART_MONEY = auto()
    SMART = auto()
    NUMBER_1 = auto()
    NUMBER_2 = auto()
    NUMBER_3 = auto()
    NUMBER_4 = auto()
    NUMBER_5 = auto()
    NUMBER_6 = auto()
    NUMBER_7 = auto()
    NUMBER_8 = auto()

    def __str__(self):
        return self.name


class Condition(Enum):
    GT = auto()
    LT = auto()
    GTE = auto()
    LTE = auto()

    def __str__(self):
        return self.name


class OutcomeKeys(object):
    # Real key on Bet dict ['']
    PERCENTAGE_USERS = "percentage_users"
    ODDS_PERCENTAGE = "odds_percentage"
    ODDS = "odds"
    TOP_POINTS = "top_points"
    # Real key on Bet dict [''] - Sum()
    TOTAL_USERS = "total_users"
    TOTAL_POINTS = "total_points"
    # This key does not exist
    DECISION_USERS = "decision_users"
    DECISION_POINTS = "decision_points"


class DelayMode(Enum):
    FROM_START = auto()
    FROM_END = auto()
    PERCENTAGE = auto()

    def __str__(self):
        return self.name


class FilterCondition(object):
    __slots__ = [
        "by",
        "where",
        "value",
    ]

    def __init__(self, by=None, where=None, value=None, decision=None):
        self.by = by
        self.where = where
        self.value = value

    def __repr__(self):
        return f"FilterCondition(by={self.by.upper()}, where={self.where}, value={self.value})"


class BetSettings(object):
    __slots__ = [
        "strategy",
        "percentage",
        "percentage_gap",
        "max_points",
        "minimum_points",
        "stealth_mode",
        "filter_condition",
        "delay",
        "delay_mode",
    ]

    def __init__(
        self,
        strategy: Strategy = None,
        percentage: int = None,
        percentage_gap: int = None,
        max_points: int = None,
        minimum_points: int = None,
        stealth_mode: bool = None,
        filter_condition: FilterCondition = None,
        delay: float = None,
        delay_mode: DelayMode = None,
    ):
        self.strategy = strategy
        self.percentage = percentage
        self.percentage_gap = percentage_gap
        self.max_points = max_points
        self.minimum_points = minimum_points
        self.stealth_mode = stealth_mode
        self.filter_condition = filter_condition
        self.delay = delay
        self.delay_mode = delay_mode

    def default(self):
        self.strategy = self.strategy if self.strategy is not None else Strategy.SMART
        self.percentage = self.percentage if self.percentage is not None else 5
        self.percentage_gap = (
            self.percentage_gap if self.percentage_gap is not None else 20
        )
        self.max_points = self.max_points if self.max_points is not None else 50000
        self.minimum_points = (
            self.minimum_points if self.minimum_points is not None else 0
        )
        self.stealth_mode = (
            self.stealth_mode if self.stealth_mode is not None else False
        )
        self.delay = self.delay if self.delay is not None else 6
        self.delay_mode = (
            self.delay_mode if self.delay_mode is not None else DelayMode.FROM_END
        )

    def __repr__(self):
        return f"BetSettings(strategy={self.strategy}, percentage={self.percentage}, percentage_gap={self.percentage_gap}, max_points={self.max_points}, minimum_points={self.minimum_points}, stealth_mode={self.stealth_mode})"


class Bet(object):
    __slots__ = ["outcomes", "decision", "total_users", "total_points", "settings"]

    def __init__(self, outcomes: list, settings: BetSettings):
        self.outcomes = outcomes
        self.__clear_outcomes()
        self.decision: dict = {}
        self.total_users = 0
        self.total_points = 0
        self.settings = settings

    def update_outcomes(self, outcomes):
        for index in range(0, len(self.outcomes)):
            self.outcomes[index][OutcomeKeys.TOTAL_USERS] = int(
                outcomes[index][OutcomeKeys.TOTAL_USERS]
            )
            self.outcomes[index][OutcomeKeys.TOTAL_POINTS] = int(
                outcomes[index][OutcomeKeys.TOTAL_POINTS]
            )
            if outcomes[index]["top_predictors"] != []:
                # Sort by points placed by other users
                outcomes[index]["top_predictors"] = sorted(
                    outcomes[index]["top_predictors"],
                    key=lambda x: x["points"],
                    reverse=True,
                )
                # Get the first elements (most placed)
                top_points = outcomes[index]["top_predictors"][0]["points"]
                self.outcomes[index][OutcomeKeys.TOP_POINTS] = top_points
            else:
                # Ensure TOP_POINTS is set to 0 if no top predictors
                self.outcomes[index][OutcomeKeys.TOP_POINTS] = 0

        # Calculate totals
        self.total_points = 0
        self.total_users = 0
        for index in range(0, len(self.outcomes)):
            self.total_users += self.outcomes[index][OutcomeKeys.TOTAL_USERS]
            self.total_points += self.outcomes[index][OutcomeKeys.TOTAL_POINTS]

        # Only calculate percentages and odds if we have meaningful data
        if self.total_users > 0 and self.total_points > 0:
            for index in range(0, len(self.outcomes)):
                # User percentage calculation
                self.outcomes[index][OutcomeKeys.PERCENTAGE_USERS] = float_round(
                    (100 * self.outcomes[index][OutcomeKeys.TOTAL_USERS]) / self.total_users
                )
                
                # Improved odds calculation with safety checks
                outcome_points = self.outcomes[index][OutcomeKeys.TOTAL_POINTS]
                if outcome_points > 0:
                    raw_odds = self.total_points / outcome_points
                    # Cap extremely high odds to prevent overflow and unrealistic scenarios
                    self.outcomes[index][OutcomeKeys.ODDS] = float_round(min(raw_odds, 1000))
                else:
                    # If no points on this outcome, set very high odds (but not infinite)
                    self.outcomes[index][OutcomeKeys.ODDS] = 999
                
                # Odds percentage calculation with safety
                odds_value = self.outcomes[index][OutcomeKeys.ODDS]
                if odds_value > 0:
                    odds_percentage = 100 / odds_value
                    # Ensure odds percentage is reasonable (between 0.1% and 100%)
                    self.outcomes[index][OutcomeKeys.ODDS_PERCENTAGE] = float_round(
                        max(0.1, min(odds_percentage, 100))
                    )
                else:
                    self.outcomes[index][OutcomeKeys.ODDS_PERCENTAGE] = 0.1
        else:
            # If insufficient data, set default safe values
            for index in range(0, len(self.outcomes)):
                self.outcomes[index][OutcomeKeys.PERCENTAGE_USERS] = 50.0 if len(self.outcomes) == 2 else 100.0 / len(self.outcomes)
                self.outcomes[index][OutcomeKeys.ODDS] = 2.0 if len(self.outcomes) == 2 else len(self.outcomes)
                self.outcomes[index][OutcomeKeys.ODDS_PERCENTAGE] = 50.0 if len(self.outcomes) == 2 else 100.0 / len(self.outcomes)

        self.__clear_outcomes()

    def __repr__(self):
        return f"Bet(total_users={millify(self.total_users)}, total_points={millify(self.total_points)}), decision={self.decision})\n\t\tOutcome A({self.get_outcome(0)})\n\t\tOutcome B({self.get_outcome(1)})"

    def get_decision(self, parsed=False):
        #decision = self.outcomes[0 if self.decision["choice"] == "A" else 1]
        decision = self.outcomes[self.decision["choice"]]
        return decision if parsed is False else Bet.__parse_outcome(decision)

    @staticmethod
    def __parse_outcome(outcome):
        return f"{outcome['title']} ({outcome['color']}), Points: {millify(outcome[OutcomeKeys.TOTAL_POINTS])}, Users: {millify(outcome[OutcomeKeys.TOTAL_USERS])} ({outcome[OutcomeKeys.PERCENTAGE_USERS]}%), Odds: {outcome[OutcomeKeys.ODDS]} ({outcome[OutcomeKeys.ODDS_PERCENTAGE]}%)"

    def get_outcome(self, index):
        return Bet.__parse_outcome(self.outcomes[index])

    def __clear_outcomes(self):
        for index in range(0, len(self.outcomes)):
            keys = copy.deepcopy(list(self.outcomes[index].keys()))
            for key in keys:
                if key not in [
                    OutcomeKeys.TOTAL_USERS,
                    OutcomeKeys.TOTAL_POINTS,
                    OutcomeKeys.TOP_POINTS,
                    OutcomeKeys.PERCENTAGE_USERS,
                    OutcomeKeys.ODDS,
                    OutcomeKeys.ODDS_PERCENTAGE,
                    "title",
                    "color",
                    "id",
                ]:
                    del self.outcomes[index][key]
            for key in [
                OutcomeKeys.PERCENTAGE_USERS,
                OutcomeKeys.ODDS,
                OutcomeKeys.ODDS_PERCENTAGE,
                OutcomeKeys.TOP_POINTS,
            ]:
                if key not in self.outcomes[index]:
                    self.outcomes[index][key] = 0

    '''def __return_choice(self, key) -> str:
        return "A" if self.outcomes[0][key] > self.outcomes[1][key] else "B"'''

    def __return_choice(self, key) -> int:
        """Enhanced choice selection with tie-breaking logic"""
        if len(self.outcomes) == 0:
            return 0
            
        largest = 0
        largest_value = self.outcomes[0][key]
        
        # Find the outcome with the highest value for the given key
        for index in range(1, len(self.outcomes)):
            if self.outcomes[index][key] > largest_value:
                largest = index
                largest_value = self.outcomes[index][key]
        
        # Check for ties and use secondary criteria
        tied_outcomes = []
        for index in range(len(self.outcomes)):
            # Consider it a tie if within 2% of the largest value (for percentage-based keys)
            if key in [OutcomeKeys.PERCENTAGE_USERS, OutcomeKeys.ODDS_PERCENTAGE]:
                if abs(self.outcomes[index][key] - largest_value) <= 2:
                    tied_outcomes.append(index)
            # For absolute values, use exact match
            elif self.outcomes[index][key] == largest_value:
                tied_outcomes.append(index)
        
        # If there's a clear winner, return it
        if len(tied_outcomes) <= 1:
            return largest
        
        # Tie-breaking logic based on secondary criteria
        best_tiebreaker = tied_outcomes[0]
        best_score = 0
        
        for outcome_index in tied_outcomes:
            # Create a composite score for tie-breaking
            user_factor = self.outcomes[outcome_index][OutcomeKeys.TOTAL_USERS] / max(self.total_users, 1)
            points_factor = self.outcomes[outcome_index][OutcomeKeys.TOTAL_POINTS] / max(self.total_points, 1)
            
            # For odds-based ties, prefer higher user count
            # For user-based ties, prefer higher points
            if key in [OutcomeKeys.ODDS, OutcomeKeys.ODDS_PERCENTAGE]:
                tiebreaker_score = user_factor * 0.7 + points_factor * 0.3
            else:
                tiebreaker_score = points_factor * 0.6 + user_factor * 0.4
            
            if tiebreaker_score > best_score:
                best_score = tiebreaker_score
                best_tiebreaker = outcome_index
        
        return best_tiebreaker

    def __return_number_choice(self, number) -> int:
        if (len(self.outcomes) > number):
            return number
        else:
            return 0

    def __return_choice_smart_money(self) -> int:
        """Enhanced SMART_MONEY strategy that considers multiple top bets and their distribution"""
        # If no top points data, fall back to regular choice
        if not any(self.outcomes[i][OutcomeKeys.TOP_POINTS] > 0 for i in range(len(self.outcomes))):
            return self.__return_choice(OutcomeKeys.TOTAL_POINTS)
        
        # Calculate "smart money" confidence for each outcome
        smart_scores = []
        for i in range(len(self.outcomes)):
            top_points = self.outcomes[i][OutcomeKeys.TOP_POINTS]
            total_points = self.outcomes[i][OutcomeKeys.TOTAL_POINTS]
            total_users = self.outcomes[i][OutcomeKeys.TOTAL_USERS]
            
            # Avoid division by zero
            if total_users == 0:
                avg_bet = 0
            else:
                avg_bet = total_points / total_users
            
            # Smart money confidence = how much bigger the top bet is vs average + raw top bet size
            if avg_bet > 0:
                top_vs_avg_ratio = top_points / avg_bet
            else:
                top_vs_avg_ratio = 1
                
            # Score = top bet size weighted by how much it stands out
            smart_score = top_points * (1 + min(top_vs_avg_ratio / 10, 2))  # Cap the multiplier
            smart_scores.append(smart_score)
        
        # Return outcome with highest smart money score
        return smart_scores.index(max(smart_scores))

    def __return_choice_smart(self) -> int:
        """Enhanced SMART strategy with multi-factor analysis"""
        if len(self.outcomes) < 2:
            return 0
            
        # Original user percentage difference
        user_diff = abs(
            self.outcomes[0][OutcomeKeys.PERCENTAGE_USERS]
            - self.outcomes[1][OutcomeKeys.PERCENTAGE_USERS]
        )
        
        # Points difference  
        points_diff = abs(
            self.outcomes[0][OutcomeKeys.TOTAL_POINTS]
            - self.outcomes[1][OutcomeKeys.TOTAL_POINTS]
        )
        total_points = self.total_points if self.total_points > 0 else 1
        points_diff_percentage = (points_diff / total_points) * 100
        
        # Calculate confidence factors
        data_confidence = min(self.total_users / 100, 1.0)  # More users = more confidence
        consensus_factor = (user_diff + points_diff_percentage) / 2  # Combined consensus
        
        # Dynamic percentage gap based on data quality
        effective_gap = self.settings.percentage_gap * (2 - data_confidence)  # Less data = need bigger gap
        
        # Decision logic with multiple factors
        if consensus_factor < effective_gap:
            # Low consensus - use odds (contrarian approach)
            odds_choice = self.__return_choice(OutcomeKeys.ODDS)
            
            # But check if odds make sense (avoid obvious value traps)
            chosen_odds = self.outcomes[odds_choice][OutcomeKeys.ODDS]
            if chosen_odds < 1.15:  # Very low odds, might be a trap
                # Fall back to a more balanced approach
                return self.__return_choice_balanced()
            return odds_choice
        else:
            # High consensus - follow the crowd but verify with smart money
            crowd_choice = self.__return_choice(OutcomeKeys.TOTAL_USERS)
            smart_choice = self.__return_choice_smart_money()
            
            # If crowd and smart money agree, high confidence
            if crowd_choice == smart_choice:
                return crowd_choice
            else:
                # Disagreement - use points as tiebreaker (middle ground)
                return self.__return_choice(OutcomeKeys.TOTAL_POINTS)

    def __return_choice_balanced(self) -> int:
        """Balanced choice when other strategies are uncertain"""
        # Score each outcome based on multiple factors
        scores = []
        for i in range(len(self.outcomes)):
            user_score = self.outcomes[i][OutcomeKeys.PERCENTAGE_USERS] / 100
            points_score = (self.outcomes[i][OutcomeKeys.TOTAL_POINTS] / self.total_points) if self.total_points > 0 else 0
            odds_score = min(self.outcomes[i][OutcomeKeys.ODDS] / 3, 1)  # Normalize odds, cap benefit
            
            # Weighted combination (favor users slightly, but consider all factors)
            combined_score = (user_score * 0.4) + (points_score * 0.3) + (odds_score * 0.3)
            scores.append(combined_score)
        
        return scores.index(max(scores))

    def __is_bet_worthwhile(self) -> bool:
        """Check if the bet meets basic quality thresholds"""
        # Skip if insufficient data
        if self.total_users < 10 or self.total_points < 100:
            return False
        
        # Skip if outcomes are too unbalanced (likely predetermined)
        if len(self.outcomes) >= 2:
            max_user_percentage = max(outcome[OutcomeKeys.PERCENTAGE_USERS] for outcome in self.outcomes)
            if max_user_percentage > 95:  # One outcome has >95% of users
                return False
        
        # Skip if all odds are too low (no value)
        if all(outcome[OutcomeKeys.ODDS] < 1.05 for outcome in self.outcomes):
            return False
            
        # Skip if chosen outcome has suspiciously low odds but high user percentage
        # (potential value trap)
        if hasattr(self, 'decision') and self.decision.get("choice") is not None:
            chosen_outcome = self.outcomes[self.decision["choice"]]
            if (chosen_outcome[OutcomeKeys.ODDS] < 1.1 and 
                chosen_outcome[OutcomeKeys.PERCENTAGE_USERS] > 80):
                return False
        
        return True

    def skip(self) -> bool:
        if self.settings.filter_condition is not None:
            # key == by , condition == where
            key = self.settings.filter_condition.by
            condition = self.settings.filter_condition.where
            value = self.settings.filter_condition.value

            fixed_key = (
                key
                if key not in [OutcomeKeys.DECISION_USERS, OutcomeKeys.DECISION_POINTS]
                else key.replace("decision", "total")
            )
            if key in [OutcomeKeys.TOTAL_USERS, OutcomeKeys.TOTAL_POINTS]:
                compared_value = (
                    self.outcomes[0][fixed_key] + self.outcomes[1][fixed_key]
                )
            else:
                #outcome_index = char_decision_as_index(self.decision["choice"])
                outcome_index = self.decision["choice"]
                compared_value = self.outcomes[outcome_index][fixed_key]

            # Check if condition is satisfied
            if condition == Condition.GT:
                if compared_value > value:
                    return False, compared_value
            elif condition == Condition.LT:
                if compared_value < value:
                    return False, compared_value
            elif condition == Condition.GTE:
                if compared_value >= value:
                    return False, compared_value
            elif condition == Condition.LTE:
                if compared_value <= value:
                    return False, compared_value
            return True, compared_value  # Else skip the bet
        else:
            return False, 0  # Default don't skip the bet

    def calculate(self, balance: int) -> dict:
        self.decision = {"choice": None, "amount": 0, "id": None}
        
        # Early exit if no valid outcomes or insufficient data
        if len(self.outcomes) < 2 or self.total_users < 10:
            return self.decision
            
        if self.settings.strategy == Strategy.MOST_VOTED:
            self.decision["choice"] = self.__return_choice(OutcomeKeys.TOTAL_USERS)
        elif self.settings.strategy == Strategy.HIGH_ODDS:
            self.decision["choice"] = self.__return_choice(OutcomeKeys.ODDS)
        elif self.settings.strategy == Strategy.PERCENTAGE:
            self.decision["choice"] = self.__return_choice(OutcomeKeys.ODDS_PERCENTAGE)
        elif self.settings.strategy == Strategy.SMART_MONEY:
            self.decision["choice"] = self.__return_choice_smart_money()
        elif self.settings.strategy == Strategy.NUMBER_1:
            self.decision["choice"] = self.__return_number_choice(0)
        elif self.settings.strategy == Strategy.NUMBER_2:
            self.decision["choice"] = self.__return_number_choice(1)
        elif self.settings.strategy == Strategy.NUMBER_3:
            self.decision["choice"] = self.__return_number_choice(2)
        elif self.settings.strategy == Strategy.NUMBER_4:
            self.decision["choice"] = self.__return_number_choice(3)
        elif self.settings.strategy == Strategy.NUMBER_5:
            self.decision["choice"] = self.__return_number_choice(4)
        elif self.settings.strategy == Strategy.NUMBER_6:
            self.decision["choice"] = self.__return_number_choice(5)
        elif self.settings.strategy == Strategy.NUMBER_7:
            self.decision["choice"] = self.__return_number_choice(6)
        elif self.settings.strategy == Strategy.NUMBER_8:
            self.decision["choice"] = self.__return_number_choice(7)
        elif self.settings.strategy == Strategy.SMART:
            self.decision["choice"] = self.__return_choice_smart()

        # Additional validation - skip bet if it doesn't meet quality thresholds
        if self.decision["choice"] is not None and not self.__is_bet_worthwhile():
            self.decision = {"choice": None, "amount": 0, "id": None}
            return self.decision

        if self.decision["choice"] is not None:
            index = self.decision["choice"]
            self.decision["id"] = self.outcomes[index]["id"]
            self.decision["amount"] = min(
                int(balance * (self.settings.percentage / 100)),
                self.settings.max_points,
            )
            if (
                self.settings.stealth_mode is True
                and self.decision["amount"]
                >= self.outcomes[index][OutcomeKeys.TOP_POINTS]
                and self.outcomes[index][OutcomeKeys.TOP_POINTS] > 0
            ):
                # Improved stealth mode: reduce by 3-7% of top bet or 1-10 points, whichever is larger
                top_points = self.outcomes[index][OutcomeKeys.TOP_POINTS]
                percentage_reduction = uniform(0.03, 0.07)
                points_reduction = uniform(1, 10)
                reduce_amount = max(top_points * percentage_reduction, points_reduction)
                
                self.decision["amount"] = max(
                    int(top_points - reduce_amount),
                    10  # Minimum bet amount
                )
            self.decision["amount"] = int(self.decision["amount"])
        return self.decision
