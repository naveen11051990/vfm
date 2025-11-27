# TODO

## Feature

### HA Post-Upgrade Validation Parity

- [ ] Repeat HA1 health, antivirus parity, and config-sync status checks after upgrade/downgrade completion to match the pre-check coverage.

### HA Backups Offload to TFTP

- [ ] Capture the PAN-OS CLI requirements for exporting configuration and tech-support bundles to TFTP and mirror the successful Cisco flow (see `plans/feature_ha_tftp_backup_plan.md`).
- [ ] Extend `ha_os_upgrade.yml` so every config backup and tech-support bundle is optionally copied to the configured TFTP target with clear failure handling.
- [ ] Document the new TFTP variables/assumptions and add validation or dry-run coverage before rollout.

## Fix

## Rework

# DONE

### HA Config Sync Guardrails

- [x] Add a pre-flight config-sync parity check by parsing `show high-availability state` (look for `Running Configuration: synchronized`) before disabling sync. (see `plans/feature_ha_config_sync_validation_plan.md`)

### HA Tech-Support Capture Automation

- [x] Capture tech-support bundle from each HA peer before upgrades using `panos_export` (see `plans/feature_ha_tech_support_capture_plan.md`)

### HA OS Upgrade Hardening

- [x] Add HA1 link pre-check step to `ha_os_upgrade.yml` before starting upgrades (see `plans/feature_ha_os_upgrade_hardening_plan.md`)
- [x] Capture tech-support bundle from each firewall ahead of the upgrade and store with existing backups (see `plans/feature_ha_os_upgrade_hardening_plan.md`)

### HA OS Downgrade Playbook

- [x] Design downgrade workflow for HA pair (see `plans/feature_ha_os_downgrade_plan.md`)
- [x] Implement `ha_os_downgrade.yml` playbook aligned with Palo Alto and Ansible docs
- [x] Test downgrade procedure in a lab HA environment

### Antivirus Parity After HA Upgrade

- [x] Investigate why antivirus definitions remain mismatched post-upgrade even though the playbook installs latest content (see `plans/feature_antivirus_parity_after_ha_upgrade_plan.md`).
- [x] Update the workflow to apply or verify antivirus updates so both peers report the same version.

### Sample Failing Training Playbooks

- [x] Add maintenance window guard playbook that fails outside approved hours (`Daniel/maintenance_window_patch_fail.yml`).
- [x] Add deployment blocker for excessive database replication lag (`Daniel/db_replication_lag_abort.yml`).
- [x] Add S3 backup prerequisite checker that fails when credentials are missing (`Daniel/s3_backup_prereq_fail.yml`).
