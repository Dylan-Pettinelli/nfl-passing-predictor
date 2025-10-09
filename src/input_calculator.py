#input_calculator.py
import pandas as pd
import numpy as np
import joblib
from src.config import PROPS_CONFIG
from src.feature_engineer import get_features_list

def get_matchup_inputs(prop_name, player_name, posteam, defteam, season=2025, prediction_week=4, max_games=4):
    """
    Enhanced to include WR stats from player's team and validate minimum game count
    """
    config = PROPS_CONFIG[prop_name]
    min_games = config.get('min_games', 10)
    
    try:
        player_df = pd.read_csv(f"data/{config['target_stat']}_player_logs.csv")
        team_df = pd.read_csv("data/team_offense_logs.csv")
        def_df = pd.read_csv("data/defense_logs.csv")
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV files for {prop_name} not found. Run train_pipeline first.")
    
    # Validate player has sufficient historical data
    player_history = player_df[
        (player_df['player_name'] == player_name) & 
        ((player_df['season'] < season) | 
         ((player_df['season'] == season) & (player_df['week'] < prediction_week)))
    ]
    
    game_count = len(player_history)
    if game_count < min_games:
        raise ValueError(
            f"Insufficient data for {player_name}: only {game_count} games found before Week {prediction_week} of {season}. "
            f"Minimum required: {min_games} games. "
            f"Cannot generate reliable prediction."
        )
    
    # Fetch player data with WR stats already included
    player_data = player_df[
        (player_df['player_name'] == player_name) & 
        (player_df['season'] == season) & 
        (player_df['week'] < prediction_week)
    ].sort_values(['season', 'week'], ascending=False).head(max_games)
    
    # Extend to prior seasons if needed
    if len(player_data) < max_games:
        for prior_season in [season - 1, season - 2]:
            extra_data = player_df[
                (player_df['player_name'] == player_name) & 
                (player_df['season'] == prior_season)
            ].sort_values('week', ascending=False).head(max_games - len(player_data))
            player_data = pd.concat([player_data, extra_data]).sort_values(['season', 'week'], ascending=False).head(max_games)
            if len(player_data) >= max_games:
                break
    
    if len(player_data) < 1:
        raise ValueError(f"No data for {player_name} in season {season} or fallbacks.")
    
    # Player numeric cols (including WR stats if present)
    player_numeric_cols = list(config['offense_agg_cols'].keys()) + ['is_home', 'score_diff']
    
    # Add WR columns if they exist
    wr_cols = [col for col in player_data.columns if col.startswith('wr_')]
    if wr_cols:
        player_numeric_cols += wr_cols
        print(f"Including {len(wr_cols)} WR stat columns")
    
    player_data = player_data.copy()
    for col in player_numeric_cols + [config['target_stat']]:
        if col in player_data.columns:
            player_data[col] = pd.to_numeric(player_data[col], errors='coerce')
        else:
            player_data[col] = 0
    
    player_data[player_numeric_cols] = player_data[player_numeric_cols].fillna(player_data[player_numeric_cols].median())
    player_recent = player_data[player_numeric_cols].mean().to_dict()
    print(f"{player_name} data: {len(player_data)} games")
    
    # Team offense data
    team_data = team_df[
        (team_df['posteam'] == posteam) & 
        (team_df['season'].isin(player_data['season'].unique())) & 
        (team_df['week'].isin(player_data['week'].unique()))
    ]
    if len(team_data) < 1:
        team_data = team_df.copy().head(max_games)
    
    team_cols = list(config['team_offense_agg_cols'].keys())
    team_data = team_data.copy()
    for col in team_cols:
        if col in team_data.columns:
            team_data[col] = pd.to_numeric(team_data[col], errors='coerce')
        else:
            team_data[col] = 0
    team_data[team_cols] = team_data[team_cols].fillna(team_data[team_cols].median())
    team_recent = team_data[team_cols].mean().to_dict()
    
    # Defense data
    def_data = def_df[
        (def_df['defteam'] == defteam) & 
        (def_df['season'].isin(player_data['season'].unique())) & 
        (def_df['week'].isin(player_data['week'].unique()))
    ].copy()
    if len(def_data) < 1:
        def_data = def_df.copy().head(max_games)
    
    def_cols = list(config['defense_agg_cols'].keys())
    for col in def_cols:
        if col in def_data.columns:
            def_data[col] = pd.to_numeric(def_data[col], errors='coerce')
        else:
            def_data[col] = 0
    def_data[def_cols] = def_data[def_cols].fillna(def_data[def_cols].median())
    def_recent = def_data[def_cols].mean().to_dict()
    
    return player_recent, team_recent, def_recent

def prepare_input(prop_name, player_recent, team_recent, def_recent, is_home=0, week=4):
    """
    Enhanced with week-based features
    """
    config = PROPS_CONFIG[prop_name]
    lag_window = config['lag_window']
    selected_features = joblib.load(f'models/{prop_name}_features.pkl')
    scaler = joblib.load(f'models/{prop_name}_scaler.pkl')
    selector = joblib.load(f'models/{prop_name}_selector.pkl')
    
    # Build input DataFrame (no lag2 features)
    input_data = pd.DataFrame([{
        **{f"{k}_lag{lag_window}": v for k, v in player_recent.items()},
        **{f"{k}_lag{lag_window}": v for k, v in team_recent.items()},
        **{f"{k}_lag{lag_window}": v for k, v in def_recent.items()},
        f"is_home_lag{lag_window}": is_home,
        'week_of_season': week,
        'season_phase_encoded': 0 if week <= 6 else (1 if week <= 12 else 2)
    }])
    
    # REMOVED: lag_window_recent features
    
    # Add interaction features
    for col1, col2 in config['interaction_features']:
        lag1 = f"{col1}_lag{lag_window}"
        lag2 = f"{col2}_lag{lag_window}"
        if lag1 in input_data.columns and lag2 in input_data.columns:
            input_data[f'{col1}_{col2}_interaction'] = input_data[lag1] * input_data[lag2]
    
    # Ensure all features present
    all_features = get_features_list(config, lag_window)
    for col in all_features:
        if col not in input_data.columns:
            input_data[col] = 0
    
    input_data[all_features] = input_data[all_features].fillna(0)
    
    # Scale and select
    input_scaled = scaler.transform(input_data[all_features])
    input_selected = selector.transform(input_scaled)
    
    return input_selected