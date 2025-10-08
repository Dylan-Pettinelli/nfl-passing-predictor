# config.py
# Simplified configuration - fewer features, better performance
# Removed WR stats (added noise); added Vegas, weather, RB share features

PROPS_CONFIG = {
    'qb_passing_yards': {
        'target_player_field': 'passer_player_name',
        'target_stat': 'passing_yards',
        'play_filter': 'pass == 1',
        'offense_agg_cols': {
            'pass_attempts': 'sum(pass, na.rm = TRUE)',
            'completions': 'sum(complete_pass, na.rm = TRUE)',
            'passing_yards': 'sum(passing_yards, na.rm = TRUE)',
            'pass_tds': 'sum(pass_touchdown, na.rm = TRUE)',
            'ints': 'sum(interception, na.rm = TRUE)',
            'air_yards': 'sum(air_yards, na.rm = TRUE)',
            'ypa': 'ifelse(sum(pass, na.rm = TRUE) > 0, sum(passing_yards, na.rm = TRUE) / sum(pass, na.rm = TRUE), 0)',
            'cpoe': 'mean(cpoe[pass == 1], na.rm = TRUE)',
            'epa_per_pass': 'ifelse(sum(pass, na.rm = TRUE) > 0, sum(epa[pass == 1], na.rm = TRUE) / sum(pass, na.rm = TRUE), 0)',
            'yac_epa': 'sum(yac_epa, na.rm = TRUE)',
            'xyac_epa': 'sum(xyac_epa, na.rm = TRUE)',
            'wpa': 'sum(wpa, na.rm = TRUE)',
            'qb_rush_attempts': 'sum(rush[passer_player_name == rusher_player_name], na.rm = TRUE)',
            'qb_rush_yds': 'sum(rushing_yards[passer_player_name == rusher_player_name], na.rm = TRUE)',
            'completion_pct': 'ifelse(sum(pass, na.rm = TRUE) > 0, sum(complete_pass, na.rm = TRUE) / sum(pass, na.rm = TRUE), 0)',
            'deep_completions': 'sum(complete_pass == 1 & air_yards > 20, na.rm = TRUE)',
            # New: Vegas and weather (aggregated in data_aggregator.R)
            'expected_spread': 'mean(spread_line, na.rm = TRUE)',
            'expected_total': 'mean(total_line, na.rm = TRUE)',
            'avg_temp': 'mean(temp, na.rm = TRUE)',
            'avg_wind': 'mean(wind, na.rm = TRUE)',
        },
        'team_offense_agg_cols': {
            'team_targets': 'n()',
            'team_receptions': 'sum(complete_pass, na.rm = TRUE)',
            'team_rec_yds': 'sum(receiving_yards, na.rm = TRUE)',
            'team_yac_epa': 'sum(yac_epa, na.rm = TRUE)',
            'team_rush_attempts': 'sum(rush, na.rm = TRUE)',
            'team_rush_yds': 'sum(rushing_yards, na.rm = TRUE)',
            # New: RB rush share (non-QB rushes)
            'rb_rush_share': 'ifelse(sum(rush, na.rm = TRUE) > 0, sum(rushing_yards[rusher_player_name != passer_player_name], na.rm = TRUE) / sum(rushing_yards, na.rm = TRUE), 0)',
        },
        'defense_agg_cols': {
            'pass_att_allowed': 'sum(pass, na.rm = TRUE)',
            'comp_allowed': 'sum(complete_pass, na.rm = TRUE)',
            'pass_yds_allowed': 'sum(passing_yards, na.rm = TRUE)',
            'pass_tds_allowed': 'sum(pass_touchdown, na.rm = TRUE)',
            'ints_forced': 'sum(interception, na.rm = TRUE)',
            'sacks': 'sum(sack, na.rm = TRUE)',
            'def_comp_air_epa': 'ifelse(sum(complete_pass, na.rm = TRUE) > 0, sum(comp_air_epa, na.rm = TRUE) / sum(complete_pass, na.rm = TRUE), 0)',
            'qb_hits': 'sum(qb_hit, na.rm = TRUE)',
            'rush_yds_allowed': 'sum(rushing_yards, na.rm = TRUE)',
            'def_ypa_allowed': 'ifelse(sum(pass, na.rm = TRUE) > 0, sum(passing_yards, na.rm = TRUE) / sum(pass, na.rm = TRUE), 0)',
        },
        'lag_window': 4,
        # REMOVED: lag_window_recent (this was causing overfitting)
        'min_games': 10,  # Back to 10 for more data quality
        'min_attempts': 10,
        'interaction_features': [
            # Keep only best interactions (removed WR ones)
            ('completions', 'pass_yds_allowed'),
            ('epa_per_pass', 'sacks'),
            ('ypa', 'def_comp_air_epa'),
            ('completion_pct', 'def_ypa_allowed'),
            # New: Interactions with added features
            ('expected_total', 'pass_yds_allowed'),  # High-total games vs weak defense
            ('avg_wind', 'air_yards'),  # Wind impacts deep balls
            ('rb_rush_share', 'pass_attempts'),  # High RB share → fewer passes
        ],
        'model_params': {
            'model_type': 'xgboost',
            'param_grid': {
                'n_estimators': [300, 400, 500],  # Added more for better fitting
                'max_depth': [3, 4, 5, 6],        # Slightly deeper to capture patterns
                'learning_rate': [0.01, 0.02, 0.03],  # Lower for stability
                'subsample': [0.8, 0.9],
                'colsample_bytree': [0.7, 0.8],
                'min_child_weight': [3, 5],
                'gamma': [0.1, 0.2],
            }
        }
    },
}