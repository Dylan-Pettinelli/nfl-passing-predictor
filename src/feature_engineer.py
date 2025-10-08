import pandas as pd
import numpy as np
from src.config import PROPS_CONFIG

def engineer_features(model_data, config, lag_window=4):
    """
    Simplified feature engineering with new Vegas/weather/RB features, no lag2 overfitting
    """
    print("Columns in model_data:", list(model_data.columns))
    
    if 'defteam' not in model_data.columns:
        raise KeyError("'defteam' not in model_data.columns after merge")
    
    # Sort for lags
    model_data = model_data.sort_values(['player_name', 'season', 'week']).reset_index(drop=True)
    
    # Filter min games
    player_counts = model_data.groupby('player_name').size()
    model_data = model_data[model_data['player_name'].isin(player_counts[player_counts >= config['min_games']].index)]
    print(f"Filtered to players with >= {config['min_games']} games. Shape: {model_data.shape}")
    
    # Fill NAs with medians
    numeric_cols = model_data.select_dtypes(include=np.number).columns
    model_data[numeric_cols] = model_data[numeric_cols].fillna(model_data[numeric_cols].median())
    
    # Player lags (standard 4-game window only)
    player_numeric_cols = list(config['offense_agg_cols'].keys()) + ['is_home', 'score_diff']
    player_lags = model_data.groupby('player_name')[player_numeric_cols].transform(
        lambda g: g.shift(1).rolling(lag_window, min_periods=1).mean()
    ).add_suffix(f'_lag{lag_window}')
    model_data = pd.concat([model_data, player_lags], axis=1)
    
    # Team lags
    team_numeric_cols = list(config['team_offense_agg_cols'].keys())
    team_lags = model_data.groupby('posteam')[team_numeric_cols].transform(
        lambda g: g.shift(1).rolling(lag_window, min_periods=1).mean()
    ).add_suffix(f'_lag{lag_window}')
    model_data = pd.concat([model_data, team_lags], axis=1)
    
    # Defense lags
    def_numeric_cols = list(config['defense_agg_cols'].keys())
    def_lags = model_data.groupby('defteam')[def_numeric_cols].transform(
        lambda g: g.shift(1).rolling(lag_window, min_periods=1).mean()
    ).add_suffix(f'_lag{lag_window}')
    model_data = pd.concat([model_data, def_lags], axis=1)
    
    # New: Roof encoding (if 'roof_type' column exists from aggregator)
    if 'roof_type' in model_data.columns:
        model_data['roof_encoded'] = model_data['roof_type'].map({'dome': 1, 'outdoors': 0, 'retractable': 0.5}).fillna(0)
    
    # Fill NaNs in all lag columns
    lag_cols = [col for col in model_data.columns if 'lag' in col]
    model_data[lag_cols] = model_data[lag_cols].fillna(model_data[lag_cols].median())
    
    # Interaction features
    for col1, col2 in config['interaction_features']:
        lag1 = f"{col1}_lag{lag_window}"
        lag2 = f"{col2}_lag{lag_window}"
        if lag1 in model_data.columns and lag2 in model_data.columns:
            model_data[f'{col1}_{col2}_interaction'] = model_data[lag1] * model_data[lag2]
    
    # Additional computed features
    model_data['week_of_season'] = model_data['week']
    model_data['season_phase'] = model_data['week'].apply(lambda w: 'early' if w <= 6 else ('mid' if w <= 12 else 'late'))
    model_data['season_phase_encoded'] = model_data['season_phase'].map({'early': 0, 'mid': 1, 'late': 2})
    
    # Final NaN fill
    feature_cols = get_features_list(config, lag_window)
    model_data[feature_cols] = model_data[feature_cols].fillna(model_data[feature_cols].median())
    
    # REMOVED: Data duplication for recent seasons (caused overfitting)
    # Instead, use sample weights in training for recent data
    
    # Filter min attempts
    min_att_col = list(config['offense_agg_cols'].keys())[0]
    model_data = model_data[model_data[min_att_col] >= config['min_attempts']]
    print(f"Filtered games with < {config['min_attempts']} {min_att_col}. Shape: {model_data.shape}")
    
    return model_data

def get_features_list(config, lag_window=4):
    """Generate list of lag features + interactions (no lag2)"""
    player_lags = [f"{col}_lag{lag_window}" for col in config['offense_agg_cols'].keys()] + \
                  [f"{col}_lag{lag_window}" for col in ['is_home', 'score_diff']]
    
    team_lags = [f"{col}_lag{lag_window}" for col in config['team_offense_agg_cols'].keys()]
    def_lags = [f"{col}_lag{lag_window}" for col in config['defense_agg_cols'].keys()]
    
    interactions = [f"{c1}_{c2}_interaction" for c1, c2 in config['interaction_features']]
    
    # Add computed features
    additional = ['week_of_season', 'season_phase_encoded', 'roof_encoded']
    
    return player_lags + team_lags + def_lags + interactions + additional