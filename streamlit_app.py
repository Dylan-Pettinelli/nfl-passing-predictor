# streamlit_app.py - Google Sheets Version with Batch Import & Excel Export
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
    tab1, tab2, tab3 = st.tabs(["📱 Single Prediction", "⚡ Batch Import", "📊 View & Export"])
    
    # TAB 1: Single Prediction
    with tab1:
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
            
            st.markdown("---")
            st.subheader("🏈 Game Details")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Player:** {pred['player_name']}")
                st.write(f"**Matchup:** {pred['posteam']} vs {pred['defteam']}")
            with col2:
                st.write(f"**Location:** {pred['home_away']}")
                st.write(f"**Week {pred['week']}, {season}**")
            
            # Recent performance
            player_history_display = player_data[
                (player_data['player_name'] == pred['player_name']) & 
                ((player_data['season'] < season) | 
                 ((player_data['season'] == season) & (player_data['week'] < pred['week'])))
            ]
            
            recent_games = player_history_display.tail(5)
            if len(recent_games) > 0:
                st.markdown("---")
                st.subheader("📜 Recent Performance")
                
                avg_recent = recent_games['passing_yards'].mean()
                last_game = recent_games['passing_yards'].iloc[-1]
                game_count = len(player_history_display)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Last 5 Avg", f"{avg_recent:.0f} yds")
                with col2:
                    st.metric("Last Game", f"{last_game:.0f} yds")
                with col3:
                    st.metric("Total Games", f"{game_count}")
    
    # TAB 2: Batch Import
    with tab2:
        st.subheader("⚡ Batch Predictions")
        st.write("Enter multiple predictions at once (one per line)")
        
        st.info("**Format:** `Player Name, Team, Opponent, Line, Home/Away`")
        st.caption("Example: `P.Mahomes, KC, LV, 265.5, Home`")
        
        batch_week = st.number_input("Week for Batch", min_value=1, max_value=18, 
                                     value=min(max_week_in_data + 1, 18), key="batch_week")
        
        batch_input = st.text_area(
            "Batch Input",
            height=200,
            placeholder="P.Mahomes, KC, LV, 265.5, Home\nJ.Allen, BUF, MIA, 250.5, Away\nL.Jackson, BAL, CIN, 240.5, Home",
            help="One prediction per line"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            batch_save = st.checkbox("💾 Save All to Sheets", value=True, key="batch_save")
        with col2:
            batch_overwrite = st.checkbox("🔄 Allow Overwrite", value=True, key="batch_overwrite")
        
        if st.button("🚀 Process Batch Predictions", type="primary", use_container_width=True):
            if not batch_input.strip():
                st.warning("⚠️ Please enter at least one prediction")
            else:
                lines = [line.strip() for line in batch_input.split('\n') if line.strip()]
                batch_results = []
                errors = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, line_text in enumerate(lines):
                    try:
                        status_text.text(f"Processing {idx+1}/{len(lines)}...")
                        progress_bar.progress((idx + 1) / len(lines))
                        
                        parts = [p.strip() for p in line_text.split(',')]
                        if len(parts) != 5:
                            errors.append(f"❌ Invalid format: {line_text}")
                            continue
                        
                        b_player, b_team, b_opp, b_line, b_location = parts
                        b_is_home = 1 if b_location.lower() == 'home' else 0
                        b_line_float = float(b_line)
                        b_team = b_team.upper()
                        b_opp = b_opp.upper()
                        
                        # Find matching QB
                        matching_qbs = [q for q in qb_list if b_player.lower() in q.lower()]
                        if not matching_qbs:
                            errors.append(f"❌ QB not found: {b_player}")
                            continue
                        
                        b_player = matching_qbs[0]
                        
                        # Validate teams
                        if b_team not in NFL_TEAMS:
                            errors.append(f"❌ Invalid team: {b_team}")
                            continue
                        if b_opp not in NFL_TEAMS:
                            errors.append(f"❌ Invalid opponent: {b_opp}")
                            continue
                        
                        # Generate prediction
                        result = predict_prop('qb_passing_yards', b_player, b_team, 
                                            b_opp, b_line_float, 2025, batch_week, b_is_home)
                        
                        pred_data = {
                            'player_name': b_player,
                            'posteam': b_team,
                            'defteam': b_opp,
                            'home_away': b_location,
                            'mean_prediction': result['mean_prediction'],
                            'line': b_line_float,
                            'prob_over_line': result['prob_over_line'],
                            'lean': 'OVER' if result['mean_prediction'] > b_line_float else 'UNDER',
                            'p10': result['p10'],
                            'p50': result['p50'],
                            'p90': result['p90']
                        }
                        
                        if batch_save:
                            success, msg = save_to_google_sheets(pred_data, batch_week, batch_overwrite)
                            if not success and "already exists" not in msg:
                                errors.append(f"❌ Save failed for {b_player}: {msg}")
                        
                        batch_results.append(pred_data)
                        
                    except Exception as e:
                        errors.append(f"❌ Error with {line_text}: {str(e)}")
                
                progress_bar.empty()
                status_text.empty()
                
                if batch_results:
                    st.success(f"✅ Processed {len(batch_results)} predictions!")
                    
                    # Show results table
                    results_df = pd.DataFrame(batch_results)
                    display_df = results_df[['player_name', 'posteam', 'defteam', 'mean_prediction', 'line', 'lean']].copy()
                    display_df['mean_prediction'] = display_df['mean_prediction'].round(1)
                    display_df = display_df.rename(columns={
                        'player_name': 'Player',
                        'posteam': 'Team',
                        'defteam': 'Opp',
                        'mean_prediction': 'Prediction',
                        'line': 'Line',
                        'lean': 'Lean'
                    })
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    st.cache_data.clear()
                
                if errors:
                    st.error("**Errors:**")
                    for error in errors:
                        st.write(error)
    
    # TAB 3: View & Export
    with tab3:
        st.subheader("📊 View Predictions & Export to Excel")
        
        view_week = st.number_input("Select Week to View", min_value=1, max_value=18, 
                                     value=min(max_week_in_data + 1, 18), key="view_week")
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        predictions_df = load_predictions_from_sheets(view_week)
        
        if not predictions_df.empty:
            st.success(f"✅ {len(predictions_df)} predictions found for Week {view_week}")
            
            # Display table
            display_cols = ['player_name', 'posteam', 'defteam', 'home_away', 'mean_prediction', 
                           'line', 'prob_over_line', 'lean', 'p10', 'p50', 'p90']
            available_cols = [c for c in display_cols if c in predictions_df.columns]
            
            if available_cols:
                display_df = predictions_df[available_cols].copy()
                
                # Format for display
                if 'mean_prediction' in display_df.columns:
                    display_df['mean_prediction'] = pd.to_numeric(display_df['mean_prediction'], errors='coerce').round(1)
                if 'line' in display_df.columns:
                    display_df['line'] = pd.to_numeric(display_df['line'], errors='coerce')
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Export to Excel
            st.markdown("---")
            st.subheader("📥 Export to Excel")
            st.write("Download this week's predictions in Excel format (perfect for copying to your main spreadsheet!)")
            
            excel_data = export_to_excel(view_week)
            if excel_data:
                st.download_button(
                    label="📥 Download Week {} as Excel".format(view_week),
                    data=excel_data,
                    file_name=f"nfl-predictions-week-{view_week}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            # Link to Google Sheet
            st.markdown("---")
            st.markdown("### 🔗 Open in Google Sheets")
            st.markdown("[View in Google Sheets →](https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID)")
            st.caption("💡 Tip: Replace YOUR_SHEET_ID in the code with your actual Sheet ID")
            
        else:
            st.info(f"📝 No predictions saved for Week {view_week}")
    
    # Footer
    st.markdown("---")
    st.info("""
    **🔄 Workflow:**
    1. Train model locally with latest data
    2. Push updated model files to GitHub
    3. Streamlit Cloud auto-deploys
    4. Make predictions from anywhere!
    5. Export to Excel when needed
    """)

else:
    st.error("❌ Unable to load player data.")

st.markdown("---")
st.caption("🏈 *Built with Streamlit | Data from nflfastR | Model: XGBoost*")