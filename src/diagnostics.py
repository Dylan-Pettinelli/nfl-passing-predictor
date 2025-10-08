# diagnostics.py
# Analyze model performance to identify improvement areas

import pandas as pd
import numpy as np
from pathlib import Path

def load_all_weeks(file_path='data/passing-prop-predictions-2025.xlsx'):
    """Load all week sheets and combine them"""
    all_data = []
    xl = pd.ExcelFile(file_path)
    
    for sheet in xl.sheet_names:
        if sheet.startswith('Week'):
            df = pd.read_excel(file_path, sheet_name=sheet)
            print(f"Sheet {sheet} columns: {list(df.columns)}")  # Debug: Print columns
            # Only include rows with valid Actual values
            df = df[df['Actual'].notna() & (df['Actual'] != '')]
            if len(df) > 0:
                # Check for Win.Loss column (standardized)
                if 'Win.Loss' not in df.columns:
                    print(f"Error: 'Win.Loss' column not found in sheet {sheet}. Available columns: {list(df.columns)}")
                    return None
                # Convert Win.Loss to string and strip whitespace
                df['WL'] = df['Win.Loss'].astype(str).str.strip()
                # Replace empty or 'nan' strings with 'Unknown'
                df['WL'] = df['WL'].replace(['', 'nan'], 'Unknown')
                # Drop original Win.Loss column
                df = df.drop(columns=['Win.Loss'])
                all_data.append(df)
            else:
                print(f"Warning: No valid data in sheet {sheet} (empty or no valid Actual values)")
    
    if not all_data:
        print("No completed predictions found!")
        return None
    
    combined = pd.concat(all_data, ignore_index=True)
    print(f"Combined DataFrame shape: {combined.shape}")  # Debug: Print shape
    print(f"Combined columns: {list(combined.columns)}")  # Debug: Print columns
    
    # Clean data types
    combined['Mean.Pred'] = pd.to_numeric(combined['Mean.Pred'], errors='coerce')
    combined['Vegas.Line'] = pd.to_numeric(combined['Vegas.Line'], errors='coerce')
    combined['Actual'] = pd.to_numeric(combined['Actual'], errors='coerce')
    
    # Rename for easier access
    combined = combined.rename(columns={
        'Mean.Pred': 'Mean Pred',
        'Vegas.Line': 'Vegas Line',
        'Home/Away': 'Home_Away',
        'Prob.Over': 'Prob Over'
    })
    
    # Ensure WL is clean
    print(f"WL column unique values: {combined['WL'].unique()}")  # Debug: Print unique WL values
    print(f"NaNs in WL column: {combined['WL'].isna().sum()}")  # Debug: Count NaNs in WL
    
    # Warn if unexpected WL values (not 'W' or 'L')
    valid_wl_values = {'W', 'L'}
    invalid_wl = combined[~combined['WL'].isin(valid_wl_values)]['WL'].unique()
    if len(invalid_wl) > 0:
        print(f"Warning: Invalid WL values found: {invalid_wl}")
        # Ensure invalid values are marked as 'Unknown'
        combined['WL'] = combined['WL'].replace(invalid_wl, 'Unknown')
    
    # Treat 'Unknown' as NaN for stats
    combined['WL'] = combined['WL'].replace('Unknown', np.nan)
    
    return combined

