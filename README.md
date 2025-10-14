NFL PASSING YARDS PREDICTION SYSTEM
Quick Start Guide

==============================================================================
WHAT IS THIS?
==============================================================================

A machine learning system that predicts NFL QB passing yards and gives you
systematic betting recommendations.

Works on desktop AND mobile (via Streamlit Cloud).

Current Performance: 82-68 (54.7%) - PROFITABLE!

==============================================================================
WEEKLY WORKFLOW
==============================================================================

MONDAY NIGHT - Update Results (5 min)
--------------------------------------
Rscript src/update_actuals.R 6

Replace "6" with the week that just finished.
Fetches results from nflfastR and updates Excel automatically.


TUESDAY MORNING - Retrain Model (10 min)
-----------------------------------------
python -m src.train_pipeline

Retrains model with latest NFL data. Do this once per week.


TUESDAY - Thursday Night Game (10 min)
---------------------------------------
Desktop:
  python predict_upcoming.py
  python smart_betting_advisor.py

Mobile:
  Open Streamlit app on phone
  Make predictions anywhere
  Syncs to Google Sheets


THURSDAY - Weekend Games (30 min)
----------------------------------
Desktop:
  python predict_upcoming.py
  python smart_betting_advisor.py

Mobile:
  Use Streamlit app if away from computer


That's it! 30-40 minutes per week total.

==============================================================================
MOBILE ACCESS (Streamlit Cloud)
==============================================================================

Your Streamlit app lets you:
  ✓ Make predictions from phone/tablet
  ✓ Saves to Google Sheets automatically
  ✓ Batch import multiple predictions
  ✓ Export to Excel format
  ✓ View all predictions on the go

Perfect for when lines drop and you're not at your computer!

To use:
  1. Open Streamlit Cloud URL (bookmark it!)
  2. Select week and QB
  3. Enter Vegas line
  4. Generate prediction
  5. Auto-saves to Google Sheets

Later:
  Export from Streamlit → Copy to main Excel file

==============================================================================
UNDERSTANDING BETTING TIERS
==============================================================================

The advisor automatically assigns each bet to a tier:

TIER 1 - Full Unit ($3 with $300 bankroll)
  All of these must be true:
  ✓ Edge: 5-20 yards (sweet spot)
  ✓ Home game
  ✓ Medium or High confidence
  ✓ No red flags
  
  Expected: 58-60% win rate
  Action: BET IT!

TIER 2 - Half Unit ($1.50)
  One of these is true:
  • Edge >20 yards (Vegas may know something)
  • Away game
  • Lower confidence
  But still passes injury/weather checks
  
  Expected: 50-52% win rate
  Action: BET IT!

TIER 0 - Skip
  • Edge <5 yards (too close)
  • 2+ red flags
  
  Action: SKIP IT!

==============================================================================
THE 5 QUICK CHECKS (Takes 2 Minutes Per Bet)
==============================================================================

The advisor asks these questions for every bet:

1. Is QB Questionable/Doubtful?
   Check: FantasyPros.com injury report

2. Are top 2 WRs out?
   Check: Team injury reports

3. 3+ O-line starters injured?
   Check: Team depth charts

4. Extreme weather? (25+ MPH wind or heavy rain)
   Check: Weather.com for game location

5. Backup QB's first start?
   Check: Team starting lineup

Answer "yes" to any → Bet gets flagged (might become Tier 2 or Skip)

==============================================================================
DESKTOP COMMANDS
==============================================================================

Main Workflow
-------------
python predict_upcoming.py        Make predictions
python smart_betting_advisor.py   Get betting advice (MOST IMPORTANT!)
Rscript src/update_actuals.R 6   Update results
python -m src.train_pipeline      Retrain model

Analysis & Reports
------------------
python diagnostics.py             Full performance analysis
python dashboard.py               Visual HTML report
python quick_actions.py           All-in-one convenience menu
python tune_advisor.py           Review betting logic

Utilities
---------
python validate_setup.py          Check installation

==============================================================================
BATCH PREDICTIONS
==============================================================================

Desktop - CSV Import:
  1. Create CSV in batch-imports/ folder
  2. python predict_upcoming.py → Batch import

Mobile - Streamlit Batch:
  1. Open Streamlit app
  2. Go to "Batch Import" tab
  3. Paste: Player, Team, Opp, Line, Home/Away
  4. Process all at once

==============================================================================
YOUR FILES
==============================================================================

Main Scripts:
  predict_upcoming.py       Desktop predictions
  smart_betting_advisor.py  Betting advice
  diagnostics.py            Performance analysis
  dashboard.py              Visual reports
  quick_actions.py          All-in-one menu
  tune_advisor.py          Review logic
  validate_setup.py         System check
  streamlit_app.py         Mobile interface

