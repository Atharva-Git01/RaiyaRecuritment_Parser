import os
import shutil
from pathlib import Path

def migrate_data():
    root = Path.cwd()
    data_dir = root / "data"
    inputs_dir = data_dir / "inputs"
    outputs_dir = data_dir / "outputs"
    historical_dir = data_dir / "historical"

    # Create directories
    for d in [inputs_dir, outputs_dir, historical_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Migrate uploads -> inputs
    uploads_dir = root / "uploads"
    if uploads_dir.exists():
        print(f"Migrating {uploads_dir}...")
        # Check for JD files in uploads
        for f in uploads_dir.glob("*.json"):
            print(f"  Moving {f.name} to inputs/")
            shutil.copy2(f, inputs_dir / f.name)
        
        # Check for AI scorer files
        ai_scorer_dir = uploads_dir / "ai_scorer"
        if ai_scorer_dir.exists():
            for f in ai_scorer_dir.glob("*.json"):
                print(f"  Moving AI score {f.name} to inputs/")
                shutil.copy2(f, inputs_dir / f.name)

    # 2. Migrate storage -> outputs / historical
    storage_dir = root / "storage"
    if storage_dir.exists():
        print(f"Migrating {storage_dir}...")
        # Main storage files
        for f in storage_dir.glob("*.json"):
            print(f"  Moving {f.name} to outputs/")
            shutil.copy2(f, outputs_dir / f.name)
        
        # Historical evidences
        hist_ev_dir = storage_dir / "Historical_Evidences"
        if hist_ev_dir.exists():
            for f in hist_ev_dir.glob("*.json"):
                print(f"  Moving historical evidence {f.name} to historical/")
                shutil.copy2(f, historical_dir / f.name)
        
        # Rule based evidence
        rule_ev_dir = storage_dir / "rule_based_evidence"
        if rule_ev_dir.exists():
            for f in rule_ev_dir.glob("*.json"):
                print(f"  Moving rule based evidence {f.name} to outputs/")
                shutil.copy2(f, outputs_dir / f.name)

    print("Migration complete (copied). Original files still exist for safety.")

if __name__ == "__main__":
    migrate_data()
