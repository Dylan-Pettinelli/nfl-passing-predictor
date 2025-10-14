# diagnostics.py
# Enhanced analysis of NFL passing yards prediction model performance

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

def load_all_weeks(file_path='data/passing-prop-predictions-2025.xlsx'):
    """Load all week sheets and combine them with enhanced error handling"""
    all_data = []
    xl = pd.ExcelFile(file_path)
    
    print("="*60)
    print("LOADING DATA")
    print("="*60)
    
    for sheet in xl.sheet_names:
        if sheet.startswith('Week'):
            df = pd.read_excel(file_path, sheet_name=sheet)
            
            # Only include rows with valid Actual values
            df_complete = df[df['Actual'].notna() & (df['Actual'] != '')].copy()
            
            if len(df_complete) > 0:
                # Standardize Win.Loss column
                if 'Win.Loss' not in df.columns:
                    print(f"⚠️  Error: 'Win.Loss' column not found in {sheet}")
                    return None
                
                # Clean and standardize WL column
                df_complete['WL'] = df_complete['Win.Loss'].astype(str).str.strip()
                df_complete['WL'] = df_complete['WL'].replace(['', 'nan'], np.nan)
                df_complete = df_complete.drop(columns=['Win.Loss'])
                
                # Add week identifier
                df_complete['Week'] = sheet
                
                all_data.append(df_complete)
                print(f"✓ {sheet}: {len(df_complete)} completed predictions loaded")
            else:
                print(f"  {sheet}: No completed predictions yet")
    
    if not all_data:
        print("\n⚠️  No completed predictions found!")
        return None
    
    combined = pd.concat(all_data, ignore_index=True)
    
    # Clean data types
    combined['Mean.Pred'] = pd.to_numeric(combined['Mean.Pred'], errors='coerce')
    combined['Vegas.Line'] = pd.to_numeric(combined['Vegas.Line'], errors='coerce')
    combined['Actual'] = pd.to_numeric(combined['Actual'], errors='coerce')
    combined['P10'] = pd.to_numeric(combined['P10'], errors='coerce')
    combined['P50'] = pd.to_numeric(combined['P50'], errors='coerce')
    combined['P90'] = pd.to_numeric(combined['P90'], errors='coerce')
    
    # Parse Prob.Over if it's a string with %
    if combined['Prob.Over'].dtype == 'object':
        combined['Prob.Over'] = combined['Prob.Over'].str.rstrip('%').astype('float') / 100
    
    # Rename for easier access
    combined = combined.rename(columns={
        'Mean.Pred': 'Mean_Pred',
        'Vegas.Line': 'Vegas_Line',
        'Home/Away': 'Home_Away',
        'Prob.Over': 'Prob_Over'
    })
    
    # Validate WL values
    valid_wl = combined['WL'].isin(['W', 'L'])
    if not valid_wl.all():
        invalid_count = (~valid_wl).sum()
        print(f"\n⚠️  Warning: {invalid_count} predictions with invalid W/L values")
    
    print(f"\n✓ Total: {len(combined)} completed predictions loaded")
    print("="*60)
    
    return combined

def calculate_metrics(df):
    """Calculate comprehensive performance metrics"""
    
    # Error metrics
    df['prediction_error'] = df['Mean_Pred'] - df['Actual']
    df['abs_error'] = abs(df['prediction_error'])
    df['pct_error'] = (df['abs_error'] / df['Actual'] * 100)
    df['line_distance'] = abs(df['Mean_Pred'] - df['Vegas_Line'])
    
    # Was our prediction closer to actual than Vegas?
    df['beat_vegas'] = df['abs_error'] < abs(df['Vegas_Line'] - df['Actual'])
    
    # Confidence metrics
    df['confidence_range'] = df['P90'] - df['P10']
    df['normalized_confidence'] = df['confidence_range'] / df['Mean_Pred']
    
    # Categorize predictions
    df['error_category'] = pd.cut(df['abs_error'], 
                                   bins=[0, 20, 40, 60, 100, 500],
                                   labels=['Excellent (<20)', 'Good (20-40)', 
                                          'Fair (40-60)', 'Poor (60-100)', 'Very Poor (>100)'])
    
    df['confidence_category'] = pd.cut(df['Prob_Over'],
                                       bins=[0, 0.4, 0.6, 1.0],
                                       labels=['Low Confidence', 'Medium Confidence', 'High Confidence'])
    
    return df

