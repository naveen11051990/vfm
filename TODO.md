# TODO

## Feature

### HA OS Downgrade Playbook

- [ ] Design downgrade workflow for HA pair (see `plans/feature_ha_os_downgrade_plan.md`)
- [ ] Implement `ha_os_downgrade.yml` playbook aligned with Palo Alto and Ansible docs
- [ ] Test downgrade procedure in a lab HA environment

## Fix

## Rework

# DONE

### Antivirus Parity After HA Upgrade

- [x] Investigate why antivirus definitions remain mismatched post-upgrade even though the playbook installs latest content (see `plans/feature_antivirus_parity_after_ha_upgrade_plan.md`).
- [x] Update the workflow to apply or verify antivirus updates so both peers report the same version.
