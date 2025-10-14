# validate_setup.py
# Comprehensive validation of entire setup and dependencies

import os
import sys
import subprocess
import importlib
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)

def check_python_version():
    """Check Python version"""
    print_header("Python Version")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("✅ Python version is compatible")
        return True
    else:
        print("❌ Python 3.8+ required")
        return False

def check_python_packages():
    """Check required Python packages"""
    print_header("Python Packages")
    
    required = {
        'pandas': '1.3.0',
        'numpy': '1.20.0',
        'scikit-learn': '1.0.0',
        'xgboost': '1.5.0',
        'joblib': '1.0.0',
        'openpyxl': '3.0.0'
    }
    
    all_good = True
    for package, min_version in required.items():
        try:
            mod = importlib.import_module(package.replace('-', '_'))
            version = getattr(mod, '__version__', 'unknown')
            print(f"✅ {package}: {version}")
        except ImportError:
            print(f"❌ {package}: NOT INSTALLED")
            all_good = False
    
    return all_good

def check_r_installation():
    """Check R and required packages"""
    print_header("R Installation")
    
    try:
        result = subprocess.run(['Rscript', '--version'], 
                              capture_output=True, text=True)
        print(f"✅ R installed: {result.stderr.split()[2]}")
        
        # Check R packages
        r_check = """
        packages <- c('nflfastR', 'dplyr', 'jsonlite', 'openxlsx')
        installed <- sapply(packages, function(pkg) {
            if (require(pkg, character.only = TRUE, quietly = TRUE)) {
                version <- as.character(packageVersion(pkg))
                cat(sprintf('INSTALLED: %s %s\\n', pkg, version))
                TRUE
            } else {
                cat(sprintf('MISSING: %s\\n', pkg))
                FALSE
            }
        })
        """
        
        result = subprocess.run(['Rscript', '-e', r_check],
                              capture_output=True, text=True)
        print(result.stdout)
        
        if 'MISSING' in result.stdout:
            print("\n⚠️  Install missing R packages with:")
            print("   install.packages(c('nflfastR', 'dplyr', 'jsonlite', 'openxlsx'))")
            return False
        return True
        
    except FileNotFoundError:
        print("❌ R not installed or not in PATH")
        print("   Download from: https://cran.r-project.org/")
        return False
    except Exception as e:
        print(f"❌ Error checking R: {e}")
        return False

def check_directory_structure():
    """Check required directories exist"""
    print_header("Directory Structure")
    
    required_dirs = [
        'data',
        'models',
        'src',
        'data/backups'
    ]
    
    all_good = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"⚠️  {dir_path}/ (creating...)")
            path.mkdir(parents=True, exist_ok=True)
    
    return all_good

def check_required_files():
    """Check required source files"""
    print_header("Required Files")
    
    required_files = [
        'src/config.py',
        'src/data_aggregator.R',
        'src/feature_engineer.py',
        'src/model_trainer.py',
        'src/predictor.py',
        'src/input_calculator.py',
        'src/train_pipeline.py',
        'src/update_actuals.R',
        'predict_upcoming.py',
        'diagnostics.py',
        'smart_betting_advisor.py',
        'quick_actions.py',
        'auto_update_actuals.py',
        'dashboard.py'
    ]
    
    all_good = True
    for file_path in required_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} ({size:,} bytes)")
        else:
            print(f"❌ {file_path} MISSING")
            all_good = False
    
    return all_good

def check_model_files():
    """Check if model has been trained"""
    print_header("Model Files")
    
    model_files = [
        'models/qb_passing_yards_model.pkl',
        'models/qb_passing_yards_scaler.pkl',
        'models/qb_passing_yards_selector.pkl',
        'models/qb_passing_yards_features.pkl',
        'models/qb_passing_yards_mae.pkl'
    ]
    
    trained = True
    for file_path in model_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} ({size:,} bytes)")
        else:
            print(f"⚠️  {file_path} not found")
            trained = False
    
    if not trained:
        print("\n💡 Model not trained yet. Run:")
        print("   python -m src.train_pipeline")
    
    return trained

