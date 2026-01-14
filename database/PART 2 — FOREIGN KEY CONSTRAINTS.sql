-- SERVICES & PRICING FKs
ALTER TABLE tenant_services
  ADD CONSTRAINT fk_ts_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_ts_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE service_entitlements
  ADD CONSTRAINT fk_se_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_se_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE rate_plans
  ADD CONSTRAINT fk_rp_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE tenant_rate_overrides
  ADD CONSTRAINT fk_tro_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_tro_rateplan FOREIGN KEY (rate_plan_id) REFERENCES rate_plans(rate_plan_id);

ALTER TABLE business_unit_rates
  ADD CONSTRAINT fk_bur_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id),
  ADD CONSTRAINT fk_bur_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE rate_cards
  ADD CONSTRAINT fk_rc_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_rc_service FOREIGN KEY (service_id) REFERENCES services(service_id);

ALTER TABLE service_cost_summary
  ADD CONSTRAINT fk_scs_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);


-- BUSINESS UNITS & RESOURCES FKs
ALTER TABLE business_units
  ADD CONSTRAINT fk_bu_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE departments
  ADD CONSTRAINT fk_dept_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id);

ALTER TABLE projects
  ADD CONSTRAINT fk_proj_dept FOREIGN KEY (dept_id) REFERENCES departments(dept_id);

ALTER TABLE bu_users
  ADD CONSTRAINT fk_buusers_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id),
  ADD CONSTRAINT fk_buusers_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE job_descriptions
  ADD CONSTRAINT fk_jd_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id);

ALTER TABLE batches
  ADD CONSTRAINT fk_batches_bu FOREIGN KEY (bu_id) REFERENCES business_units(bu_id),
  ADD CONSTRAINT fk_batches_uploader FOREIGN KEY (uploader_user_id) REFERENCES global_users(user_id);

ALTER TABLE jobs
  ADD CONSTRAINT fk_jobs_batch FOREIGN KEY (batch_id) REFERENCES batches(batch_id),
  ADD CONSTRAINT fk_jobs_jd FOREIGN KEY (jd_id) REFERENCES job_descriptions(jd_id),
  ADD CONSTRAINT fk_jobs_requester FOREIGN KEY (requester_user_id) REFERENCES global_users(user_id);

ALTER TABLE resume_results
  ADD CONSTRAINT fk_rr_job FOREIGN KEY (job_id) REFERENCES jobs(job_id);


-- BILLING & SUBSCRIPTIONS FKs
ALTER TABLE subscriptions
  ADD CONSTRAINT fk_sub_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_sub_plan FOREIGN KEY (plan_id) REFERENCES plan_catalog(plan_id);

ALTER TABLE credits
  ADD CONSTRAINT fk_credits_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE credit_ledger_entries
  ADD CONSTRAINT fk_ledger_credit FOREIGN KEY (credit_id) REFERENCES credits(credit_id);

ALTER TABLE transactions
  ADD CONSTRAINT fk_txn_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE invoices
  ADD CONSTRAINT fk_inv_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE invoice_line_items
  ADD CONSTRAINT fk_line_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id);

ALTER TABLE billing_events
  ADD CONSTRAINT fk_be_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE usage_metering
  ADD CONSTRAINT fk_usage_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_usage_service FOREIGN KEY (service_id) REFERENCES services(service_id);