def analyze_predictions(df):
    """Comprehensive analysis of prediction performance"""
    
    print("="*60)
    print("MODEL PERFORMANCE DIAGNOSTICS")
    print("="*60)
    
    # Overall stats (only count W and L for win rate)
    total = len(df)
    wins = (df['WL'] == 'W').sum()
    losses = (df['WL'] == 'L').sum()
    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    
    print(f"\nOVERALL RECORD: {wins}-{losses} ({win_rate:.1f}%)")
    print(f"Total predictions: {total}")
    
    # Prediction accuracy
    df['prediction_error'] = df['Mean Pred'] - df['Actual']
    df['abs_error'] = abs(df['prediction_error'])
    df['pct_error'] = (df['abs_error'] / df['Actual'] * 100)
    
    print(f"\nPREDICTION ACCURACY:")
    print(f"  Mean Absolute Error (MAE): {df['abs_error'].mean():.1f} yards")
    print(f"  Median Absolute Error: {df['abs_error'].median():.1f} yards")
    print(f"  Mean % Error: {df['pct_error'].mean():.1f}%")
    print(f"  Std Dev of Errors: {df['prediction_error'].std():.1f} yards")
    
    # Bias analysis
    mean_error = df['prediction_error'].mean()
    if abs(mean_error) > 5:
        bias_direction = "OVERESTIMATING" if mean_error > 0 else "UNDERESTIMATING"
        print(f"\n⚠ MODEL BIAS DETECTED: {bias_direction} by {abs(mean_error):.1f} yards on average")
    
    # Over vs Under performance
    over_bets = df[df['Lean'] == 'OVER']
    under_bets = df[df['Lean'] == 'UNDER']
    
    print(f"\nOVER BETS: {len(over_bets)} total")
    if len(over_bets) > 0:
        over_wins = (over_bets['WL'] == 'W').sum()
        print(f"  Record: {over_wins}-{len(over_bets)-over_wins} ({over_wins/len(over_bets)*100:.1f}%)")
        print(f"  Avg prediction error: {over_bets['prediction_error'].mean():.1f} yards")
    
    print(f"\nUNDER BETS: {len(under_bets)} total")
    if len(under_bets) > 0:
        under_wins = (under_bets['WL'] == 'W').sum()
        print(f"  Record: {under_wins}-{len(under_bets)-under_wins} ({under_wins/len(under_bets)*100:.1f}%)")
        print(f"  Avg prediction error: {under_bets['prediction_error'].mean():.1f} yards")
    
    # Home vs Away
    home_games = df[df['Home_Away'] == 'Home']
    away_games = df[df['Home_Away'] == 'Away']
    
    print(f"\nHOME GAMES: {len(home_games)} total")
    if len(home_games) > 0:
        home_wins = (home_games['WL'] == 'W').sum()
        print(f"  Record: {home_wins}-{len(home_games)-home_wins} ({home_wins/len(home_games)*100:.1f}%)")
    
    print(f"\nAWAY GAMES: {len(away_games)} total")
    if len(away_games) > 0:
        away_wins = (away_games['WL'] == 'W').sum()
        print(f"  Record: {away_wins}-{len(away_games)-away_wins} ({away_wins/len(away_games)*100:.1f}%)")
    
    # Close lines analysis (within 10 yards of line)
    df['line_distance'] = abs(df['Mean Pred'] - df['Vegas Line'])
    close_lines = df[df['line_distance'] <= 10]
    far_lines = df[df['line_distance'] > 10]
    
    print(f"\nCLOSE TO LINE (≤10 yards difference):")
    print(f"  Total: {len(close_lines)}")
    if len(close_lines) > 0:
        close_wins = (close_lines['WL'] == 'W').sum()
        print(f"  Record: {close_wins}-{len(close_lines)-close_wins} ({close_wins/len(close_lines)*100:.1f}%)")
        print(f"  → Maybe avoid betting close lines")
    
    print(f"\nFAR FROM LINE (>10 yards difference):")
    print(f"  Total: {len(far_lines)}")
    if len(far_lines) > 0:
        far_wins = (far_lines['WL'] == 'W').sum()
        print(f"  Record: {far_wins}-{len(far_lines)-far_wins} ({far_wins/len(far_lines)*100:.1f}%)")
    
    # Worst performers
    print(f"\nWORST PREDICTIONS (biggest errors):")
    worst = df.nlargest(5, 'abs_error')[['Player', 'Team', 'Mean Pred', 'Actual', 'abs_error', 'Lean', 'WL']]
    print(worst.to_string(index=False))
    
    # Best performers
    print(f"\nBEST PREDICTIONS (smallest errors):")
    best = df.nsmallest(5, 'abs_error')[['Player', 'Team', 'Mean Pred', 'Actual', 'abs_error', 'Lean', 'WL']]
    print(best.to_string(index=False))
    
    return df

def main():
    df = load_all_weeks()
    
    if df is None:
        return
    
    df = analyze_predictions(df)
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    
    # Generate recommendations based on analysis
    if df['prediction_error'].mean() > 10:
        print("1. Model is significantly overestimating - consider adjusting down")
    elif df['prediction_error'].mean() < -10:
        print("1. Model is significantly underestimating - consider adjusting up")
    
    over_win_rate = (df[df['Lean'] == 'OVER']['WL'] == 'W').mean() * 100 if len(df[df['Lean'] == 'OVER']) > 0 else 0
    under_win_rate = (df[df['Lean'] == 'UNDER']['WL'] == 'W').mean() * 100 if len(df[df['Lean'] == 'UNDER']) > 0 else 0
    
    if abs(over_win_rate - under_win_rate) > 15:
        print(f"2. Big imbalance: OVER {over_win_rate:.1f}% vs UNDER {under_win_rate:.1f}%")
        print("   → Consider only betting the better-performing direction")
    
    close_lines = df[df['line_distance'] <= 10]
    if len(close_lines) > 0:
        close_win_rate = (close_lines['WL'] == 'W').mean() * 100
        if close_win_rate < 45:
            print(f"3. Avoid close lines (≤10 yards): only {close_win_rate:.1f}% win rate")
    
    print("\n4. Next steps to improve:")
    print("   - Add more features (weather, injuries, opponent strength)")
    print("   - Tune the probability threshold (currently using mean prediction)")
    print("   - Consider recent form more heavily")
    print("   - Add situational adjustments (division games, primetime, etc.)")

if __name__ == "__main__":
    main()