def check_data_files():
    """Check if data has been aggregated"""
    print_header("Data Files")
    
    data_files = [
        'data/passing_yards_player_logs.csv',
        'data/team_offense_logs.csv',
        'data/defense_logs.csv'
    ]
    
    all_good = True
    for file_path in data_files:
        if os.path.exists(file_path):
            df = __import__('pandas').read_csv(file_path)
            print(f"✅ {file_path} ({len(df):,} rows)")
        else:
            print(f"⚠️  {file_path} not found")
            all_good = False
    
    if not all_good:
        print("\n💡 Data not aggregated yet. Run:")
        print("   python -m src.train_pipeline")
    
    return all_good

def check_predictions_file():
    """Check predictions Excel file"""
    print_header("Predictions File")
    
    excel_file = 'data/passing-prop-predictions-2025.xlsx'
    if os.path.exists(excel_file):
        try:
            xl = __import__('pandas').ExcelFile(excel_file)
            weeks = [s for s in xl.sheet_names if s.startswith('Week')]
            print(f"✅ {excel_file}")
            print(f"   Weeks: {len(weeks)}")
            
            # Check each week
            for week in sorted(weeks):
                df = __import__('pandas').read_excel(excel_file, sheet_name=week)
                completed = df[df['Actual'].notna() & (df['Actual'] != '')]
                print(f"   {week}: {len(df)} predictions ({len(completed)} completed)")
            
            return True
        except Exception as e:
            print(f"⚠️  Error reading Excel file: {e}")
            return False
    else:
        print(f"ℹ️  {excel_file} not found (no predictions yet)")
        return True

def run_quick_test():
    """Run a quick functionality test"""
    print_header("Quick Functionality Test")
    
    try:
        # Test pandas
        import pandas as pd
        df = pd.DataFrame({'a': [1, 2, 3]})
        print("✅ Pandas DataFrame creation")
        
        # Test numpy
        import numpy as np
        arr = np.array([1, 2, 3])
        print("✅ NumPy array creation")
        
        # Test sklearn
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        print("✅ Scikit-learn import")
        
        # Test xgboost
        import xgboost as xgb
        print("✅ XGBoost import")
        
        # Test openpyxl
        import openpyxl
        print("✅ OpenPyXL import")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def generate_installation_guide():
    """Generate installation commands for missing dependencies"""
    print_header("Installation Guide")
    
    print("\n📦 If any Python packages are missing, install with:")
    print("   pip install pandas numpy scikit-learn xgboost joblib openpyxl")
    
    print("\n📦 If R packages are missing, run in R:")
    print("   install.packages(c('nflfastR', 'dplyr', 'jsonlite', 'openxlsx'))")
    
    print("\n🚀 To set up the model from scratch:")
    print("   1. python -m src.train_pipeline")
    print("   2. python predict_upcoming.py")
    
    print("\n📊 To analyze existing predictions:")
    print("   python diagnostics.py")
    
    print("\n🎯 For quick actions:")
    print("   python quick_actions.py")
    
    print("\n💰 For betting recommendations:")
    print("   python smart_betting_advisor.py")

def main():
    """Run complete validation"""
    print("\n" + "🔍 " + "="*58)
    print("  NFL PREDICTION SYSTEM - SETUP VALIDATION")
    print("="*60)
    
    results = {
        'Python Version': check_python_version(),
        'Python Packages': check_python_packages(),
        'R Installation': check_r_installation(),
        'Directory Structure': check_directory_structure(),
        'Required Files': check_required_files(),
        'Model Files': check_model_files(),
        'Data Files': check_data_files(),
        'Predictions File': check_predictions_file(),
        'Functionality Test': run_quick_test()
    }
    
    # Summary
    print_header("Validation Summary")
    
    passed = sum(results.values())
    total = len(results)
    
    for check, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {check}")
    
    print(f"\n{'='*60}")
    print(f"  {passed}/{total} checks passed")
    
    if passed == total:
        print("  🎉 System fully configured and ready!")
        print("\n  Next steps:")
        print("  1. python quick_actions.py  (convenience menu)")
        print("  2. python smart_betting_advisor.py  (get betting advice)")
    elif passed >= 7:
        print("  ⚠️  System mostly ready - minor issues detected")
        generate_installation_guide()
    else:
        print("  ❌ System needs configuration")
        generate_installation_guide()
    
    print('='*60)
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nValidation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)