def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(title.upper())
    print('='*60)

def analyze_overall_performance(df):
    """Overall model performance statistics"""
    
    print_section("Overall Performance Summary")
    
    total = len(df)
    wins = (df['WL'] == 'W').sum()
    losses = (df['WL'] == 'L').sum()
    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    
    print(f"\n📊 RECORD: {wins}-{losses} ({win_rate:.1f}%)")
    print(f"   Total predictions analyzed: {total}")
    
    # Break-even analysis
    breakeven = 52.38  # Standard -110 vig
    if win_rate >= breakeven:
        print(f"   ✓ PROFITABLE (above {breakeven}% breakeven)")
    else:
        needed = int(np.ceil(breakeven * total / 100) - wins)
        print(f"   ✗ Below breakeven (need {needed} more wins)")
    
    # Prediction accuracy
    print(f"\n📏 ACCURACY METRICS:")
    print(f"   Mean Absolute Error:    {df['abs_error'].mean():.1f} yards")
    print(f"   Median Absolute Error:  {df['abs_error'].median():.1f} yards")
    print(f"   Mean % Error:           {df['pct_error'].mean():.1f}%")
    print(f"   Std Dev of Errors:      {df['prediction_error'].std():.1f} yards")
    
    # Beat Vegas rate
    beat_vegas_rate = df['beat_vegas'].mean() * 100
    print(f"\n🎯 BEAT VEGAS LINE:")
    print(f"   Predictions closer than Vegas: {beat_vegas_rate:.1f}%")
    
    # Bias detection
    mean_error = df['prediction_error'].mean()
    if abs(mean_error) > 5:
        bias_direction = "OVERESTIMATING" if mean_error > 0 else "UNDERESTIMATING"
        print(f"\n⚠️  MODEL BIAS: {bias_direction} by {abs(mean_error):.1f} yards on average")
    else:
        print(f"\n✓ No significant bias detected (mean error: {mean_error:.1f} yards)")

def analyze_by_category(df, category, category_name):
    """Analyze performance by any categorical variable"""
    
    print_section(f"Performance by {category_name}")
    
    for value in sorted(df[category].unique()):
        subset = df[df[category] == value]
        wins = (subset['WL'] == 'W').sum()
        total = len(subset)
        win_rate = wins / total * 100 if total > 0 else 0
        avg_error = subset['prediction_error'].mean()
        
        status = "✓" if win_rate >= 52.38 else "✗"
        
        print(f"\n{status} {value}: {wins}-{total-wins} ({win_rate:.1f}%)")
        print(f"   Predictions: {total}")
        print(f"   Avg prediction error: {avg_error:+.1f} yards")
        print(f"   Avg absolute error: {subset['abs_error'].mean():.1f} yards")

def analyze_confidence_levels(df):
    """Analyze performance at different confidence levels"""
    
    print_section("Performance by Confidence Level")
    
    for conf_level in ['High Confidence', 'Medium Confidence', 'Low Confidence']:
        subset = df[df['confidence_category'] == conf_level]
        if len(subset) > 0:
            wins = (subset['WL'] == 'W').sum()
            total = len(subset)
            win_rate = wins / total * 100
            
            status = "✓" if win_rate >= 52.38 else "✗"
            
            print(f"\n{status} {conf_level}:")
            print(f"   Record: {wins}-{total-wins} ({win_rate:.1f}%)")
            print(f"   Predictions: {total}")
            print(f"   Avg prob: {subset['Prob_Over'].mean():.1%}")

