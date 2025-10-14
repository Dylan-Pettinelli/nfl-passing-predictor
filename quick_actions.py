# quick_actions.py
# Convenience hub for common NFL prediction workflows

import os
import sys
import subprocess
import pandas as pd
from datetime import datetime
from pathlib import Path

def print_menu():
    """Display main menu"""
    print("\n" + "="*60)
    print("NFL PASSING YARDS PREDICTION - QUICK ACTIONS")
    print("="*60)
    print("\n📊 ANALYSIS & DIAGNOSTICS")
    print("  1. Run full diagnostics on all predictions")
    print("  2. Quick weekly summary (latest week)")
    print("  3. Compare model vs Vegas accuracy")
    print("  4. Export predictions to CSV")
    print("  5. Show bankroll tracker")
    
    print("\n🎯 PREDICTIONS & BETTING")
    print("  6. Generate predictions for upcoming week")
    print("  7. Get betting recommendations (SMART ADVISOR) ⭐")
    print("  8. Update actuals for completed week")
    print("  9. Batch import from template CSV")
    
    print("\n🔧 MAINTENANCE")
    print("  10. Retrain model with latest data")
    print("  11. Validate data integrity")
    print("  12. Backup predictions file")
    print("  13. Generate HTML dashboard")
    
    print("\n❓ UTILITIES")
    print("  14. Check player eligibility (min games)")
    print("  15. Show available weeks in Excel")
    
    print("\n  0. Exit")
    print("="*60)

