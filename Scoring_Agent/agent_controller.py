    def _do_verify_output(self):
        logger.info("Verifying output...")
        
        if not self.authority.authorize_score(self.memory.result):
            self.memory.error = "Authority rejected the AI score (Malformed or out of bounds)."
            self.transition_to(AgentState.FAILED)
            return
        
        self.transition_to(AgentState.RAG_VALIDATION)

    def _do_rag_validation(self):
        logger.info("Running RAG Validation Layer...")
        
        import subprocess
        import json
        import os
        
        # Save AI score to RAG inputs
        rag_inputs_dir = os.path.join(os.path.dirname(__file__), '..', 'RAG_Validation_layer', 'data', 'inputs')
        os.makedirs(rag_inputs_dir, exist_ok=True)
        
        ai_score_file = os.path.join(rag_inputs_dir, 'score_my_resume.json')
        with open(ai_score_file, 'w') as f:
            json.dump({
                'inputs': {
                    'resume': self.memory.resume_data,
                    'jd': self.memory.jd_data
                },
                'result': self.memory.result
            }, f, indent=2)
        
        # Save JD
        jd_file = os.path.join(rag_inputs_dir, 'job_description.json')
        with open(jd_file, 'w') as f:
            json.dump(self.memory.jd_data, f, indent=2)
        
        # Run RAG pipeline
        rag_dir = os.path.join(os.path.dirname(__file__), '..', 'RAG_Validation_layer')
        try:
            result = subprocess.run(['python', 'main.py'], cwd=rag_dir, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                self.memory.error = f"RAG Validation failed: {result.stderr}"
                self.transition_to(AgentState.FAILED)
                return
        except subprocess.TimeoutExpired:
            self.memory.error = "RAG Validation timed out."
            self.transition_to(AgentState.FAILED)
            return
        
        # Load final validation report
        output_dir = os.path.join(rag_dir, 'data', 'outputs')
        final_report_file = os.path.join(output_dir, 'final_validation_report.json')
        if os.path.exists(final_report_file):
            with open(final_report_file, 'r') as f:
                validation_report = json.load(f)
            self.memory.result['validation_report'] = validation_report
        else:
            logger.warning("Final validation report not found.")
        
        self.transition_to(AgentState.COMPLETED)