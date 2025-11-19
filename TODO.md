# TODO

## Feature

### HA1 Link Pre-Check

- [ ] Add a pre-check that validates HA1 status is `up` before any upgrade work begins.
- [ ] Abort with guidance if HA1 is down to avoid desynchronizing the peers.

## Fix

## Rework

# DONE

### Antivirus Parity After HA Upgrade

- [x] Investigate why antivirus definitions remain mismatched post-upgrade even though the playbook installs latest content (see `plans/feature_antivirus_parity_after_ha_upgrade_plan.md`).
- [x] Update the workflow to apply or verify antivirus updates so both peers report the same version.
