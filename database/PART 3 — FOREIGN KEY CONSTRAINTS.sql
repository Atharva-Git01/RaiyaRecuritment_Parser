-- JOB SYSTEM FKs
ALTER TABLE job_dispatch
  ADD CONSTRAINT fk_jd_job FOREIGN KEY (job_id) REFERENCES job_queue(queue_id),
  ADD CONSTRAINT fk_jd_worker FOREIGN KEY (worker_id) REFERENCES worker_pools(worker_id);

ALTER TABLE dead_letter_queue
  ADD CONSTRAINT fk_dlq_job FOREIGN KEY (job_id) REFERENCES job_queue(queue_id);

ALTER TABLE job_metrics
  ADD CONSTRAINT fk_jm_job FOREIGN KEY (job_id) REFERENCES job_queue(queue_id);


-- EVENT SYSTEM FKs
ALTER TABLE tenant_webhooks
  ADD CONSTRAINT fk_tw_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE notifications
  ADD CONSTRAINT fk_notif_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);


-- SEARCH INDEXING FKs
ALTER TABLE search_sync_jobs
  ADD CONSTRAINT fk_ssj_idx FOREIGN KEY (index_id) REFERENCES search_index_metadata(index_id);


-- STORAGE METADATA FKs
ALTER TABLE object_storage_metadata
  ADD CONSTRAINT fk_osm_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE presigned_urls
  ADD CONSTRAINT fk_pu_file FOREIGN KEY (file_id) REFERENCES object_storage_metadata(file_id);

ALTER TABLE virus_scan_results
  ADD CONSTRAINT fk_vsr_file FOREIGN KEY (file_id) REFERENCES object_storage_metadata(file_id);


-- STORAGE LIFECYCLE
ALTER TABLE storage_lifecycle_policies
  ADD CONSTRAINT fk_slp_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);


-- API GATEWAY FKs
ALTER TABLE api_keys
  ADD CONSTRAINT fk_apikeys_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE rate_limits
  ADD CONSTRAINT fk_rl_apikey FOREIGN KEY (api_key_id) REFERENCES api_keys(api_key_id);

ALTER TABLE request_logs
  ADD CONSTRAINT fk_rl_log_apikey FOREIGN KEY (api_key_id) REFERENCES api_keys(api_key_id);

ALTER TABLE abuse_detection_logs
  ADD CONSTRAINT fk_adl_apikey FOREIGN KEY (api_key_id) REFERENCES api_keys(api_key_id);


-- OBSERVABILITY FKs
ALTER TABLE metrics
  ADD CONSTRAINT fk_metrics_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE structured_logs
  ADD CONSTRAINT fk_logs_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE incident_alerts
  ADD CONSTRAINT fk_incident_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);


-- BACKUP LAYER FKs
ALTER TABLE backup_policies
  ADD CONSTRAINT fk_bp_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE database_backups
  ADD CONSTRAINT fk_db_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE object_storage_backups
  ADD CONSTRAINT fk_osb_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE tenant_snapshots
  ADD CONSTRAINT fk_tsnap_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE bu_snapshots
  ADD CONSTRAINT fk_busnap_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id);

ALTER TABLE restore_requests
  ADD CONSTRAINT fk_rr_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE disaster_recovery_metadata
  ADD CONSTRAINT fk_drm_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);
