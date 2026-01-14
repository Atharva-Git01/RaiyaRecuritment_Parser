# scripts/set_version.py
import json
import sys
import os

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "system_config.json"))

def set_version(version):
    if not os.path.exists(CONFIG_PATH):
        print(f"Config not found at {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    
    data["active_prompt_version"] = version
    
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Active version set to: {version}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_version.py <version>")
    else:
        set_version(sys.argv[1])
