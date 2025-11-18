# TODO

## Feature

### Per-Hop HA Upgrade Parity

- [ ] Update HA upgrade orchestration so each version in `upgrade_path` is installed on the passive peer, fail over, then installed on the active peer before moving to the next version (see `plans/feature_per_hop_ha_upgrade_parity_plan.md`).
- [ ] Verify failover/restore sequencing stays consistent for every hop in the path.

### Passive-First Failure Catch-Up

- [ ] Track which `upgrade_path` entries finish successfully on the passive peer.
- [ ] Ensure the active peer only upgrades up to the last passive-successful version when a later passive hop fails.

### Failure - Revert

- [ ] when installing an OS version fails then the playbook must automatically revert to the last working version on both peers of HA

## Fix

## Rework

# DONE

### HA OS Upgrade

- [ ] Playbook for upgrading OS in HA pair palo altofirewalls

### Short-Circuit Fail

- [x] if an upgrade version provided in upgrade path is the same as or lower than the current installed version, the playbook must immediately stop and report about the same (see `plans/feature_short_circuit_fail_plan.md`)
