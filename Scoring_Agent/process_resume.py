import sys
import os
import json
import logging
import time
import datetime

# Ensure path to app modules (current dir is root of 'phi 4 testing')
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agent_controller import AgentController, AgentState
from app.runtime_paths import get_results_dir, resolve_jd_path, resolve_resume_path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ResumeProcessor")

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    logger.info(f"Result saved to: {path}")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    resume_path = resolve_resume_path("test_parsed_resume_6.json")
    jd_path = resolve_jd_path("job_description.json")
    results_dir = get_results_dir()
    
    # Validation
    if not os.path.exists(resume_path):
        logger.error(f"Resume file not found: {resume_path}")
        return
    if not os.path.exists(jd_path):
        logger.error(f"JD file not found: {jd_path}")
        return
        
    # Output Filename (Timestamped)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"scoring_result_{timestamp}.json"
    output_path = os.path.join(results_dir, output_filename)

    try:
        logger.info("Loading inputs...")
        resume_data = load_json(resume_path)
        
        # Normailize / Alias Support
        if "name" not in resume_data and "candidate_name" in resume_data:
            resume_data["name"] = resume_data["candidate_name"]

        jd_data = load_json(jd_path)
        
        logger.info("Initializing Agent...")
        agent = AgentController(resume_data, jd_data)
        
        logger.info("Running Agent Pipeline...")
        start_time = time.time()
        result = agent.run()
        end_time = time.time()
        
        logger.info(f"Pipeline completed in {end_time - start_time:.2f}s")
        logger.info(f"Final State: {agent.state.value}")
        
        # Save full memory dump (audit trail + result)
        logger.info("Saving results...")
        save_json(agent.memory.to_dict(), output_path)
        
        if agent.state == AgentState.COMPLETED:
            print(f"\nSUCCESS: Processing complete. Score: {result.get('result', {}).get('final_score')}")
        else:
            print(f"\nFAILURE: Processing failed. Error: {agent.error}")
            
        print(f"Full report saved to: {output_path}")

    except Exception as e:
        logger.exception(f"Fatal error during execution: {e}")

if __name__ == "__main__":
    main()