def analyze_line_edge(df):
    """Analyze performance based on how far prediction is from Vegas line"""
    
    print_section("Performance by Model Edge")
    
    # Define edge categories
    bins = [0, 5, 10, 20, 50, 500]
    labels = ['0-5 yards', '5-10 yards', '10-20 yards', '20-50 yards', '>50 yards']
    
    df['edge_category'] = pd.cut(df['line_distance'], bins=bins, labels=labels)
    
    for edge in labels:
        subset = df[df['edge_category'] == edge]
        if len(subset) > 0:
            wins = (subset['WL'] == 'W').sum()
            total = len(subset)
            win_rate = wins / total * 100
            
            status = "✓" if win_rate >= 52.38 else "✗"
            
            print(f"\n{status} Edge: {edge}")
            print(f"   Record: {wins}-{total-wins} ({win_rate:.1f}%)")
            print(f"   Avg edge: {subset['line_distance'].mean():.1f} yards")

def analyze_by_week(df):
    """Show performance trends by week"""
    
    print_section("Performance by Week")
    
    for week in sorted(df['Week'].unique()):
        subset = df[df['Week'] == week]
        wins = (subset['WL'] == 'W').sum()
        total = len(subset)
        win_rate = wins / total * 100 if total > 0 else 0
        
        status = "✓" if win_rate >= 52.38 else "✗"
        
        print(f"{status} {week}: {wins}-{total-wins} ({win_rate:.1f}%)")

def analyze_player_performance(df):
    """Identify which players the model predicts best/worst"""
    
    print_section("Player-Specific Performance")
    
    # Players with multiple predictions
    player_stats = df.groupby('Player').agg({
        'WL': lambda x: (x == 'W').sum(),
        'abs_error': 'mean',
        'Player': 'count'
    }).rename(columns={'Player': 'count', 'WL': 'wins'})
    
    player_stats = player_stats[player_stats['count'] >= 2]  # At least 2 predictions
    player_stats['losses'] = player_stats['count'] - player_stats['wins']
    player_stats['win_rate'] = (player_stats['wins'] / player_stats['count'] * 100).round(1)
    player_stats = player_stats.sort_values('count', ascending=False)
    
    print(f"\n🎯 BEST PREDICTED PLAYERS (lowest avg error, min 2 predictions):")
    best_players = player_stats.nsmallest(5, 'abs_error')[['count', 'wins', 'losses', 'win_rate', 'abs_error']]
    print(best_players.to_string())
    
    print(f"\n⚠️  WORST PREDICTED PLAYERS (highest avg error, min 2 predictions):")
    worst_players = player_stats.nlargest(5, 'abs_error')[['count', 'wins', 'losses', 'win_rate', 'abs_error']]
    print(worst_players.to_string())

def show_extreme_predictions(df):
    """Show best and worst individual predictions"""
    
    print_section("Notable Individual Predictions")
    
    cols = ['Player', 'Team', 'Week', 'Mean_Pred', 'Vegas_Line', 'Actual', 'abs_error', 'Lean', 'WL']
    
    print("\n🏆 BEST PREDICTIONS (smallest errors):")
    best = df.nsmallest(5, 'abs_error')[cols]
    for idx, row in best.iterrows():
        print(f"   {row['Player']} ({row['Team']}) - {row['Week']}")
        print(f"      Predicted: {row['Mean_Pred']:.0f} | Vegas: {row['Vegas_Line']:.0f} | Actual: {row['Actual']:.0f}")
        print(f"      Error: {row['abs_error']:.1f} yards | {row['Lean']} bet → {row['WL']}")
    
    print("\n❌ WORST PREDICTIONS (biggest errors):")
    worst = df.nlargest(5, 'abs_error')[cols]
    for idx, row in worst.iterrows():
        print(f"   {row['Player']} ({row['Team']}) - {row['Week']}")
        print(f"      Predicted: {row['Mean_Pred']:.0f} | Vegas: {row['Vegas_Line']:.0f} | Actual: {row['Actual']:.0f}")
        print(f"      Error: {row['abs_error']:.1f} yards | {row['Lean']} bet → {row['WL']}")

