# src/model_trainer.py
# Train model based on config

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_regression
import xgboost as xgb
import joblib
import warnings
from src.feature_engineer import get_features_list
from src.config import PROPS_CONFIG

warnings.filterwarnings('ignore')

def train_model(prop_name, model_data, config):
    """
    Train and save model for given prop
    """
    target_stat = config['target_stat']
    features = get_features_list(config, config['lag_window'])
    
    # Check for NaNs in features and target
    print("NaNs in features before dropna:\n", model_data[features].isna().sum())
    model_data = model_data.dropna(subset=features + [target_stat]).reset_index(drop=True)
    print(f"Final dataset for {prop_name} shape: {model_data.shape}, Features: {len(features)}")
    
    # Verify no NaNs remain
    if model_data[features].isna().any().any():
        raise ValueError(f"NaNs found in feature columns: {model_data[features].isna().sum()}")
    
    # Debug rushing features
    print("Rushing Feature Summary:")
    rushing_cols = ['qb_rush_attempts', 'qb_rush_yds', 
                    'team_rush_attempts', 'team_rush_yds']
    available_rushing_cols = [col for col in rushing_cols if col in model_data.columns]
    if available_rushing_cols:
        print(model_data[available_rushing_cols].describe())
    
    # Scale and select features
    scaler = StandardScaler()
    X = scaler.fit_transform(model_data[features])
    X = pd.DataFrame(X, columns=features)
    
    # Check for NaNs after scaling
    if np.isnan(X).any().any():
        raise ValueError(f"NaNs found in X after scaling: {pd.DataFrame(X, columns=features).isna().sum()}")
    
    y = model_data[target_stat]
    selector = SelectKBest(score_func=f_regression, k=min(25, len(features)))
    X_selected = selector.fit_transform(X, y)
    selected_features = [features[i] for i in selector.get_support(indices=True)]
    print(f"Selected {len(selected_features)} features: {selected_features}")
    
    # Train/test split
    train_mask = model_data['season'] <= 2023
    X_train, y_train = X_selected[train_mask], y[train_mask]
    X_test, y_test = X_selected[~train_mask], y[~train_mask]
    print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    
    # New: Sample weights - weight recent seasons (2021+) 2x
    sample_weight = np.where(model_data.loc[train_mask, 'season'] >= 2021, 2, 1)
    
    # Train model
    model_type = config['model_params']['model_type']
    param_grid = config['model_params']['param_grid']
    
    if model_type == 'xgboost':
        model = GridSearchCV(
            xgb.XGBRegressor(random_state=42, objective='reg:squarederror', early_stopping_rounds=10),
            param_grid, cv=3, scoring='neg_mean_absolute_error', n_jobs=-1
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False, sample_weight=sample_weight)
        print(f"Best {prop_name} params: {model.best_params_}")
    
    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"{prop_name} Test MAE: {mae:.2f} | RMSE: {rmse:.2f}")
    
    # Feature importance
    print("Feature Importance:")
    importance = model.best_estimator_.get_booster().get_score(importance_type='gain')
    for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
        print(f"{feature}: {score:.4f}")
    
    # Save model and components
    joblib.dump(model.best_estimator_, f'models/{prop_name}_model.pkl')
    joblib.dump(selected_features, f'models/{prop_name}_features.pkl')
    joblib.dump(scaler, f'models/{prop_name}_scaler.pkl')
    joblib.dump(selector, f'models/{prop_name}_selector.pkl')
    
    return model, mae, selected_features, scaler, selector