def run_diagnostics():
    """Run full diagnostics"""
    print("\n🔍 Running full diagnostics...")
    try:
        subprocess.run([sys.executable, "diagnostics.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running diagnostics: {e}")
    except FileNotFoundError:
        print("❌ diagnostics.py not found")

def quick_weekly_summary():
    """Show quick summary of latest week"""
    print("\n📈 Latest Week Summary...")
    try:
        excel_file = 'data/passing-prop-predictions-2025.xlsx'
        if not os.path.exists(excel_file):
            print("❌ No predictions file found")
            return
        
        xl = pd.ExcelFile(excel_file)
        latest_week = sorted([s for s in xl.sheet_names if s.startswith('Week')])[-1]
        
        df = pd.read_excel(excel_file, sheet_name=latest_week)
        df_complete = df[df['Actual'].notna() & (df['Actual'] != '')]
        
        if len(df_complete) == 0:
            print(f"ℹ️  {latest_week}: No completed predictions yet")
            return
        
        wins = (df_complete['Win.Loss'] == 'W').sum()
        losses = (df_complete['Win.Loss'] == 'L').sum()
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        
        df_complete['abs_error'] = abs(pd.to_numeric(df_complete['Mean.Pred'], errors='coerce') - 
                                       pd.to_numeric(df_complete['Actual'], errors='coerce'))
        
        print(f"\n{latest_week} Results:")
        print(f"  Record: {wins}-{losses} ({win_rate:.1f}%)")
        print(f"  Total predictions: {len(df)}")
        print(f"  Completed: {len(df_complete)}")
        print(f"  Pending: {len(df) - len(df_complete)}")
        print(f"  Avg Error: {df_complete['abs_error'].mean():.1f} yards")
        print(f"  Median Error: {df_complete['abs_error'].median():.1f} yards")
        
        best = df_complete.nsmallest(1, 'abs_error')
        worst = df_complete.nlargest(1, 'abs_error')
        
        print(f"\n  Best: {best.iloc[0]['Player']} ({best.iloc[0]['abs_error']:.0f} yards off)")
        print(f"  Worst: {worst.iloc[0]['Player']} ({worst.iloc[0]['abs_error']:.0f} yards off)")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def compare_vegas_accuracy():
    """Compare model accuracy vs Vegas"""
    print("\n🎰 Model vs Vegas Comparison...")
    try:
        excel_file = 'data/passing-prop-predictions-2025.xlsx'
        xl = pd.ExcelFile(excel_file)
        
        all_completed = []
        for sheet in [s for s in xl.sheet_names if s.startswith('Week')]:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            df_complete = df[df['Actual'].notna() & (df['Actual'] != '')]
            if len(df_complete) > 0:
                all_completed.append(df_complete)
        
        if not all_completed:
            print("❌ No completed predictions found")
            return
        
        combined = pd.concat(all_completed, ignore_index=True)
        combined['Mean.Pred'] = pd.to_numeric(combined['Mean.Pred'], errors='coerce')
        combined['Vegas.Line'] = pd.to_numeric(combined['Vegas.Line'], errors='coerce')
        combined['Actual'] = pd.to_numeric(combined['Actual'], errors='coerce')
        
        combined['model_error'] = abs(combined['Mean.Pred'] - combined['Actual'])
        combined['vegas_error'] = abs(combined['Vegas.Line'] - combined['Actual'])
        combined['beat_vegas'] = combined['model_error'] < combined['vegas_error']
        
        beat_rate = combined['beat_vegas'].mean() * 100
        model_mae = combined['model_error'].mean()
        vegas_mae = combined['vegas_error'].mean()
        
        print(f"\n  Model MAE: {model_mae:.1f} yards")
        print(f"  Vegas MAE: {vegas_mae:.1f} yards")
        print(f"  Beat Vegas Rate: {beat_rate:.1f}%")
        print(f"  Advantage: {vegas_mae - model_mae:+.1f} yards")
        
        if beat_rate > 50:
            print("\n  ✅ Model is outperforming Vegas!")
        else:
            print("\n  ⚠️  Vegas is currently more accurate")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def export_to_csv():
    """Export predictions to CSV for analysis"""
    print("\n💾 Exporting predictions to CSV...")
    try:
        excel_file = 'data/passing-prop-predictions-2025.xlsx'
        xl = pd.ExcelFile(excel_file)
        
        all_data = []
        for sheet in [s for s in xl.sheet_names if s.startswith('Week')]:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            df['Week'] = sheet
            all_data.append(df)
        
        combined = pd.concat(all_data, ignore_index=True)
        output_file = f'data/all_predictions_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        combined.to_csv(output_file, index=False)
        
        print(f"  ✅ Exported {len(combined)} predictions to {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def bankroll_tracker():
    """Simple bankroll tracking"""
    print("\n💰 Bankroll Tracker...")
    try:
        excel_file = 'data/passing-prop-predictions-2025.xlsx'
        xl = pd.ExcelFile(excel_file)
        
        all_completed = []
        for sheet in [s for s in xl.sheet_names if s.startswith('Week')]:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            df['Week'] = sheet
            df_complete = df[df['Actual'].notna() & (df['Actual'] != '')]
            if len(df_complete) > 0:
                all_completed.append(df_complete)
        
        if not all_completed:
            print("❌ No completed predictions found")
            return
        
        combined = pd.concat(all_completed, ignore_index=True)
        
        unit_size = float(input("\nEnter unit size ($): "))
        
        wins = (combined['Win.Loss'] == 'W').sum()
        losses = (combined['Win.Loss'] == 'L').sum()
        
        profit = (wins * unit_size * 0.909) - (losses * unit_size)
        roi = (profit / (wins + losses) / unit_size) * 100
        
        print(f"\n  Total Bets: {wins + losses}")
        print(f"  Record: {wins}-{losses}")
        print(f"  Win Rate: {wins/(wins+losses)*100:.1f}%")
        print(f"  Profit/Loss: ${profit:,.2f}")
        print(f"  ROI: {roi:,.1f}%")
        print(f"  Units: {profit/unit_size:+.2f}u")
        
        print("\n  Weekly P&L:")
        for week in sorted(combined['Week'].unique()):
            week_df = combined[combined['Week'] == week]
            week_wins = (week_df['Win.Loss'] == 'W').sum()
            week_losses = (week_df['Win.Loss'] == 'L').sum()
            week_profit = (week_wins * unit_size * 0.909) - (week_losses * unit_size)
            print(f"    {week}: ${week_profit:+,.2f} ({week_wins}-{week_losses})")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def generate_predictions():
    """Launch prediction script"""
    print("\n🎯 Launching prediction interface...")
    try:
        subprocess.run([sys.executable, "predict_upcoming.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
    except FileNotFoundError:
        print("❌ predict_upcoming.py not found")

def get_betting_recommendations():
    """Launch smart betting advisor"""
    print("\n🎯 Launching Smart Betting Advisor...")
    try:
        subprocess.run([sys.executable, "smart_betting_advisor.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
    except FileNotFoundError:
        print("❌ smart_betting_advisor.py not found")

def update_actuals():
    """Update actuals for a week"""
    print("\n📝 Update Actuals...")
    week = input("Enter week number to update (1-18): ").strip()
    try:
        subprocess.run(['Rscript', 'src/update_actuals.R', week], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
    except FileNotFoundError:
        print("❌ update_actuals.R not found or R not installed")

def batch_import_template():
    """Create batch import template"""
    print("\n📄 Batch import templates are in batch-imports/ folder")
    print("  Use predict_upcoming.py with batch mode to import them")

def retrain_model():
    """Retrain model"""
    print("\n🔄 Retraining model...")
    confirm = input("This will take several minutes. Continue? (yes/no): ").strip().lower()
    if confirm == 'yes':
        try:
            subprocess.run([sys.executable, "-m", "src.train_pipeline"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {e}")
    else:
        print("  Cancelled")

def validate_data():
    """Check data integrity"""
    print("\n🔍 Validating data integrity...")
    try:
        files_to_check = [
            'data/passing_yards_player_logs.csv',
            'data/team_offense_logs.csv',
            'data/defense_logs.csv',
            'models/qb_passing_yards_model.pkl'
        ]
        
        all_good = True
        for file in files_to_check:
            if os.path.exists(file):
                size = os.path.getsize(file)
                print(f"  ✅ {file} ({size:,} bytes)")
            else:
                print(f"  ❌ {file} MISSING")
                all_good = False
        
        if all_good:
            print("\n  ✅ All core files present")
        else:
            print("\n  ⚠️  Some files missing - consider retraining")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def backup_predictions():
    """Backup Excel file"""
    print("\n💾 Backing up predictions...")
    try:
        source = 'data/passing-prop-predictions-2025.xlsx'
        if not os.path.exists(source):
            print("❌ No predictions file to backup")
            return
        
        backup_dir = Path('data/backups')
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f'predictions_backup_{timestamp}.xlsx'
        
        import shutil
        shutil.copy2(source, backup_path)
        
        print(f"  ✅ Backup created: {backup_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def generate_weekly_report():
    """Generate formatted weekly report"""
    print("\n📊 Generating HTML dashboard...")
    try:
        subprocess.run([sys.executable, "dashboard.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
    except FileNotFoundError:
        print("❌ dashboard.py not found")

def check_player_eligibility():
    """Check if player has enough games for prediction"""
    print("\n👤 Check Player Eligibility...")
    try:
        player_name = input("Enter player name (e.g., P.Mahomes): ").strip()
        player_data = pd.read_csv('data/passing_yards_player_logs.csv')
        
        player_games = player_data[player_data['player_name'] == player_name]
        
        if len(player_games) == 0:
            print(f"  ❌ {player_name} not found in database")
            print("\n  Similar players:")
            similar = player_data[player_data['player_name'].str.contains(
                player_name.split('.')[0], case=False, na=False
            )]['player_name'].unique()[:5]
            for p in similar:
                print(f"    - {p}")
        else:
            total_games = len(player_games)
            seasons = player_games['season'].unique()
            latest_season = player_games['season'].max()
            latest_week = player_games[player_games['season'] == latest_season]['week'].max()
            
            print(f"\n  ✅ {player_name} found")
            print(f"  Total games: {total_games}")
            print(f"  Seasons: {sorted(seasons)}")
            print(f"  Latest: Season {latest_season}, Week {latest_week}")
            
            if total_games >= 10:
                print(f"  ✅ Eligible for predictions (≥10 games)")
            else:
                print(f"  ⚠️  Need {10 - total_games} more games for reliable predictions")
                
    except Exception as e:
        print(f"❌ Error: {e}")

def show_available_weeks():
    """Show what weeks exist in Excel"""
    print("\n📅 Available Weeks...")
    try:
        excel_file = 'data/passing-prop-predictions-2025.xlsx'
        if not os.path.exists(excel_file):
            print("❌ No predictions file found")
            return
        
        xl = pd.ExcelFile(excel_file)
        weeks = [s for s in xl.sheet_names if s.startswith('Week')]
        
        print(f"\n  Found {len(weeks)} weeks:")
        for week in sorted(weeks):
            df = pd.read_excel(excel_file, sheet_name=week)
            completed = df[df['Actual'].notna() & (df['Actual'] != '')]
            status = "✅" if len(completed) > 0 else "📝"
            print(f"    {status} {week}: {len(df)} predictions ({len(completed)} completed)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main menu loop"""
    actions = {
        '1': run_diagnostics,
        '2': quick_weekly_summary,
        '3': compare_vegas_accuracy,
        '4': export_to_csv,
        '5': bankroll_tracker,
        '6': generate_predictions,
        '7': get_betting_recommendations,
        '8': update_actuals,
        '9': batch_import_template,
        '10': retrain_model,
        '11': validate_data,
        '12': backup_predictions,
        '13': generate_weekly_report,
        '14': check_player_eligibility,
        '15': show_available_weeks
    }
    
    while True:
        print_menu()
        choice = input("\nSelect action (0-15): ").strip()
        
        if choice == '0':
            print("\n👋 Goodbye!")
            break
        elif choice in actions:
            actions[choice]()
            input("\nPress Enter to continue...")
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")