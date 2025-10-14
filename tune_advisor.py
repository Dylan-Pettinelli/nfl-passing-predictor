# tune_advisor.py
# Automated analysis and rule recommendations for smart_betting_advisor.py

import pandas as pd
import numpy as np
from datetime import datetime

class AdvisorTuner:
    """
    Analyzes historical performance and suggests rule updates
    """
    
    def __init__(self, min_sample_size=50):
        self.min_sample_size = min_sample_size
        self.load_data()
    
    def load_data(self):
        """Load all completed predictions"""
        excel_file = 'data/passing-prop-predictions-2025.xlsx'
        xl = pd.ExcelFile(excel_file)
        
        all_data = []
        for sheet in [s for s in xl.sheet_names if s.startswith('Week')]:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            df['Week'] = sheet
            df_complete = df[df['Actual'].notna() & (df['Actual'] != '')]
            if len(df_complete) > 0:
                all_data.append(df_complete)
        
        if not all_data:
            print("❌ No completed predictions found")
            self.df = None
            return
        
        self.df = pd.concat(all_data, ignore_index=True)
        self.df['Mean.Pred'] = pd.to_numeric(self.df['Mean.Pred'], errors='coerce')
        self.df['Vegas.Line'] = pd.to_numeric(self.df['Vegas.Line'], errors='coerce')
        self.df['Actual'] = pd.to_numeric(self.df['Actual'], errors='coerce')
        
        # Calculate metrics
        self.df['edge'] = abs(self.df['Mean.Pred'] - self.df['Vegas.Line'])
        self.df['abs_error'] = abs(self.df['Mean.Pred'] - self.df['Actual'])
        
        # Parse probability
        if self.df['Prob.Over'].dtype == 'object':
            self.df['Prob.Over'] = self.df['Prob.Over'].str.rstrip('%').astype('float') / 100
        
        # Determine confidence
        self.df['model_prob'] = self.df.apply(
            lambda row: row['Prob.Over'] if row['Lean'] == 'OVER' else 1 - row['Prob.Over'],
            axis=1
        )
        self.df['confidence'] = pd.cut(
            self.df['model_prob'],
            bins=[0, 0.55, 0.65, 1.0],
            labels=['Low', 'Medium', 'High']
        )
        
        print(f"✅ Loaded {len(self.df)} completed predictions")
    
    def analyze_edge_ranges(self):
        """Analyze win rates by edge size"""
        print("\n" + "="*70)
        print("📊 EDGE ANALYSIS")
        print("="*70)
        
        # Define edge bins
        bins = [0, 5, 10, 15, 20, 30, 50, 500]
        labels = ['0-5', '5-10', '10-15', '15-20', '20-30', '30-50', '>50']
        
        self.df['edge_bin'] = pd.cut(self.df['edge'], bins=bins, labels=labels)
        
        results = []
        for edge_range in labels:
            subset = self.df[self.df['edge_bin'] == edge_range]
            if len(subset) > 5:  # Need at least 5 bets
                wins = (subset['Win.Loss'] == 'W').sum()
                total = len(subset)
                win_rate = (wins / total) * 100
                
                results.append({
                    'edge_range': edge_range,
                    'count': total,
                    'win_rate': win_rate,
                    'wins': wins
                })
                
                status = "✅" if win_rate >= 52.38 else "❌"
                print(f"{status} Edge {edge_range}y: {wins}/{total} ({win_rate:.1f}%)")
        
        # Find optimal range
        if results:
            optimal = max(results, key=lambda x: x['win_rate'])
            print(f"\n🎯 OPTIMAL EDGE RANGE: {optimal['edge_range']} yards ({optimal['win_rate']:.1f}% win rate)")
            
            # Current advisor uses 5-20 yards
            if optimal['edge_range'] not in ['5-10', '10-15', '15-20']:
                print(f"⚠️  RECOMMENDATION: Consider updating Tier 1 edge range")
                print(f"   Current: 5-20 yards")
                print(f"   Suggested: Test {optimal['edge_range']} yard range")
        
        return results
    
    def analyze_home_away(self):
        """Analyze home vs away performance"""
        print("\n" + "="*70)
        print("🏠 HOME/AWAY ANALYSIS")
        print("="*70)
        
        home = self.df[self.df['Home/Away'] == 'Home']
        away = self.df[self.df['Home/Away'] == 'Away']
        
        home_wins = (home['Win.Loss'] == 'W').sum()
        home_total = len(home)
        home_wr = (home_wins / home_total) * 100 if home_total > 0 else 0
        
        away_wins = (away['Win.Loss'] == 'W').sum()
        away_total = len(away)
        away_wr = (away_wins / away_total) * 100 if away_total > 0 else 0
        
        print(f"Home games: {home_wins}/{home_total} ({home_wr:.1f}%)")
        print(f"Away games: {away_wins}/{away_total} ({away_wr:.1f}%)")
        print(f"Difference: {home_wr - away_wr:+.1f}%")
        
        # Recommendation
        if abs(home_wr - away_wr) < 3:
            print(f"\n💡 RECOMMENDATION: Home/Away split is minimal")
            print(f"   Consider removing home requirement from Tier 1")
        elif home_wr > away_wr + 5:
            print(f"\n✅ KEEP: Home games significantly outperform")
            print(f"   Current Tier 1 requirement (home only) is optimal")
        
        return home_wr, away_wr
    
    def analyze_confidence_levels(self):
        """Analyze performance by confidence"""
        print("\n" + "="*70)
        print("🎲 CONFIDENCE ANALYSIS")
        print("="*70)
        
        for conf in ['High', 'Medium', 'Low']:
            subset = self.df[self.df['confidence'] == conf]
            if len(subset) > 0:
                wins = (subset['Win.Loss'] == 'W').sum()
                total = len(subset)
                win_rate = (wins / total) * 100
                avg_prob = subset['model_prob'].mean()
                
                status = "✅" if win_rate >= 52.38 else "❌"
                print(f"{status} {conf} confidence: {wins}/{total} ({win_rate:.1f}%) | Avg prob: {avg_prob:.1%}")
        
        # Recommendation
        low_conf = self.df[self.df['confidence'] == 'Low']
        if len(low_conf) > 10:
            low_wr = (low_conf['Win.Loss'] == 'W').mean() * 100
            if low_wr < 50:
                print(f"\n💡 RECOMMENDATION: Low confidence bets underperform")
                print(f"   Consider excluding from Tier 1 (already done)")
                print(f"   Consider excluding from Tier 2 as well")
    
    def analyze_problem_players(self):
        """Identify players to blacklist"""
        print("\n" + "="*70)
        print("⚠️  PROBLEM PLAYERS ANALYSIS")
        print("="*70)
        
        player_stats = self.df.groupby('Player').agg({
            'abs_error': 'mean',
            'Win.Loss': lambda x: (x == 'W').sum(),
            'Player': 'count'
        }).rename(columns={'Player': 'games', 'Win.Loss': 'wins'})
        
        player_stats = player_stats[player_stats['games'] >= 3]  # Min 3 games
        player_stats['win_rate'] = (player_stats['wins'] / player_stats['games']) * 100
        
        # Flag players with high error
        problem_players = player_stats[player_stats['abs_error'] > 70].sort_values('abs_error', ascending=False)
        
        print("\nPlayers with >70 yard average error (min 3 games):")
        for player, row in problem_players.iterrows():
            print(f"❌ {player}: {row['abs_error']:.1f} yards avg error | {row['wins']:.0f}/{row['games']:.0f} ({row['win_rate']:.1f}%)")
        
        if len(problem_players) > 0:
            print(f"\n💡 RECOMMENDATION: Current blacklist is accurate")
            print(f"   These players should trigger red flags in advisor")
        
        # Check for new problem players
        current_blacklist = ['R.Wilson', 'J.Fields', 'M.Stafford']
        new_problems = [p for p in problem_players.index if p not in current_blacklist]
        
        if new_problems:
            print(f"\n⚠️  NEW PROBLEM PLAYERS DETECTED:")
            for player in new_problems:
                print(f"   • {player}: {problem_players.loc[player, 'abs_error']:.1f} yards avg error")
            print(f"\n   Add to blacklist in check_player_history() method")
    
    def simulate_tier_performance(self):
        """Simulate what advisor would have recommended"""
        print("\n" + "="*70)
        print("🧪 TIER SIMULATION")
        print("="*70)
        print("Simulating what current advisor logic would recommend...\n")
        
        # Simulate tier assignment
        tier1_mask = (
            (self.df['edge'] >= 5) & 
            (self.df['edge'] <= 20) & 
            (self.df['Home/Away'] == 'Home') & 
            (self.df['confidence'].isin(['Medium', 'High'])) &
            (self.df['abs_error'] <= 70)  # Not a problem player
        )
        
        tier2_mask = (
            ((self.df['edge'] > 20) | 
             (self.df['Home/Away'] == 'Away') | 
             (self.df['confidence'] == 'Low')) &
            (self.df['edge'] >= 5) &
            (self.df['abs_error'] <= 70)  # Not a problem player
        )
        
        tier1 = self.df[tier1_mask]
        tier2 = self.df[tier2_mask]
        skip = self.df[~(tier1_mask | tier2_mask)]
        
        print(f"📊 TIER BREAKDOWN:")
        print(f"   Tier 1: {len(tier1)} bets")
        print(f"   Tier 2: {len(tier2)} bets")
        print(f"   Skip: {len(skip)} bets")
        
        # Analyze tier performance
        if len(tier1) > 0:
            tier1_wins = (tier1['Win.Loss'] == 'W').sum()
            tier1_wr = (tier1_wins / len(tier1)) * 100
            tier1_status = "✅" if tier1_wr >= 58 else "⚠️" if tier1_wr >= 52 else "❌"
            print(f"\n{tier1_status} TIER 1 PERFORMANCE:")
            print(f"   Record: {tier1_wins}/{len(tier1)} ({tier1_wr:.1f}%)")
            print(f"   Target: 58-60%")
            
            if tier1_wr < 55:
                print(f"   ⚠️  Below target - consider tightening requirements")
            elif tier1_wr > 62:
                print(f"   ✅ Exceeding target - criteria are working well!")
        
        if len(tier2) > 0:
            tier2_wins = (tier2['Win.Loss'] == 'W').sum()
            tier2_wr = (tier2_wins / len(tier2)) * 100
            tier2_status = "✅" if tier2_wr >= 50 else "❌"
            print(f"\n{tier2_status} TIER 2 PERFORMANCE:")
            print(f"   Record: {tier2_wins}/{len(tier2)} ({tier2_wr:.1f}%)")
            print(f"   Target: 50-52%")
            
            if tier2_wr < 48:
                print(f"   ❌ Below target - these bets may not be worth it")
        
        # Check what we're skipping
        if len(skip) > 0:
            skip_wins = (skip['Win.Loss'] == 'W').sum()
            skip_wr = (skip_wins / len(skip)) * 100
            print(f"\n🚫 SKIPPED BETS:")
            print(f"   Record: {skip_wins}/{len(skip)} ({skip_wr:.1f}%)")
            
            if skip_wr > 55:
                print(f"   ⚠️  We're skipping profitable bets!")
                print(f"   Consider loosening requirements")
    
    def generate_update_code(self):
        """Generate code snippet for updating advisor"""
        print("\n" + "="*70)
        print("📝 SUGGESTED CODE UPDATES")
        print("="*70)
        
        # Analyze and suggest updates
        edge_results = self.analyze_edge_ranges()
        home_wr, away_wr = self.analyze_home_away()
        
        print("\nIf you need to update smart_betting_advisor.py:")
        print("="*70)
        
        # Edge update
        optimal_edge = max(edge_results, key=lambda x: x['win_rate'])
        if optimal_edge['edge_range'] not in ['5-10', '10-15', '15-20']:
            print("\n# Update edge range in calculate_tier() method:")
            print(f"# Change line ~104:")
            print(f"# OLD: if (5 <= edge <= 20 and is_home...")
            print(f"# NEW: if ({optimal_edge['edge_range'].split('-')[0]} <= edge <= {optimal_edge['edge_range'].split('-')[1]} and is_home...")
        
        # Home/away update
        if abs(home_wr - away_wr) < 3:
            print("\n# Remove home requirement from Tier 1:")
            print("# Change line ~104:")
            print("# OLD: if (5 <= edge <= 20 and is_home and confidence...")
            print("# NEW: if (5 <= edge <= 20 and confidence...")
        
        print("\n" + "="*70)
        print("⚠️  Only make these changes after 50+ new predictions!")
        print("="*70)
    
    def run_full_analysis(self):
        """Run complete analysis"""
        if self.df is None:
            print("❌ No data available")
            return
        
        print("\n" + "🔬 " + "="*68)
        print("  ADVISOR TUNING ANALYSIS")
        print("="*70)
        print(f"Analyzing {len(self.df)} completed predictions...")
        
        if len(self.df) < self.min_sample_size:
            print(f"\n⚠️  WARNING: Only {len(self.df)} predictions available")
            print(f"   Recommended minimum: {self.min_sample_size}")
            print(f"   Results may not be reliable yet")
            print(f"   Continue? (y/n): ", end='')
            if input().strip().lower() != 'y':
                return
        
        # Run all analyses
        self.analyze_edge_ranges()
        self.analyze_home_away()
        self.analyze_confidence_levels()
        self.analyze_problem_players()
        self.simulate_tier_performance()
        self.generate_update_code()
        
        # Final recommendation
        print("\n" + "="*70)
        print("📋 SUMMARY & RECOMMENDATIONS")
        print("="*70)
        
        tier1 = self.df[
            (self.df['edge'] >= 5) & 
            (self.df['edge'] <= 20) & 
            (self.df['Home/Away'] == 'Home') & 
            (self.df['confidence'].isin(['Medium', 'High']))
        ]
        
        if len(tier1) > 10:
            tier1_wr = (tier1['Win.Loss'] == 'W').mean() * 100
            
            if tier1_wr >= 58:
                print("\n✅ TIER 1 LOGIC IS WORKING WELL")
                print("   Keep current settings")
            elif tier1_wr >= 52:
                print("\n⚠️  TIER 1 IS PROFITABLE BUT BELOW TARGET")
                print("   Monitor for another 25 bets before changing")
            else:
                print("\n❌ TIER 1 NEEDS ADJUSTMENT")
                print("   Consider tightening requirements")
        
        print(f"\n📊 Next review: After {self.min_sample_size - len(self.df)} more predictions")
        print(f"   ({len(self.df)}/{self.min_sample_size} completed)")
        
        print("\n" + "="*70)


def main():
    """Run tuning analysis"""
    tuner = AdvisorTuner(min_sample_size=50)
    tuner.run_full_analysis()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()