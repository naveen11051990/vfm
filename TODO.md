# TODO

## Feature

### HA Backups Offload to TFTP

- [ ] Capture the PAN-OS CLI requirements for exporting configuration and tech-support bundles to TFTP and mirror the successful Cisco flow (see `plans/feature_ha_tftp_backup_plan.md`).
- [ ] Extend `ha_os_upgrade.yml` so every config backup and tech-support bundle is optionally copied to the configured TFTP target with clear failure handling.
- [ ] Document the new TFTP variables/assumptions and add validation or dry-run coverage before rollout.

### HA Downgrade TFTP Offload

- [ ] Re-introduce optional TFTP offload for config backups and tech-support bundles in `ha_os_downgrade.yml`, aligned with the upgrade playbook behavior.
- [ ] Add variables/validation for TFTP targets and failure handling in downgrade flow.
- [ ] Document usage and differences from upgrade offload (if any).

## Fix

## Rework

### HA OS Upgrade Module Cleanup

- [ ] Draft implementation plan (see `plans/rework_ha_os_upgrade_module_cleanup_plan.md`).
- [ ] Replace content and antivirus handling with official modules (no regex/job-id parsing).
- [ ] Toggle HA config sync and pre/post commit waits using official modules, minimizing XML/regex parsing.

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

### HA Post-Upgrade Validation Parity

- [x] Re-run HA1 control/active-passive assertions after upgrades and failback.
- [x] Re-validate HA wiring (HA1 IP/netmask/port/peer) matches pre-upgrade discovery.
- [x] Re-run HA readiness/config-sync health after re-enabling sync and sync-to-remote.
- [x] Re-check antivirus/content version parity post-upgrade.
- [x] Add consolidated post-check debug/summary output.

### Antivirus Parity After HA Upgrade

- [x] Investigate why antivirus definitions remain mismatched post-upgrade even though the playbook installs latest content (see `plans/feature_antivirus_parity_after_ha_upgrade_plan.md`).
- [x] Update the workflow to apply or verify antivirus updates so both peers report the same version.

### Sample Failing Training Playbooks

- [x] Add maintenance window guard playbook that fails outside approved hours (`Daniel/maintenance_window_patch_fail.yml`).
- [x] Add deployment blocker for excessive database replication lag (`Daniel/db_replication_lag_abort.yml`).
- [x] Add S3 backup prerequisite checker that fails when credentials are missing (`Daniel/s3_backup_prereq_fail.yml`).