Data:
  data/passing-prop-predictions-2025.xlsx  Your main predictions
  data/*_logs.csv                          Historical NFL data
  data/backups/                            Auto backups
  data/dashboard.html                      Latest report

Models:
  models/*.pkl  Trained model files

Source:
  src/  Internal code
  src/update_actuals.R  Updates results

Batch:
  batch-imports/  CSV templates

Cloud:
  .streamlit/secrets.toml   Google Sheets credentials
  service_account.json      Google Cloud auth

==============================================================================
TROUBLESHOOTING
==============================================================================

"Player not found"
------------------
Format: "P.Mahomes" not "Patrick Mahomes"
Needs 10+ historical games

Check: python quick_actions.py → Option 14


Predictions seem off
--------------------
Did you retrain this week?
python -m src.train_pipeline


Streamlit app not connecting
-----------------------------
Check service_account.json is in root folder
Or update secrets in Streamlit Cloud dashboard


Excel won't open
----------------
python quick_actions.py → Option 12
Creates backup in data/backups/


Installation issues
-------------------
python validate_setup.py

==============================================================================
BANKROLL MANAGEMENT
==============================================================================

Recommended:
  Starting: $300-1000
  Base unit: 1% of bankroll
  Weekly risk: $15-30 (5-10 bets)

Example ($300 bankroll):
  Base unit: $3.00
  Tier 1: $3.00 per bet (full)
  Tier 2: $1.50 per bet (half)

Recalculate monthly:
  Bankroll $400 → Unit $4.00
  Bankroll $250 → Unit $2.50

Never bet >3% on one game.

==============================================================================
THE 3 RULES
==============================================================================

1. TRUST THE TIERS
   Follow recommendations
   Don't second-guess

2. ANSWER CHECKS HONESTLY
   5 questions per bet
   2 minutes well spent

3. DON'T CHERRY-PICK
   Your gut: ~50%
   System: 54.7%
   
   Your emotions cost you 4.7%

==============================================================================
MOBILE WORKFLOW TIPS
==============================================================================

When away from computer:
  1. Bookmark Streamlit app URL
  2. Make predictions on phone
  3. Saves to Google Sheets automatically
  4. Later: Export to Excel and merge with main file

When at computer:
  1. Use desktop scripts (faster)
  2. Get betting advice from smart_betting_advisor.py
  3. More features available

Best of both worlds!

==============================================================================
CURRENT PERFORMANCE (150 Bets)
==============================================================================

Overall:        82-68 (54.7%) ✓ PROFITABLE
Home Games:     57.3% win rate ✓ STRONG  
Away Games:     52.0% win rate ✓ OK
Optimal Edge:   5-20 yards = 60% win rate
Large Edge:     20-50 yards = 45% (Vegas knows!)

Problem Players: R.Wilson, J.Fields, M.Stafford
                 (70+ yard avg errors - auto-flagged)

==============================================================================
QUICK REFERENCE
==============================================================================

Monday:    Rscript src/update_actuals.R [week]
Tuesday:   python -m src.train_pipeline
Tuesday:   python predict_upcoming.py
Tuesday:   python smart_betting_advisor.py
Thursday:  python predict_upcoming.py  
Thursday:  python smart_betting_advisor.py

Anytime:   python quick_actions.py (convenience menu)
Anytime:   python diagnostics.py (check performance)
Anytime:   python dashboard.py (visual report)

Mobile:    Open Streamlit app (make predictions anywhere!)

==============================================================================
SYSTEM STATUS
==============================================================================

Status: FULLY OPERATIONAL ✓
Platforms: Desktop + Mobile (Streamlit Cloud)

Your edge: +2.32% over breakeven (52.38%)
Expected ROI: ~2.4% per bet
Expected season profit: 10-20% bankroll growth

Trust the system. Follow the tiers. Be patient.

Questions? → python quick_actions.py
On the go? → Streamlit app

==============================================================================
WEEKLY CHECKLIST (Copy This!)
==============================================================================

MONDAY NIGHT
------------
[ ] Rscript src/update_actuals.R 6
    (Updates last week's results - takes 5 min)


TUESDAY MORNING
---------------
[ ] python -m src.train_pipeline
    (Retrains model - takes 10 min, grab coffee)


TUESDAY AFTERNOON (Thursday Game)
----------------------------------
[ ] python predict_upcoming.py
    (Add Thursday game prediction)

[ ] python smart_betting_advisor.py
    (Get betting advice, answer 5 questions, place bet)


THURSDAY AFTERNOON (Weekend Games)
-----------------------------------
[ ] python predict_upcoming.py
    (Add Sunday/Monday predictions)

[ ] python smart_betting_advisor.py
    (Get betting advice for all bets, place them)


THAT'S IT!
----------
30-40 minutes total per week
Set reminders on your phone for each day

Optional:
  - Every 2 weeks: python diagnostics.py (check performance)
  - Anytime: python quick_actions.py (convenience menu)
  - Away from PC: Use Streamlit app on phone


REMEMBER:
  Trust the tiers
  Answer injury checks honestly
  Don't cherry-pick
  Be patient - need 50+ bets to see results