# predictor.py
# Generic prediction

import joblib
import numpy as np
import os
from src.input_calculator import get_matchup_inputs, prepare_input
from src.config import PROPS_CONFIG

def predict_prop(prop_name, player_name, posteam, defteam, line, season, prediction_week, is_home=0, n_sims=10000):
    """
    Predict prop outcome and probability over line
    """
    config = PROPS_CONFIG[prop_name]
    model = joblib.load(f'models/{prop_name}_model.pkl')
    mae = joblib.load(f'models/{prop_name}_mae.pkl') if os.path.exists(f'models/{prop_name}_mae.pkl') else 50.0
    
    player_r, team_r, def_r = get_matchup_inputs(prop_name, player_name, posteam, defteam, season, prediction_week)
    
    # Debug: Check for NaNs in input data
    print("Player data sample:", player_r)
    print("Team data sample:", team_r)
    print("Defense data sample:", def_r)
    
    input_scaled = prepare_input(prop_name, player_r, team_r, def_r, is_home)
    
    # Check for NaNs in input_scaled
    if np.isnan(input_scaled).any():
        raise ValueError(f"NaNs found in input_scaled: {np.isnan(input_scaled).sum()}")
    
    mean_pred = model.predict(input_scaled)[0]
    sims = np.random.normal(mean_pred, mae, n_sims)
    sims = np.maximum(sims, 0)
    prob_over = np.mean(sims > line)
    
    return {
        'prop_name': prop_name,
        'player_name': player_name,
        'mean_prediction': mean_pred,
        'p10': np.percentile(sims, 10),
        'p50': np.percentile(sims, 50),
        'p90': np.percentile(sims, 90),
        'line': line,
        'prob_over_line': prob_over,
        'posteam': posteam,
        'defteam': defteam
    }