# TODO

## Feature

### HA Config Sync Guardrails

- [ ] Add a pre-flight config-sync parity check by parsing `show high-availability state` (look for `Running Configuration: synchronized`) before disabling sync.

### HA Post-Upgrade Validation Parity

- [ ] Repeat HA1 health, antivirus parity, and config-sync status checks after upgrade/downgrade completion to match the pre-check coverage.

## Fix

## Rework

# DONE

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
