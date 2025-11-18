# TODO

## Feature

### Short-Circuit Fail

- [ ] if an upgrade version provided in upgrade path is the same as or lower than the current installed version, the playbook must immediately stop and report about the same (see `plans/feature_short_circuit_fail_plan.md`)

### Failure - Revert

- [ ] when installing an OS version fails then the playbook must automatically revert to the last working version on both peers of HA

## Fix

## Rework

# DONE

### HA OS Upgrade

- [ ] Playbook for upgrading OS in HA pair palo altofirewalls
