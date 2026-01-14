-- ===========================
-- FOREIGN KEY CONSTRAINTS
-- ===========================

ALTER TABLE user_tenants
  ADD CONSTRAINT fk_ut_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
  ADD CONSTRAINT fk_ut_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE auth_providers
  ADD CONSTRAINT fk_ap_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE sessions
  ADD CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE mfa_settings
  ADD CONSTRAINT fk_mfa_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE password_history
  ADD CONSTRAINT fk_ph_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE custom_roles
  ADD CONSTRAINT fk_cr_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE policy_rules
  ADD CONSTRAINT fk_pr_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);

ALTER TABLE effective_permissions
  ADD CONSTRAINT fk_ep_user FOREIGN KEY (user_id) REFERENCES global_users(user_id);

ALTER TABLE tenant_onboarding_jobs
  ADD CONSTRAINT fk_toj_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id);