def generate_recommendations(df):
    """Generate actionable recommendations based on analysis"""
    
    print_section("Actionable Recommendations")
    
    recommendations = []
    
    # Overall performance
    win_rate = (df['WL'] == 'W').mean() * 100
    if win_rate < 52.38:
        recommendations.append(f"🔴 CRITICAL: Overall win rate ({win_rate:.1f}%) is below breakeven (52.38%). Model needs significant improvement.")
    elif win_rate < 55:
        recommendations.append(f"🟡 Win rate ({win_rate:.1f}%) is marginally profitable. Focus on high-confidence bets.")
    else:
        recommendations.append(f"🟢 Win rate ({win_rate:.1f}%) is profitable! Continue current strategy.")
    
    # Bias check
    mean_error = df['prediction_error'].mean()
    if abs(mean_error) > 10:
        direction = "down" if mean_error > 0 else "up"
        recommendations.append(f"📊 Model consistently predicts {abs(mean_error):.1f} yards too {'high' if mean_error > 0 else 'low'}. Adjust predictions {direction}.")
    
    # Over vs Under
    over_wr = (df[df['Lean'] == 'OVER']['WL'] == 'W').mean() * 100
    under_wr = (df[df['Lean'] == 'UNDER']['WL'] == 'W').mean() * 100
    
    if abs(over_wr - under_wr) > 10:
        better = 'OVER' if over_wr > under_wr else 'UNDER'
        worse = 'UNDER' if better == 'OVER' else 'OVER'
        recommendations.append(f"⚖️  {better} bets ({max(over_wr, under_wr):.1f}%) significantly outperform {worse} bets ({min(over_wr, under_wr):.1f}%). Consider focusing on {better} only.")
    
    # Home vs Away
    home_wr = (df[df['Home_Away'] == 'Home']['WL'] == 'W').mean() * 100
    away_wr = (df[df['Home_Away'] == 'Away']['WL'] == 'W').mean() * 100
    
    if abs(home_wr - away_wr) > 10:
        better = 'Home' if home_wr > away_wr else 'Away'
        recommendations.append(f"🏠 Model performs better on {better} games ({max(home_wr, away_wr):.1f}% vs {min(home_wr, away_wr):.1f}%).")
    
    # Edge analysis
    close_lines = df[df['line_distance'] <= 10]
    if len(close_lines) > 0:
        close_wr = (close_lines['WL'] == 'W').mean() * 100
        if close_wr < 45:
            recommendations.append(f"🎯 Avoid betting when prediction is close to line (≤10 yards): only {close_wr:.1f}% win rate.")
    
    # Confidence levels
    high_conf = df[df['confidence_category'] == 'High Confidence']
    if len(high_conf) > 0:
        high_wr = (high_conf['WL'] == 'W').mean() * 100
        recommendations.append(f"🎲 High confidence bets win {high_wr:.1f}% of the time. Focus on these when possible.")
    
    # Print recommendations
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec}")
    
    print("\n\n💡 NEXT STEPS TO IMPROVE:")
    improvements = [
        "Add weather data (wind speed, temperature, precipitation)",
        "Incorporate injury reports and player status",
        "Weight recent performance more heavily (last 3-4 games)",
        "Add opponent pass defense rankings (DVOA, yards allowed)",
        "Include situational factors (division games, primetime, playoff implications)",
        "Consider implementing a Kelly Criterion bet sizing strategy",
        "Track and analyze model performance by specific defenses",
        "Add quarterback pressure rate and time to throw metrics"
    ]
    
    for i, imp in enumerate(improvements, 1):
        print(f"   {i}. {imp}")

def main():
    """Run complete diagnostics"""
    
    df = load_all_weeks()
    
    if df is None:
        return
    
    df = calculate_metrics(df)
    
    # Run all analyses
    analyze_overall_performance(df)
    analyze_by_category(df, 'Lean', 'Bet Direction (Over/Under)')
    analyze_by_category(df, 'Home_Away', 'Home/Away')
    analyze_confidence_levels(df)
    analyze_line_edge(df)
    analyze_by_week(df)
    analyze_player_performance(df)
    show_extreme_predictions(df)
    generate_recommendations(df)
    
    print("\n" + "="*60)
    print("DIAGNOSTICS COMPLETE")
    print("="*60)
    
    return df

if __name__ == "__main__":
    df = main()