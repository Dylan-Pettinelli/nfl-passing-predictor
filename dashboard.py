# dashboard.py
# Generate visual HTML dashboard of model performance

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def generate_html_dashboard(output_file='data/dashboard.html'):
    """Generate interactive HTML dashboard"""
    
    try:
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
            print("❌ No completed predictions to display")
            return
        
        df = pd.concat(all_data, ignore_index=True)
        df['Mean.Pred'] = pd.to_numeric(df['Mean.Pred'], errors='coerce')
        df['Vegas.Line'] = pd.to_numeric(df['Vegas.Line'], errors='coerce')
        df['Actual'] = pd.to_numeric(df['Actual'], errors='coerce')
        
        # Calculate metrics
        df['abs_error'] = abs(df['Mean.Pred'] - df['Actual'])
        df['vegas_error'] = abs(df['Vegas.Line'] - df['Actual'])
        df['beat_vegas'] = df['abs_error'] < df['vegas_error']
        
        wins = (df['Win.Loss'] == 'W').sum()
        losses = (df['Win.Loss'] == 'L').sum()
        win_rate = wins / (wins + losses) * 100
        
        # Weekly stats
        weekly_stats = []
        for week in sorted(df['Week'].unique()):
            week_df = df[df['Week'] == week]
            week_wins = (week_df['Win.Loss'] == 'W').sum()
            week_total = len(week_df)
            weekly_stats.append({
                'week': week,
                'wins': week_wins,
                'total': week_total,
                'win_rate': (week_wins / week_total * 100) if week_total > 0 else 0
            })
        
        # Generate HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NFL Prediction Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #2d3748;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .subtitle {{
            color: #718096;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-card.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}
        .metric-card.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f7fafc;
            border-radius: 8px;
        }}
        .chart-title {{
            font-size: 1.3em;
            color: #2d3748;
            margin-bottom: 15px;
            font-weight: 600;
        }}
        .bar {{
            height: 30px;
            margin: 10px 0;
            border-radius: 4px;
            display: flex;
            align-items: center;
            padding-left: 10px;
            color: white;
            font-weight: 500;
            transition: all 0.3s;
        }}
        .bar:hover {{
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        .bar.green {{ background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%); }}
        .bar.red {{ background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%); }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
        }}
        tr:hover {{
            background: #f7fafc;
        }}
        .win {{ color: #38a169; font-weight: bold; }}
        .loss {{ color: #e53e3e; font-weight: bold; }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #718096;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏈 NFL Passing Yards Prediction Dashboard</h1>
        <div class="subtitle">Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
        
        <div class="metrics-grid">
            <div class="metric-card {'success' if win_rate >= 52.38 else 'warning'}">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value">{win_rate:.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Record</div>
                <div class="metric-value">{wins}-{losses}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Model MAE</div>
                <div class="metric-value">{df['abs_error'].mean():.1f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Beat Vegas</div>
                <div class="metric-value">{df['beat_vegas'].mean()*100:.1f}%</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">📈 Weekly Performance</div>
"""
        
        # Add weekly bars
        for stat in weekly_stats:
            width_pct = stat['win_rate']
            color = 'green' if stat['win_rate'] >= 52.38 else 'red'
            html += f"""
            <div class="bar {color}" style="width: {width_pct}%;">
                {stat['week']}: {stat['wins']}/{stat['total']} ({stat['win_rate']:.1f}%)
            </div>
"""
        
        html += """
        </div>
        
        <div class="chart-container">
            <div class="chart-title">🎯 Over vs Under Performance</div>
"""
        
        # Over/Under breakdown
        over_df = df[df['Lean'] == 'OVER']
        under_df = df[df['Lean'] == 'UNDER']
        
        if len(over_df) > 0:
            over_wins = (over_df['Win.Loss'] == 'W').sum()
            over_wr = over_wins / len(over_df) * 100
            over_color = 'green' if over_wr >= 52.38 else 'red'
            html += f"""
            <div class="bar {over_color}" style="width: {over_wr}%;">
                OVER: {over_wins}/{len(over_df)} ({over_wr:.1f}%)
            </div>
"""
        
        if len(under_df) > 0:
            under_wins = (under_df['Win.Loss'] == 'W').sum()
            under_wr = under_wins / len(under_df) * 100
            under_color = 'green' if under_wr >= 52.38 else 'red'
            html += f"""
            <div class="bar {under_color}" style="width: {under_wr}%;">
                UNDER: {under_wins}/{len(under_df)} ({under_wr:.1f}%)
            </div>
"""
        
        html += """
        </div>
        
        <div class="chart-container">
            <div class="chart-title">🏆 Best Predictions (Lowest Error)</div>
            <table>
                <tr>
                    <th>Player</th>
                    <th>Week</th>
                    <th>Predicted</th>
                    <th>Actual</th>
                    <th>Error</th>
                    <th>Result</th>
                </tr>
"""
        
        # Best predictions
        best = df.nsmallest(10, 'abs_error')
        for _, row in best.iterrows():
            result_class = 'win' if row['Win.Loss'] == 'W' else 'loss'
            html += f"""
                <tr>
                    <td>{row['Player']}</td>
                    <td>{row['Week']}</td>
                    <td>{row['Mean.Pred']:.0f}</td>
                    <td>{row['Actual']:.0f}</td>
                    <td>{row['abs_error']:.1f}</td>
                    <td class="{result_class}">{row['Win.Loss']}</td>
                </tr>
"""
        
        html += """
            </table>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">⚠️ Worst Predictions (Highest Error)</div>
            <table>
                <tr>
                    <th>Player</th>
                    <th>Week</th>
                    <th>Predicted</th>
                    <th>Actual</th>
                    <th>Error</th>
                    <th>Result</th>
                </tr>
"""
        
        # Worst predictions
        worst = df.nlargest(10, 'abs_error')
        for _, row in worst.iterrows():
            result_class = 'win' if row['Win.Loss'] == 'W' else 'loss'
            html += f"""
                <tr>
                    <td>{row['Player']}</td>
                    <td>{row['Week']}</td>
                    <td>{row['Mean.Pred']:.0f}</td>
                    <td>{row['Actual']:.0f}</td>
                    <td>{row['abs_error']:.1f}</td>
                    <td class="{result_class}">{row['Win.Loss']}</td>
                </tr>
"""
        
        html += f"""
            </table>
        </div>
        
        <div class="footer">
            Dashboard generated from {len(df)} completed predictions across {len(df['Week'].unique())} weeks
        </div>
    </div>
</body>
</html>
"""
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Dashboard generated: {output_file}")
        print(f"   Open this file in your browser to view")
        
        # Try to open in browser
        import webbrowser
        try:
            webbrowser.open(f'file://{Path(output_file).absolute()}')
            print("   Opening in browser...")
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error generating dashboard: {e}")

if __name__ == "__main__":
    generate_html_dashboard()