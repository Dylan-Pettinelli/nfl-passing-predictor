# src/train_pipeline.py
# Train models for specified props

import pandas as pd
import joblib
import subprocess
import os
import json
from src.config import PROPS_CONFIG
from src.feature_engineer import engineer_features, get_features_list
from src.model_trainer import train_model


def run_r_aggregation(prop_name, seasons=range(2006, 2026), max_week_2025=6):
    """
    Run R data aggregation for a prop, limiting 2025 to max_week_2025
    """
    r_script_path = os.path.join(os.path.dirname(__file__), 'data_aggregator.R')
    json_config_path = os.path.join(os.path.dirname(__file__), '..', 'models', f'{prop_name}_config.json')
    if not os.path.exists(r_script_path):
        raise FileNotFoundError(f"data_aggregator.R not found in {r_script_path}.")

    # Convert paths to use forward slashes for R compatibility
    r_script_path = r_script_path.replace('\\', '/')
    json_config_path = json_config_path.replace('\\', '/')

    # Format seasons as R vector
    seasons_r = f"c({','.join(map(str, seasons))})"
    r_script = f"""
    library(conflicted)
    conflict_prefer("filter", "dplyr")
    conflict_prefer("lag", "dplyr")
    conflict_prefer("flatten", "purrr")
    source('{r_script_path}')
    library(jsonlite)
    library(nflfastR)
    library(tidyverse)
    config <- fromJSON('{json_config_path}')
    output_dir <- 'data'
    original_aggregate_data <- aggregate_data
    aggregate_data <- function(config, pbp, output_dir) {{
        pbp <- pbp %>% filter(season < 2025 | (season == 2025 & week <= {max_week_2025}))
        original_aggregate_data(config, pbp, output_dir)
    }}
    pbp <- load_pbp({seasons_r})
    aggregate_data(config, pbp, output_dir)
    """
    temp_r_script = f'models/{prop_name}_temp_r_script.R'
    try:
        with open(temp_r_script, 'w') as f:
            f.write(r_script)
        result = subprocess.run(['Rscript', temp_r_script], capture_output=True, text=True, check=True)
        print(f"R script output for {prop_name}:\n{result.stdout}")
        if result.stderr:
            print(f"R script warnings/errors for {prop_name}:\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"Error running R script for {prop_name}:\n{e.stderr}")
        raise RuntimeError(f"R script failed for {prop_name}. Check R installation, nflfastR, stringr, and data_aggregator.R.")
    finally:
        if os.path.exists(temp_r_script):
            os.remove(temp_r_script)
        if os.path.exists(f'models/{prop_name}_config.json'):
            os.remove(f'models/{prop_name}_config.json')


def save_config_json(prop_name):
    """
    Save config as JSON for R
    """
    config = PROPS_CONFIG[prop_name]
    with open(f'models/{prop_name}_config.json', 'w') as f:
        json.dump(config, f)


def train_prop(prop_name):
    """
    Full training pipeline for a prop
    """
    # Save config as JSON and run R aggregation
    print(f"Starting training for {prop_name}...")
    save_config_json(prop_name)
    run_r_aggregation(prop_name)

    # Check if CSV files were created
    config = PROPS_CONFIG[prop_name]
    player_csv = f"data/{config['target_stat']}_player_logs.csv"
    team_csv = "data/team_offense_logs.csv"
    def_csv = "data/defense_logs.csv"
    wr_csv = "data/wr_logs.csv"
    for csv_file in [player_csv, team_csv, def_csv, wr_csv]:
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file {csv_file} not found. Data aggregation failed.")

    # Load data
    player_data = pd.read_csv(player_csv)
    team_data = pd.read_csv(team_csv)
    def_data = pd.read_csv(def_csv)
    wr_data = pd.read_csv(wr_csv)

    # Debug: Print columns
    print("Player data columns:", list(player_data.columns))
    print("Team data columns:", list(team_data.columns))
    print("Def data columns:", list(def_data.columns))
    print("WR data columns:", list(wr_data.columns))

    # Merge data with suffixes to avoid column conflicts
    merge_keys = ['game_id', 'season', 'week', 'posteam', 'defteam']
    model_data = player_data.merge(
        team_data, on=merge_keys, how='left', suffixes=('', '_team')
    ).merge(
        def_data, on=merge_keys, how='left', suffixes=('', '_def')
    )

    # Handle possible suffix for defteam if conflict
    if 'defteam' not in model_data.columns:
        if 'defteam_def' in model_data.columns:
            model_data['defteam'] = model_data['defteam_def']
        elif 'defteam_team' in model_data.columns:
            model_data['defteam'] = model_data['defteam_team']
        else:
            raise KeyError("'defteam' not found after merge. Check CSV columns.")

    # ✅ WR team stats are already in player_data from R, no need to merge wr_data again
    print(f"After merging team/defense data shape: {model_data.shape}")
    print("wr_team_* columns available:", [c for c in model_data.columns if c.startswith("wr_team_")])

    # Engineer features
    try:
        model_data = engineer_features(model_data, config)
    except Exception as e:
        raise RuntimeError(f"Feature engineering failed: {str(e)}")

    # Train model
    model, mae, selected_features, scaler, selector = train_model(prop_name, model_data, config)

    # Save MAE
    joblib.dump(mae, f'models/{prop_name}_mae.pkl')

    print(f"Completed training for {prop_name}")


if __name__ == "__main__":
    for prop in ['qb_passing_yards']:
        try:
            train_prop(prop)
        except Exception as e:
            print(f"Failed to train {prop}: {str(e)}")
