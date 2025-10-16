# streamlit_app.py - Google Sheets Version with Batch Import, Excel Export & Betting Advisor
# Deploy to Streamlit Cloud for anywhere access

import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
from io import BytesIO

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.predictor import predict_prop
from src.config import PROPS_CONFIG

st.set_page_config(page_title="NFL Passing Yards Predictor", page_icon="🏈", layout="wide")

# Valid NFL teams
NFL_TEAMS = ['ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 
             'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 'LA', 'LAC', 'LV', 'MIA', 
             'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS']

# Custom CSS
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .bet-card {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .tier1 {
        background-color: #90EE90;
        border: 2px solid #32CD32;
    }
    .tier2 {
        background-color: #FFD700;
        border: 2px solid #FFA500;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏈 NFL QB Passing Yards Predictor")
st.markdown("### Make predictions from anywhere 🌍")

# Google Sheets Setup
@st.cache_resource
def get_google_sheets_client():
    """Connect to Google Sheets"""
    try:
        # Try Streamlit secrets first (for deployment)
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            # Local development - load from file
            with open('service_account.json') as f:
                creds_dict = json.load(f)
        
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets connection failed: {e}")
        return None

def get_or_create_worksheet(sheet_name, week):
    """Get or create worksheet for the week"""
    client = get_google_sheets_client()
    if not client:
        return None
    
    try:
        sheet = client.open(sheet_name)
        worksheet_name = f"Week {week}"
        
        try:
            worksheet = sheet.worksheet(worksheet_name)
        except:
            # Create new worksheet
            worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=13)
            headers = ['Player', 'Team', 'Opponent', 'Home/Away', 'Mean.Pred', 
                      'Vegas.Line', 'Actual', 'Prob.Over', 'Lean', 'Win.Loss', 
                      'P10', 'P50', 'P90']
            worksheet.append_row(headers)
            
            # Format header row
            worksheet.format('A1:M1', {
                "textFormat": {"bold": True},
                "horizontalAlignment": "CENTER"
            })
        
        return worksheet
    except Exception as e:
        st.error(f"Error accessing sheet: {e}")
        return None

def load_predictions_from_sheets(week):
    """Load existing predictions from Google Sheets"""
    worksheet = get_or_create_worksheet("NFL Passing Predictions 2025", week)
    if not worksheet:
        return pd.DataFrame()
    
    try:
        data = worksheet.get_all_values()
        if len(data) <= 1:
            return pd.DataFrame()
        
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Rename to internal format
        column_mapping = {
            'Player': 'player_name',
            'Team': 'posteam',
            'Opponent': 'defteam',
            'Home/Away': 'home_away',
            'Mean.Pred': 'mean_prediction',
            'Vegas.Line': 'line',
            'Actual': 'actual',
            'Prob.Over': 'prob_over_line',
            'Lean': 'lean',
            'Win.Loss': 'win_loss',
            'P10': 'p10',
            'P50': 'p50',
            'P90': 'p90'
        }
        df = df.rename(columns=column_mapping)
        
        # Convert numeric columns
        numeric_cols = ['mean_prediction', 'line', 'p10', 'p50', 'p90']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert prob_over_line from percentage string to float
        if 'prob_over_line' in df.columns:
            df['prob_over_line'] = df['prob_over_line'].apply(
                lambda x: float(str(x).rstrip('%')) / 100 if isinstance(x, str) and '%' in str(x) else float(x) if x else 0
            )
        
        return df
    except Exception as e:
        return pd.DataFrame()

def save_to_google_sheets(prediction_data, week, allow_overwrite=False):
    """Save prediction to Google Sheets"""
    worksheet = get_or_create_worksheet("NFL Passing Predictions 2025", week)
    if not worksheet:
        return False, "Google Sheets not connected"
    
    try:
        all_values = worksheet.get_all_values()
        player_name = prediction_data['player_name']
        
        # Check if player exists
        player_row = None
        for idx, row in enumerate(all_values[1:], start=2):
            if row[0] == player_name:
                player_row = idx
                break
        
        if player_row and not allow_overwrite:
            return False, "Player already exists. Enable 'Allow Overwrite' to update."
        
        # Format probability
        prob_str = f"{prediction_data['prob_over_line']:.1%}" if isinstance(prediction_data['prob_over_line'], (int, float)) else prediction_data['prob_over_line']
        
        # Create row (convert numpy floats to Python floats)
        new_row = [
            str(prediction_data['player_name']),
            str(prediction_data['posteam']),
            str(prediction_data['defteam']),
            str(prediction_data['home_away']),
            float(round(prediction_data['mean_prediction'], 1)),
            float(prediction_data['line']),
            '',
            prob_str,
            str(prediction_data['lean']),
            '',
            float(round(prediction_data['p10'], 1)),
            float(round(prediction_data['p50'], 1)),
            float(round(prediction_data['p90'], 1))
        ]
        
        if player_row:
            # Update existing row
            worksheet.update(f'A{player_row}:M{player_row}', [new_row])
            message = "Prediction updated!"
        else:
            # Append new row
            worksheet.append_row(new_row)
            player_row = len(all_values) + 1
            message = "Prediction saved!"
        
        # Format Lean column (green for OVER, red for UNDER)
        lean_cell = f"I{player_row}"
        if prediction_data['lean'] == 'OVER':
            worksheet.format(lean_cell, {
                "backgroundColor": {"red": 0.56, "green": 0.93, "blue": 0.56},
                "horizontalAlignment": "CENTER"
            })
        else:
            worksheet.format(lean_cell, {
                "backgroundColor": {"red": 1.0, "green": 0.71, "blue": 0.76},
                "horizontalAlignment": "CENTER"
            })
        
        return True, message
        
    except Exception as e:
        return False, f"Error saving: {str(e)}"

def export_to_excel(week):
    """Export Google Sheets data to Excel format for download"""
    try:
        df = load_predictions_from_sheets(week)
        if df.empty:
            return None
        
        # Rename columns to Excel format
        excel_df = df.rename(columns={
            'player_name': 'Player',
            'posteam': 'Team',
            'defteam': 'Opponent',
            'home_away': 'Home/Away',
            'mean_prediction': 'Mean.Pred',
            'line': 'Vegas.Line',
            'actual': 'Actual',
            'prob_over_line': 'Prob.Over',
            'lean': 'Lean',
            'win_loss': 'Win.Loss',
            'p10': 'P10',
            'p50': 'P50',
            'p90': 'P90'
        })
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            excel_df.to_excel(writer, sheet_name=f'Week {week}', index=False)
        
        return output.getvalue()
    except Exception as e:
        st.error(f"Export error: {e}")
        return None

# BETTING ADVISOR LOGIC
def calculate_bet_tier(row, bankroll, base_unit_pct):
    """
    Calculate betting tier for a prediction
    Returns: (tier, unit_size, reasoning)
    """
    try:
        mean_pred = float(row['mean_prediction'])
        vegas_line = float(row['line'])
        prob_over = float(row['prob_over_line'])
        home_away = str(row['home_away'])
        lean = str(row['lean'])
        
        edge = abs(mean_pred - vegas_line)
        is_home = (home_away.lower() == 'home')
        base_unit = bankroll * (base_unit_pct / 100)
        
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
        
        # TIER 0: Skip entirely
        if edge < 5:
            return 0, 0, "Edge too small (<5 yards)", confidence, model_prob
        
        # TIER 1: Full unit (optimal conditions)
        if (5 <= edge <= 20 and is_home and confidence in ['Medium', 'High']):
            tier = 1
            unit = base_unit
            reason = f"Optimal: {edge:.0f}y edge, Home, {confidence} confidence"
            return tier, unit, reason, confidence, model_prob
        
        # TIER 2: Half unit (decent but not optimal)
        else:
            tier = 2
            unit = base_unit * 0.5
            reasons = []
            if edge > 20:
                reasons.append(f"Large edge ({edge:.0f}y)")
            if not is_home:
                reasons.append("Away game")
            if confidence == 'Low':
                reasons.append(f"Low confidence ({model_prob:.0%})")
            
            reason = "Caution: " + ", ".join(reasons) if reasons else "Standard bet"
            return tier, unit, reason, confidence, model_prob
            
    except Exception as e:
        return 0, 0, f"Error: {str(e)}", 'N/A', 0

def analyze_week_for_betting(df, bankroll, base_unit_pct):
    """Analyze all predictions and return betting recommendations"""
    if df.empty:
        return pd.DataFrame()
    
    recommendations = []
    
    for idx, row in df.iterrows():
        tier, unit, reason, confidence, model_prob = calculate_bet_tier(row, bankroll, base_unit_pct)
        
        if tier > 0:  # Only include bets (skip tier 0)
            # Calculate expected value
            ev = (model_prob * unit * 0.909) - ((1 - model_prob) * unit)
            roi = (ev / unit * 100) if unit > 0 else 0
            
            recommendations.append({
                'player': row['player_name'],
                'matchup': f"{row['posteam']} vs {row['defteam']}",
                'location': row['home_away'],
                'prediction': row['mean_prediction'],
                'line': row['line'],
                'edge': abs(row['mean_prediction'] - row['line']),
                'lean': row['lean'],
                'prob': row['prob_over_line'],
                'confidence': confidence,
                'tier': tier,
                'unit': unit,
                'ev': ev,
                'roi': roi,
                'reason': reason
            })
    
    return pd.DataFrame(recommendations)

# Check if model is trained
if not os.path.exists('models/qb_passing_yards_model.pkl'):
    st.error("⚠️ Model not found! Please ensure model files are in the repository.")
    st.stop()

# Load player data
@st.cache_data
def load_player_data():
    try:
        player_df = pd.read_csv('data/passing_yards_player_logs.csv')
        return player_df
    except FileNotFoundError:
        st.error("❌ Player data not found.")
        return None

@st.cache_data
def get_qb_list(player_df):
    """Filter to only QBs"""
    qb_threshold = 50
    qb_stats = player_df.groupby('player_name').agg({
        'pass_attempts': 'sum',
        'passing_yards': 'sum'
    }).reset_index()
    qbs = qb_stats[qb_stats['pass_attempts'] >= qb_threshold]['player_name'].tolist()
    return sorted(qbs)

player_data = load_player_data()

if player_data is not None:
    qb_list = get_qb_list(player_data)
    max_week_in_data = player_data[player_data['season'] == 2025]['week'].max()
    
    # Connection status
    client = get_google_sheets_client()
    if client:
        st.success("✅ Connected to Google Sheets")
    else:
        st.error("❌ Google Sheets not connected. Check your service account setup.")
        st.stop()
    
    st.info(f"📊 Model trained through 2025 Week {max_week_in_data}")
    
    # Tabs for different modes
    tab1, tab2, tab3, tab4 = st.tabs(["📱 Single Prediction", "⚡ Batch Import", "📊 View & Export", "💰 Betting Advisor"])
    
    # TAB 1: Single Prediction (keep existing code)
    with tab1:
        # [Keep all existing tab1 code - not showing here to save space]
        # Sidebar inputs
        st.sidebar.header("🎯 Prediction Inputs")
        
        season = 2025
        week = st.sidebar.number_input("Week to Predict", min_value=1, max_value=18, 
                                        value=min(max_week_in_data + 1, 18))
        
        # Load existing predictions
        existing_predictions = load_predictions_from_sheets(week)
        if len(existing_predictions) > 0:
            st.sidebar.success(f"✅ {len(existing_predictions)} predictions saved for Week {week}")
            with st.sidebar.expander("View Saved Predictions"):
                display_cols = ['player_name', 'mean_prediction', 'line', 'lean']
                available_cols = [c for c in display_cols if c in existing_predictions.columns]
                if available_cols:
                    st.dataframe(existing_predictions[available_cols], use_container_width=True, hide_index=True)
        else:
            st.sidebar.info(f"📝 No predictions saved for Week {week}")
        
        # Player selection
        player_name = st.sidebar.selectbox("Select QB", options=qb_list)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            posteam = st.selectbox("QB's Team", options=NFL_TEAMS)
        with col2:
            defteam = st.selectbox("Opponent", options=NFL_TEAMS)
        
        line = st.sidebar.number_input("Vegas Line (yards)", min_value=0.0, max_value=500.0, value=250.5, step=0.5)
        is_home = st.sidebar.radio("Location", options=["Away", "Home"], index=0)
        is_home_val = 1 if is_home == "Home" else 0
        
        save_to_file = st.sidebar.checkbox("💾 Save to Google Sheets", value=True)
        allow_overwrite = st.sidebar.checkbox("🔄 Allow Overwrite", value=False)
        
        if st.sidebar.button("🎯 Generate Prediction", type="primary", use_container_width=True):
            config = PROPS_CONFIG['qb_passing_yards']
            min_games = config.get('min_games', 10)
            
            player_history = player_data[
                (player_data['player_name'] == player_name) & 
                ((player_data['season'] < season) | 
                 ((player_data['season'] == season) & (player_data['week'] < week)))
            ]
            
            game_count = len(player_history)
            
            if game_count < min_games:
                st.error(f"❌ Insufficient data: {player_name} has only {game_count} games. Min: {min_games}")
            else:
                with st.spinner("🔮 Generating prediction..."):
                    try:
                        result = predict_prop('qb_passing_yards', player_name, posteam, defteam, 
                                            line, season, week, is_home_val)
                        
                        st.session_state['last_prediction'] = {
                            'player_name': player_name,
                            'posteam': posteam,
                            'defteam': defteam,
                            'home_away': is_home,
                            'mean_prediction': result['mean_prediction'],
                            'line': line,
                            'prob_over_line': result['prob_over_line'],
                            'lean': 'OVER' if result['mean_prediction'] > line else 'UNDER',
                            'p10': result['p10'],
                            'p50': result['p50'],
                            'p90': result['p90'],
                            'week': week,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        if save_to_file:
                            success, message = save_to_google_sheets(st.session_state['last_prediction'], 
                                                                    week, allow_overwrite)
                            if success:
                                st.success(f"✅ {message}")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.warning(f"⚠️ {message}")
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.exception(e)
        
        # Display last prediction
        if 'last_prediction' in st.session_state:
            pred = st.session_state['last_prediction']
            
            st.success("✅ Prediction Complete!")
            
            col1, col2, col3 = st.columns(3)
            delta_val = pred['mean_prediction'] - pred['line']
            
            with col1:
                st.metric("📊 Mean Prediction", f"{pred['mean_prediction']:.1f} yds",
                         delta=f"{delta_val:+.1f} vs line")
            with col2:
                st.metric("🎰 Vegas Line", f"{pred['line']:.1f} yds")
            with col3:
                prob = pred['prob_over_line']
                st.metric("📈 Probability Over", f"{prob:.1%}")
            
            st.markdown("---")
            
            lean = pred['lean']
            confidence = abs(pred['mean_prediction'] - pred['line'])
            
            if lean == "OVER":
                if confidence > 15:
                    st.success(f"### 🔥 **Strong {lean}** - {confidence:.1f} yard edge")
                else:
                    st.success(f"### 📈 **Lean {lean}** - {confidence:.1f} yard edge")
            else:
                if confidence > 15:
                    st.info(f"### 🔥 **Strong {lean}** - {confidence:.1f} yard edge")
                else:
                    st.info(f"### 📉 **Lean {lean}** - {confidence:.1f} yard edge")
            
            st.markdown("---")
            st.subheader("📊 Prediction Range")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("P10", f"{pred['p10']:.0f} yds")
            with col2:
                st.metric("P50", f"{pred['p50']:.0f} yds")
            with col3:
                st.metric("P90", f"{pred['p90']:.0f} yds")
    
    # TAB 2 & 3: Keep existing code
    # [Not showing to save space - keep all existing code]
    
    # TAB 4: BETTING ADVISOR (NEW)
    with tab4:
        st.subheader("💰 Smart Betting Advisor")
        st.write("Get data-driven bet recommendations based on your predictions")
        
        # Settings
        col1, col2 = st.columns(2)
        with col1:
            advisor_week = st.number_input("Week to Analyze", min_value=1, max_value=18, 
                                          value=min(max_week_in_data + 1, 18), key="advisor_week")
        with col2:
            bankroll = st.number_input("Bankroll ($)", min_value=100, max_value=10000, 
                                      value=300, step=50, key="advisor_bankroll")
        
        col3, col4 = st.columns(2)
        with col3:
            unit_pct = st.number_input("Base Unit %", min_value=0.5, max_value=5.0, 
                                      value=2.0, step=0.5, key="advisor_unit")
        with col4:
            base_unit = bankroll * (unit_pct / 100)
            st.metric("Base Unit", f"${base_unit:.2f}")
        
        if st.button("🎯 Analyze Bets", type="primary", use_container_width=True):
            with st.spinner("Analyzing predictions..."):
                predictions_df = load_predictions_from_sheets(advisor_week)
                
                if predictions_df.empty:
                    st.warning(f"⚠️ No predictions found for Week {advisor_week}")
                else:
                    # Analyze for bets
                    bets_df = analyze_week_for_betting(predictions_df, bankroll, unit_pct)
                    
                    if bets_df.empty:
                        st.info("📝 No bets meet the criteria for this week")
                    else:
                        # Summary metrics
                        tier1_bets = bets_df[bets_df['tier'] == 1]
                        tier2_bets = bets_df[bets_df['tier'] == 2]
                        
                        st.success(f"✅ {len(bets_df)} Bets Recommended")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Tier 1 Bets", len(tier1_bets))
                        with col2:
                            st.metric("Tier 2 Bets", len(tier2_bets))
                        with col3:
                            st.metric("Total Risk", f"${bets_df['unit'].sum():.2f}")
                        with col4:
                            st.metric("Expected EV", f"${bets_df['ev'].sum():.2f}")
                        
                        st.markdown("---")
                        
                        # Display bets by tier
                        st.subheader("🔥 Tier 1 Bets (Full Unit)")
                        if len(tier1_bets) > 0:
                            for _, bet in tier1_bets.iterrows():
                                st.markdown(f"""
                                <div class="bet-card tier1">
                                    <h4>🏈 {bet['player']} - {bet['lean']}</h4>
                                    <p><strong>Matchup:</strong> {bet['matchup']} ({bet['location']})</p>
                                    <p><strong>Line:</strong> {bet['line']:.1f} | <strong>Prediction:</strong> {bet['prediction']:.1f} | <strong>Edge:</strong> {bet['edge']:.1f} yards</p>
                                    <p><strong>Probability:</strong> {bet['prob']:.1%} | <strong>Confidence:</strong> {bet['confidence']}</p>
                                    <p><strong>💰 Bet:</strong> ${bet['unit']:.2f} | <strong>Expected EV:</strong> ${bet['ev']:.2f} ({bet['roi']:.1f}% ROI)</p>
                                    <p><em>{bet['reason']}</em></p>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("No Tier 1 bets this week")
                        
                        st.markdown("---")
                        st.subheader("⚠️ Tier 2 Bets (Half Unit)")
                        if len(tier2_bets) > 0:
                            for _, bet in tier2_bets.iterrows():
                                st.markdown(f"""
                                <div class="bet-card tier2">
                                    <h4>🏈 {bet['player']} - {bet['lean']}</h4>
                                    <p><strong>Matchup:</strong> {bet['matchup']} ({bet['location']})</p>
                                    <p><strong>Line:</strong> {bet['line']:.1f} | <strong>Prediction:</strong> {bet['prediction']:.1f} | <strong>Edge:</strong> {bet['edge']:.1f} yards</p>
                                    <p><strong>Probability:</strong> {bet['prob']:.1%} | <strong>Confidence:</strong> {bet['confidence']}</p>
                                    <p><strong>💰 Bet:</strong> ${bet['unit']:.2f} | <strong>Expected EV:</strong> ${bet['ev']:.2f} ({bet['roi']:.1f}% ROI)</p>
                                    <p><em>{bet['reason']}</em></p>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("No Tier 2 bets this week")
                        
                        # Export bets summary
                        st.markdown("---")
                        st.subheader("📥 Export Bet Slip")
                        
                        bet_slip = bets_df[['player', 'lean', 'line', 'prediction', 'edge', 
                                           'prob', 'tier', 'unit', 'ev', 'roi']].copy()
                        bet_slip.columns = ['Player', 'Lean', 'Line', 'Prediction', 'Edge', 
                                           'Probability', 'Tier', 'Unit ($)', 'EV ($)', 'ROI (%)']
                        
                        csv = bet_slip.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Bet Slip (CSV)",
                            data=csv,
                            file_name=f"bet-slip-week-{advisor_week}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
    
    # Footer
    st.markdown("---")
    st.info("""
    **🔄 Workflow:**
    1. Train model locally with latest data
    2. Push updated model files to GitHub
    3. Streamlit Cloud auto-deploys
    4. Make predictions from anywhere!
    5. Get betting recommendations on your phone!
    """)

else:
    st.error("❌ Unable to load player data.")

st.markdown("---")
st.caption("🏈 *Built with Streamlit | Data from nflfastR | Model: XGBoost*")