# smart_betting_advisor.py
# Real-time betting recommendations from your Excel predictions with backtest capability

import pandas as pd
import numpy as np
import os
from datetime import datetime
import openpyxl
from openpyxl.styles import PatternFill, Font

class SmartBettingAdvisor:
    """
    Analyzes predictions from Excel and provides emotionless betting recommendations
    """
    
    def __init__(self, bankroll=1000, base_unit_pct=1.0):
        self.bankroll = bankroll
        self.base_unit_pct = base_unit_pct
        self.base_unit = bankroll * (base_unit_pct / 100)
        
        # Load historical performance data
        self.load_historical_stats()
        
    def load_historical_stats(self):
        """Load historical performance to inform decisions"""
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
            
            if all_completed:
                self.history = pd.concat(all_completed, ignore_index=True)
                self.history['Mean.Pred'] = pd.to_numeric(self.history['Mean.Pred'], errors='coerce')
                self.history['Vegas.Line'] = pd.to_numeric(self.history['Vegas.Line'], errors='coerce')
                self.history['Actual'] = pd.to_numeric(self.history['Actual'], errors='coerce')
                self.history['abs_error'] = abs(self.history['Mean.Pred'] - self.history['Actual'])
                
                # Calculate player-specific performance
                self.player_stats = self.history.groupby('Player').agg({
                    'abs_error': 'mean',
                    'Player': 'count'
                }).rename(columns={'Player': 'games'})
                
                print(f"✅ Loaded {len(self.history)} historical predictions")
            else:
                self.history = None
                self.player_stats = None
                print("ℹ️  No historical data available (first week)")
                
        except Exception as e:
            print(f"⚠️  Could not load historical data: {e}")
            self.history = None
            self.player_stats = None
    
    def check_player_history(self, player_name):
        """Check if player has historically poor model performance"""
        if self.player_stats is None:
            return False, 0
        
        if player_name in self.player_stats.index:
            avg_error = self.player_stats.loc[player_name, 'abs_error']
            games = self.player_stats.loc[player_name, 'games']
            
            # Flag if avg error > 70 yards with 3+ games
            if avg_error > 70 and games >= 3:
                return True, avg_error
        
        return False, 0
    
    def get_red_flags(self, player_name, team, opponent, home_away):
        """
        Check for automated red flags we can detect
        Returns: (red_flag_list, red_flag_count)
        """
        red_flags = []
        
        # Check player history
        is_bad_player, avg_error = self.check_player_history(player_name)
        if is_bad_player:
            red_flags.append(f"⚠️  High historical error: {avg_error:.1f} yards avg")
        
        return red_flags, len(red_flags)
    
    def calculate_tier(self, mean_pred, vegas_line, prob_over, home_away, lean, red_flags_count):
        """
        Determine betting tier based on model outputs and historical performance
        
        Returns: (tier, unit_size, reasoning)
        """
        edge = abs(mean_pred - vegas_line)
        is_home = (home_away == 'Home')
        
        # Determine confidence from probability
        if lean == 'OVER':
            model_prob = prob_over
        else:
            model_prob = 1 - prob_over
        
        if model_prob >= 0.65:
            confidence = 'High'
        elif model_prob >= 0.55:
            confidence = 'Medium'
        else:
            confidence = 'Low'
        
        reasoning = []
        
        # TIER 0: Skip entirely
        if red_flags_count >= 2:
            return 0, 0, ["❌ Too many red flags - SKIP"]
        
        if edge < 5:
            return 0, 0, ["❌ Edge too small (<5 yards) - SKIP"]
        
        # TIER 1: Full unit (optimal conditions)
        # Based on diagnostics: 5-20 yard edge, home games, medium+ confidence
        if (5 <= edge <= 20 and is_home and confidence in ['Medium', 'High'] 
            and red_flags_count == 0):
            tier = 1
            unit = self.base_unit
            reasoning.append(f"✅ TIER 1: Optimal conditions")
            reasoning.append(f"   • Edge in sweet spot: {edge:.1f} yards")
            reasoning.append(f"   • Home game advantage")
            reasoning.append(f"   • {confidence} confidence")
            reasoning.append(f"   • No red flags")
        
        # TIER 2: Half unit (decent but not optimal)
        elif red_flags_count <= 1:
            tier = 2
            unit = self.base_unit * 0.5
            reasoning.append(f"⚠️  TIER 2: Bet with caution")
            
            if edge > 20:
                reasoning.append(f"   • Large edge ({edge:.1f}y) - Vegas may know something")
            if not is_home:
                reasoning.append(f"   • Away game (52% win rate vs 57% home)")
            if confidence == 'Low':
                reasoning.append(f"   • Low confidence ({model_prob:.1%})")
            if red_flags_count == 1:
                reasoning.append(f"   • 1 red flag detected")
        
        else:
            tier = 0
            unit = 0
            reasoning.append("❌ SKIP: Failed tier requirements")
        
        return tier, unit, reasoning
    
    def analyze_prediction(self, row, show_manual_checks=True):
        """
        Analyze a single prediction and provide betting recommendation
        
        Args:
            row: DataFrame row with prediction data
            show_manual_checks: Whether to prompt for manual injury/weather checks
        
        Returns: Dict with recommendation
        """
        player = row['Player']
        team = row['Team']
        opponent = row['Opponent']
        home_away = row['Home/Away']
        mean_pred = float(row['Mean.Pred'])
        vegas_line = float(row['Vegas.Line'])
        
        # Handle probability (could be string with % or float)
        prob_over = row['Prob.Over']
        if isinstance(prob_over, str):
            prob_over = float(prob_over.rstrip('%')) / 100
        
        lean = row['Lean']
        
        edge = abs(mean_pred - vegas_line)
        
        print("\n" + "="*70)
        print(f"🏈 {player} ({team} vs {opponent})")
        print("="*70)
        print(f"Location:     {home_away}")
        print(f"Model:        {mean_pred:.1f} yards")
        print(f"Vegas Line:   {vegas_line:.1f} yards")
        print(f"Edge:         {edge:.1f} yards")
        print(f"Lean:         {lean}")
        print(f"Probability:  {prob_over:.1%} OVER")
        
        # Get automated red flags
        auto_flags, auto_count = self.get_red_flags(player, team, opponent, home_away)
        
        if auto_flags:
            print(f"\n⚠️  AUTOMATED RED FLAGS ({auto_count}):")
            for flag in auto_flags:
                print(f"    {flag}")
        
        # Manual checks
        manual_flags = []
        manual_count = 0
        
        if show_manual_checks:
            print(f"\n📋 MANUAL CHECKS (answer y/n):")
            
            checks = [
                f"Is {player} listed as Questionable/Doubtful?",
                f"Are {team}'s top 2 WRs out?",
                f"Does {team} have 3+ O-line starters injured?",
                f"Is weather extreme? (25+ MPH wind, heavy rain)",
                f"Is this a backup QB's first start?"
            ]
            
            for check in checks:
                response = input(f"  {check} (y/n): ").strip().lower()
                if response in ['y', 'yes']:
                    manual_flags.append(check)
                    manual_count += 1
        
        total_red_flags = auto_count + manual_count
        
        if manual_count > 0:
            print(f"\n⚠️  MANUAL RED FLAGS ({manual_count}):")
            for flag in manual_flags:
                print(f"    • {flag}")
        
        # Calculate tier
        tier, unit, reasoning = self.calculate_tier(
            mean_pred, vegas_line, prob_over, home_away, lean, total_red_flags
        )
        
        print(f"\n" + "-"*70)
        print("💡 RECOMMENDATION:")
        for line in reasoning:
            print(line)
        
        if tier > 0:
            print(f"\n💰 BET: ${unit:.2f} on {lean}")
            
            # Expected value calculation
            model_prob = prob_over if lean == 'OVER' else (1 - prob_over)
            ev = (model_prob * unit * 0.909) - ((1 - model_prob) * unit)
            roi = (ev / unit) * 100 if unit > 0 else 0
            
            print(f"   Expected Value: ${ev:.2f}")
            print(f"   Expected ROI:   {roi:.1f}%")
        else:
            print(f"\n🚫 SKIP THIS BET")
        
        print("="*70)
        
        return {
            'player': player,
            'team': team,
            'opponent': opponent,
            'home_away': home_away,
            'mean_pred': mean_pred,
            'vegas_line': vegas_line,
            'edge': edge,
            'lean': lean,
            'prob_over': prob_over,
            'tier': tier,
            'unit_size': unit,
            'auto_red_flags': auto_count,
            'manual_red_flags': manual_count,
            'total_red_flags': total_red_flags,
            'expected_ev': ev if tier > 0 else 0,
            'reasoning': ' | '.join(reasoning)
        }
    
    def analyze_week(self, week_num, auto_mode=False, include_completed=False):
        """
        Analyze all predictions for a specific week
        
        Args:
            week_num: Week number to analyze
            auto_mode: If True, skip manual checks (for batch preview)
            include_completed: If True, include predictions with actuals (for backtest)
        """
        excel_file = 'data/passing-prop-predictions-2025.xlsx'
        sheet_name = f'Week {week_num}'
        
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        except Exception as e:
            print(f"❌ Error loading {sheet_name}: {e}")
            return None
        
        # Filter based on mode
        if include_completed:
            df_analyze = df.copy()  # Include all for backtest
        else:
            df_analyze = df[df['Actual'].isna() | (df['Actual'] == '')]  # Only pending
        
        if len(df_analyze) == 0:
            if include_completed:
                print(f"ℹ️  No predictions in {sheet_name}")
            else:
                print(f"ℹ️  No pending predictions in {sheet_name}")
            return None
        
        print(f"\n{'='*70}")
        mode_text = "BACKTESTING" if include_completed else "ANALYZING"
        print(f"📊 {mode_text} WEEK {week_num}: {len(df_analyze)} PREDICTIONS")
        print(f"{'='*70}")
        
        recommendations = []
        
        for idx, row in df_analyze.iterrows():
            rec = self.analyze_prediction(row, show_manual_checks=not auto_mode)
            recommendations.append(rec)
            
            if not auto_mode and idx < len(df_analyze) - 1:
                cont = input("\nContinue to next? (y/n/q to quit): ").strip().lower()
                if cont == 'q':
                    break
                elif cont != 'y':
                    continue
        
        return pd.DataFrame(recommendations)
    
    def generate_bet_summary(self, recommendations_df):
        """Generate summary of betting recommendations"""
        if len(recommendations_df) == 0:
            print("\n⚠️  No bets recommended")
            return None
        
        bets = recommendations_df[recommendations_df['tier'] > 0]
        skips = recommendations_df[recommendations_df['tier'] == 0]
        
        print(f"\n{'='*70}")
        print("📋 BETTING SUMMARY")
        print(f"{'='*70}")
        
        print(f"\n✅ BETS TO PLACE: {len(bets)}")
        if len(bets) > 0:
            tier1 = bets[bets['tier'] == 1]
            tier2 = bets[bets['tier'] == 2]
            
            print(f"   • Tier 1 (Full unit): {len(tier1)} bets")
            print(f"   • Tier 2 (Half unit): {len(tier2)} bets")
            print(f"\n   Total risk: ${bets['unit_size'].sum():.2f}")
            print(f"   Expected profit: ${bets['expected_ev'].sum():.2f}")
            print(f"   Expected ROI: {(bets['expected_ev'].sum() / bets['unit_size'].sum() * 100):.1f}%")
            
            print(f"\n   Bet Details:")
            for _, bet in bets.iterrows():
                tier_label = "FULL" if bet['tier'] == 1 else "HALF"
                print(f"   • {bet['player']:15} {bet['lean']:5} ${bet['unit_size']:6.2f} ({tier_label}) - {bet['edge']:.0f}y edge")
        
        print(f"\n🚫 SKIPPED: {len(skips)}")
        if len(skips) > 0:
            print(f"   Reasons:")
            skip_reasons = skips['reasoning'].value_counts()
            for reason, count in skip_reasons.items():
                print(f"   • {count}x: {reason[:60]}...")
        
        print(f"\n{'='*70}")
        
        return bets
    
    def backtest_week(self, week_num):
        """Backtest advisor recommendations on completed week"""
        excel_file = 'data/passing-prop-predictions-2025.xlsx'
        sheet_name = f'Week {week_num}'
        
        print(f"\n{'='*70}")
        print(f"🔬 BACKTEST MODE - WEEK {week_num}")
        print(f"{'='*70}")
        print("Analyzing what the advisor WOULD have recommended...\n")
        
        # Get recommendations (without manual checks, include completed)
        recs = self.analyze_week(week_num, auto_mode=True, include_completed=True)
        
        if recs is None:
            return
        
        # Show what would have been recommended
        bets_df = self.generate_bet_summary(recs)
        
        if bets_df is None or len(bets_df) == 0:
            return
        
        # Now compare to actual results
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            
            print(f"\n{'='*70}")
            print("📊 ACTUAL RESULTS")
            print(f"{'='*70}\n")
            
            tier1_correct = 0
            tier1_total = 0
            tier2_correct = 0
            tier2_total = 0
            total_profit = 0
            
            for _, bet in bets_df.iterrows():
                player = bet['player']
                actual_row = df[df['Player'] == player].iloc[0]
                
                if pd.notna(actual_row.get('Win.Loss')) and actual_row['Win.Loss'] != '':
                    result = actual_row['Win.Loss']
                    tier = bet['tier']
                    unit = bet['unit_size']
                    
                    # Calculate P/L
                    if result == 'W':
                        pl = unit * 0.909
                        total_profit += pl
                    else:
                        pl = -unit
                        total_profit += pl
                    
                    # Track by tier
                    if tier == 1:
                        tier1_total += 1
                        if result == 'W':
                            tier1_correct += 1
                    else:
                        tier2_total += 1
                        if result == 'W':
                            tier2_correct += 1
                    
                    tier_label = "TIER 1" if tier == 1 else "TIER 2"
                    status = "✅" if result == 'W' else "❌"
                    print(f"{status} {player:15} {bet['lean']:5} ${unit:6.2f} ({tier_label}) → {result} ({pl:+.2f})")
            
            # Summary
            total_bets = tier1_total + tier2_total
            total_correct = tier1_correct + tier2_correct
            
            print(f"\n{'='*70}")
            print("BACKTEST RESULTS:")
            print(f"{'='*70}")
            
            if total_bets > 0:
                overall_wr = (total_correct / total_bets) * 100
                print(f"\n📊 OVERALL:")
                print(f"   Record: {total_correct}-{total_bets - total_correct} ({overall_wr:.1f}%)")
                print(f"   Profit/Loss: ${total_profit:+.2f}")
                print(f"   ROI: {(total_profit / bets_df['unit_size'].sum()) * 100:+.1f}%")
            
            if tier1_total > 0:
                tier1_wr = (tier1_correct / tier1_total) * 100
                print(f"\n✅ TIER 1:")
                print(f"   Record: {tier1_correct}-{tier1_total - tier1_correct} ({tier1_wr:.1f}%)")
                print(f"   Target: 58-60% (based on historical data)")
                if tier1_wr >= 58:
                    print(f"   Status: ✅ ON TARGET")
                elif tier1_wr >= 52:
                    print(f"   Status: ⚠️  Profitable but below target")
                else:
                    print(f"   Status: ❌ Below expectations")
            
            if tier2_total > 0:
                tier2_wr = (tier2_correct / tier2_total) * 100
                print(f"\n⚠️  TIER 2:")
                print(f"   Record: {tier2_correct}-{tier2_total - tier2_correct} ({tier2_wr:.1f}%)")
                print(f"   Target: 50-52% (based on historical data)")
                if tier2_wr >= 50:
                    print(f"   Status: ✅ ON TARGET")
                else:
                    print(f"   Status: ❌ Below expectations")
            
            print(f"\n{'='*70}")
            
        except Exception as e:
            print(f"❌ Error analyzing results: {e}")
    
    def save_bet_slip(self, bets_df, week_num):
        """Save recommended bets to CSV for tracking"""
        if len(bets_df) == 0:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/bet_slip_week{week_num}_{timestamp}.csv"
        
        # Add tracking columns
        bet_slip = bets_df.copy()
        bet_slip['week'] = week_num
        bet_slip['date_generated'] = datetime.now()
        bet_slip['actual_result'] = None
        bet_slip['win_loss'] = None
        bet_slip['profit_loss'] = None
        bet_slip['book'] = None
        bet_slip['odds_taken'] = -110
        
        bet_slip.to_csv(filename, index=False)
        print(f"\n💾 Bet slip saved: {filename}")
    
    def quick_preview(self, week_num):
        """Quick preview of week without manual checks"""
        print(f"\n{'='*70}")
        print(f"👀 QUICK PREVIEW MODE - Week {week_num}")
        print(f"{'='*70}")
        print("(Skipping manual checks - showing automated tiers only)\n")
        
        recs = self.analyze_week(week_num, auto_mode=True, include_completed=False)
        
        if recs is not None:
            self.generate_bet_summary(recs)


def main():
    """Interactive betting advisor"""
    print("\n" + "🏈 " + "="*68)
    print("  SMART BETTING ADVISOR - EXCEL INTEGRATION")
    print("="*70)
    
    print("\nThis tool analyzes your Excel predictions and provides")
    print("emotionless, data-driven betting recommendations.")
    
    # Setup
    print("\n" + "-"*70)
    bankroll = float(input("Enter bankroll ($): ").strip() or "1000")
    unit_pct = float(input("Enter base unit % (1-2% recommended): ").strip() or "1")
    
    advisor = SmartBettingAdvisor(bankroll=bankroll, base_unit_pct=unit_pct)
    
    print(f"\n✅ Advisor initialized")
    print(f"   Bankroll: ${bankroll:,.2f}")
    print(f"   Base unit: ${advisor.base_unit:.2f} ({unit_pct}%)")
    
    # Select mode
    print("\n" + "-"*70)
    print("Select mode:")
    print("1. Full analysis (with manual checks)")
    print("2. Quick preview (automated only)")
    print("3. Analyze specific player")
    print("4. Backtest mode (see what advisor would have recommended) ⭐")
    
    mode = input("\nChoice (1-4): ").strip()
    
    week = input("Enter week number: ").strip()
    
    if mode == '1':
        # Full analysis with manual checks
        recs = advisor.analyze_week(week, auto_mode=False, include_completed=False)
        if recs is not None:
            bets = advisor.generate_bet_summary(recs)
            
            if bets is not None and len(bets) > 0:
                save = input("\nSave bet slip? (y/n): ").strip().lower()
                if save == 'y':
                    advisor.save_bet_slip(bets, week)
    
    elif mode == '2':
        # Quick preview
        advisor.quick_preview(week)
    
    elif mode == '3':
        # Single player lookup
        player_name = input("Enter player name (e.g., P.Mahomes): ").strip()
        
        try:
            df = pd.read_excel('data/passing-prop-predictions-2025.xlsx', 
                             sheet_name=f'Week {week}')
            player_row = df[df['Player'] == player_name]
            
            if len(player_row) == 0:
                print(f"❌ {player_name} not found in Week {week}")
            else:
                advisor.analyze_prediction(player_row.iloc[0], show_manual_checks=True)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    elif mode == '4':
        # Backtest mode
        advisor.backtest_week(week)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()