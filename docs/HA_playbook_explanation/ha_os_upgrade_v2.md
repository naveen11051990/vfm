# Line‑by‑Line Explanation of `ha_os_upgrade.yml`

This document walks through every line of `ha_os_upgrade.yml`, explaining what it does and how earlier variables are used later. Line numbers refer to `ha_os_upgrade.yml` as shown by `nl -ba`.

---

## Play Header and Variables (Lines 1–21)

- **Line 1** – YAML document start marker (`---`).
- **Line 2** – Names the play: “PAN‑OS HA Content and Software Upgrade with Config Backup”.
- **Line 3** – Targets the hosts group `PA-HA` by default (or whatever `hosts` is overridden to at runtime).
- **Line 4** – `connection: local` – Ansible runs modules from the controller/execution environment, not by SSHing into the firewalls.
- **Line 5** – `gather_facts: false` – Disables generic Ansible system fact gathering; we only use PAN‑OS‑specific facts later.
- **Line 7** – Starts the `vars` section (play‑level variables).
- **Lines 8–11** – Define `device`, a dictionary with `ip_address`, `username`, and `password`. These are expected to be set in inventory or extra vars and are reused in many PAN‑OS module calls.
- **Lines 13–14** – Define backup location:
  - `backup_directory` uses environment variable `PANOS_BACKUP_DIR` if set, otherwise `/runner/backups`.
  - `backup_filename` combines this directory with the current host’s name (via `inventory_hostname`), e.g., `backups/121UPGRADE-running-config.xml`. This is used later in the backup task.
- **Lines 16–17** – Declare two control flags, `reboot_between_steps` and `quiet_polling`. These are informational and align with how `tasks/upgrade_step_v2.yml` behaves.
- **Lines 19–20** – Specify that this play uses the `paloaltonetworks.panos` collection, which provides all PAN‑OS‑specific modules used below.

---

## Validation and HA Discovery (Lines 22–113)

- **Line 22** – Begins the `tasks` section.

### Validate Upgrade Path (Lines 23–29)

- **Lines 23–28** – `Validate upgrade_path is provided`:
  - Uses `ansible.builtin.assert` to ensure:
    - `upgrade_path` is defined.
    - `upgrade_path` has at least one entry.
  - The `fail_msg` tells the operator how to pass `upgrade_path` (e.g., `-e upgrade_path='["11.0.4-h2","11.0.4-h5"]'`).
- **Line 29** – `run_once: true` ensures this assertion is evaluated only once (not per host) since it’s global input.

### Collect HA/System Facts (Lines 31–41)

- **Lines 31–35** – `Gather HA and system facts`:
  - Calls `panos_facts` with `gather_subset: ["system", "ha"]` using the `device` credentials defined at lines 8–11.
  - Stores the result in `ha_facts`, which includes hostname, serial, HA enabled flag, HA mode, role, and group ID.
- **Lines 37–41** – `Gather full HA configuration (running config)`:
  - Calls `panos_facts` again, this time with `gather_subset: ["config"]`.
  - Stores the XML representation of the running configuration in `ha_cfg.ansible_facts.ansible_net_config`.

### Snapshot Per‑Device HA State (Lines 43–52)

- **Lines 43–52** – `Record HA snapshot for {{ inventory_hostname }}`:
  - Builds a `ha_runtime` fact per host from `ha_facts` (line 35):
    - `inventory_hostname`, `hostname`, `serial`.
    - `ha_enabled` – boolean “is HA on?”.
    - `ha_mode` – e.g. `active-passive`.
    - `ha_initial_role` – `active` or `passive` at the start of the run.
    - `ha_group_id` – numeric HA group ID.
  - This snapshot is reused later in the topology view and role‑flag steps.

### Discover HA1 Interface and Peer IP (Lines 54–75)

- **Lines 54–75** – `Discover HA interface wiring from running config`:
  - Uses `ansible.builtin.set_fact` to parse `ha_cfg.ansible_facts.ansible_net_config` (line 41) with regex:
    - `ha1_ip_address` (lines 56–60): looks for `<ha1><ip-address>…</ip-address>` under `<interface>`.
    - `ha1_netmask` (lines 61–65): looks for `<ha1><netmask>…</netmask>`.
    - `ha1_port` (lines 66–70): looks for `<ha1><port>…</port>` – e.g., `ethernet1/3`.
    - `ha_peer_ip` (lines 71–75): looks for `<high-availability><group><peer-ip>…</peer-ip>`.
  - Each regex call returns a list of matches; `| default([]) | first | default('')` reduces this to a single string or empty string if not found.

### Validate HA Wiring Discovery (Lines 77–86)

- **Lines 77–86** – `Validate discovered HA wiring`:
  - Asserts that `ha1_ip_address`, `ha1_netmask`, `ha1_port`, and `ha_peer_ip` all have non‑zero length.
  - If any are empty, the play fails with a clear message rather than proceeding with incomplete HA knowledge.

### Build HA Topology View (Lines 88–108)

- **Lines 88–94** – `Consolidate HA topology view`:
  - `run_once: true`, delegated to `localhost`, meaning this block runs only on the controller.
  - Sets `ha_view` to a list of all hosts’ `ha_runtime` facts (from lines 43–52), using `ansible_play_hosts_all` and `hostvars`.
- **Lines 95–103** – `Validate HA pair is active/passive and healthy`:
  - Asserts:
    - There are exactly two devices (`ha_view | length == 2`).
    - Both have HA enabled.
    - Both report the same HA mode, and that mode is `active-passive`.
    - Exactly one host shows `ha_initial_role == 'active'`.
    - Exactly one host shows `ha_initial_role == 'passive'`.
  - Fails with a helpful message if the pair is not a clean active/passive pair.
- **Lines 104–108** – `Persist HA role ownership`:
  - Sets:
    - `ha_topology` to `ha_view` (for potential future use).
    - `ha_active_host` to the `inventory_hostname` whose initial role is `active`.
    - `ha_passive_host` to the `inventory_hostname` whose initial role is `passive`.
  - These hostnames are used later in the controller‑driven block (lines 221–316) to decide which node to upgrade first and which to suspend.

### Mark Initial Role Flags (Lines 110–113)

- **Lines 110–113** – `Mark initial HA role flags`:
  - On each device (not run_once), sets:
    - `is_initial_active` to true if this host’s `ha_runtime.ha_initial_role` is `active`.
    - `is_initial_passive` to true if it is `passive`.
  - These flags are used at the end (lines 400–418) to gate the “wait for original active/passive role” checks.

---

## Content Update and Backup (Per Device, Lines 115–193)

### Pre‑Content Health Check (Lines 115–121)

- **Lines 115–121** – `Ensure device is ready before content upgrade`:
  - Calls `panos_check` with `provider: "{{ device }}"` to verify each firewall reports “Device is ready”.
  - Retries up to 10 times with a delay between attempts.
  - Prevents content operations from running while the firewall is already in a busy or error state.

### Refresh and Install Latest Content (Lines 123–177)

- **Lines 123–127** – `Refresh content update index`:
  - Calls `panos_op` with `cmd: "request content upgrade check"` to have the firewall check for new content packages.
- **Lines 128–132** – `Download latest content update`:
  - Calls `panos_op` with `cmd: "request content upgrade download latest"`.
  - Registers the output as `content_download`, which contains XML including a `<job>` ID for the download.
- **Lines 134–136** – `Extract job ID for content download`:
  - Sets `content_download_jobid` by regex‑searching `content_download.stdout_xml` for `<job>…</job>` and extracting the numeric job ID string.
- **Lines 138–149** – `Wait for content download job to complete`:
  - Uses `panos_op` to query job status with `<show><jobs><id>…</id></jobs></show>`.
  - Loops until the job’s status is `FIN` (finished).
  - Fails early if the XML shows a `<result>FAIL</result>`.
  - Executes only when a non‑empty job ID was found.
- **Lines 151–155** – `Install latest content update`:
  - Calls `panos_op` with `cmd: "request content upgrade install version latest"` to start installing the downloaded content package.
  - Registers output as `content_install` for job ID extraction.
- **Lines 157–159** – `Extract job ID for content install`:
  - Similar to the download step, extracts `content_install_jobid` from `content_install.stdout_xml`.
- **Lines 161–177** – `Wait for content install job to complete`:
  - Queries the job status repeatedly using `panos_op`.
  - Loops until status is either `FIN` or `FAIL`.
  - Treats combinations of `FIN` + `FAIL` result or any `FAIL` status as an error.
  - Only runs when there is a non‑empty job ID.

### Post‑Content Health Check (Lines 179–186)

- **Lines 179–186** – `Wait for device readiness after content install`:
  - Again uses `panos_check` to ensure each firewall returns to a “Device is ready” state after content installation.
  - Retries for up to 60 attempts, with a 15‑second delay between attempts.

### Configuration Backup (Lines 188–193)

- **Lines 188–193** – `Backup running configuration`:
  - Calls `panos_export` with:
    - `category: configuration`.
    - `filename: "{{ backup_filename }}"` (defined at line 14).
    - `create_directory: true` to ensure the backup directory exists.
  - Saves a full configuration backup for each firewall to the controller, providing a rollback point.

---

## Disable HA Config Sync (Per Device, Lines 195–219)

### Turn Off Config Sync (Lines 195–200)

- **Lines 195–200** – `Disable config sync`:
  - Uses `panos_type_cmd` to run a low‑level `set` command:
    - `xpath` points to the HA configuration‑sync flag:  
      `/config/devices/entry[@name='localhost.localdomain']/deviceconfig/high-availability/group/configuration-synchronization`
    - `element: "<enabled>no</enabled>"` sets this flag to `no` (disabled).
  - This prevents automatic configuration synchronization between the two peers during the upgrade.

### Commit the Change (Lines 202–205)

- **Lines 202–205** – `Commit HA change (config sync disabled)`:
  - Calls `panos_commit_firewall` for each device to commit the configuration change made in lines 195–200.
  - The description (“Disable HA config sync before OS upgrade”) makes the purpose of this commit visible in the device’s commit history.

### Re‑Read HA State and Validate (Lines 207–219)

- **Lines 207–211** – `Re-collect HA facts after disabling config sync`:
  - Re‑runs `panos_facts` with `gather_subset: ["ha"]` and stores results in `ha_post_disable`.
  - The intention is to verify that only config sync behavior changed, not HA mode or roles.
- **Lines 213–219** – `Verify HA state after disabling config sync`:
  - Asserts that:
    - HA is still enabled (`ansible_net_ha_enabled` is true).
    - HA mode is still `active-passive`.
    - The local role is still either `active` or `passive`.
  - If any of these checks fail, the play stops with a clear message, indicating something unexpected happened to HA state.

---

## Passive‑First Upgrade Orchestration (Controller, Lines 221–316)

### Start the Controller‑Driven Block (Lines 221–226)

- **Lines 221–226** – `Orchestrate passive-first upgrade sequence (controller-driven)`:
  - `run_once: true` means this orchestration logic runs only once on the controller.
  - Defines:
    - `passive_host` as `ha_passive_host` from line 108 (the initial passive peer).
    - `active_host` as `ha_active_host` from line 107 (the initial active peer).
  - These variables determine which device is upgraded first and which is suspended.

### Ensure No Commit on Passive (Lines 227–238)

- **Lines 227–238** – `Wait for any running commit to finish on passive`:
  - Uses `panos_op` on the passive host’s credentials to run `show jobs all`.
  - Loops until the job output does **not** contain any commit job with status `PEND`, `ACT`, `RUN`, or `ACTIVE`.
  - Ensures the passive firewall is idle (no commit in progress) before starting its software upgrade.

### Upgrade Passive Firewall (Lines 240–250)

- **Lines 240–250** – `Upgrade passive firewall first`:
  - Includes the task file `tasks/upgrade_step_v2.yml` once for each entry in `upgrade_path` (step 6).
  - For each `item` (version string), sets:
    - `version_item: "{{ item }}"`, passed into `upgrade_step_v2.yml` to tell it which PAN‑OS version to target.
    - A `device` provider with the passive host’s `ip_address`, `username`, `password` (from inventory and `hostvars`).
  - `upgrade_step_v2.yml` performs the download, install, reboot, and verification sequence for each version, ensuring the passive firewall reaches the final target version.

### Suspend Original Active and Fail Over (Lines 252–283)

- **Lines 252–258** – `Suspend original active to trigger failover`:
  - Uses `panos_op` on `active_host` to run `request high-availability state suspend`.
  - This transitions the original active firewall into a suspended state so that the upgraded passive can take over as active.
- **Lines 260–273** – `Check HA role on upgraded passive` (nested block):
  - Calls `panos_facts` on the upgraded passive firewall to poll its HA status.
  - Retries until `ansible_net_ha_localstate` equals `active`.
  - Confirms the upgraded node has actually taken over the active role.
- **Lines 274–283** – `Wait for upgraded passive (now active) readiness`:
  - Calls `panos_check` on the same device.
  - Loops until `Device is ready`, confirming the new active is healthy before proceeding.

### Ensure No Commit on Original Active (Lines 285–296)

- **Lines 285–296** – `Wait for any running commit to finish on original active`:
  - Similar to lines 227–238, but now executed against the original active firewall.
  - Waits until there are no active or pending commit jobs before upgrading the original active.

### Upgrade Original Active (Lines 298–308)

- **Lines 298–308** – `Upgrade originally active firewall`:
  - Again includes `tasks/upgrade_step_v2.yml` once per entry in `upgrade_path`.
  - This time `device` is set to point at `active_host`’s IP, username, and password.
  - Performs the same download/install/reboot/check/assert sequence as for the passive, bringing the original active up to the target version while it is not carrying production traffic.

### Return Suspended Firewall to Functional State (Lines 310–316)

- **Lines 310–316** – `Return suspended firewall to functional state`:
  - Uses `panos_op` on `active_host` to run `request high-availability state functional`.
  - Brings the original active firewall back into normal HA participation (active or passive, depending on HA election/preemption behavior at this stage).

---

## Re‑Enable Config Sync and Failback Logic (Lines 318–399)

### Re‑Enable Config Sync (Lines 318–323)

- **Lines 318–323** – `Re-enable config sync`:
  - Uses `panos_type_cmd` with:
    - The same HA xpath used in the disable step (lines 195–200).
    - `element: "<enabled>yes</enabled>"` to turn configuration synchronization back on.
  - This re‑activates HA config sync but does not yet commit it.

### Commit Config Sync Re‑Enable (Lines 325–328)

- **Lines 325–328** – `Commit HA change (config sync enabled)`:
  - Calls `panos_commit_firewall` for each device.
  - Makes the “config sync enabled” setting effective on both peers.

### Sync Running Config from Original Active (Lines 330–334)

- **Lines 330–334** – `Force running-config sync from initial active back to peer`:
  - Uses `panos_op` with `cmd: "request high-availability sync-to-remote running-config"`.
  - The `when` clause ensures this runs only on the host whose `inventory_hostname` equals `ha_active_host` (original active, determined at line 107).
  - Ensures the peer’s running configuration is explicitly synced from the original active after the upgrades.

### New Failback Block to Restore Original Active (Lines 336–399)

- **Lines 336–399** – `Ensure original active regains active role if needed`:
  - `run_once: true`, executed on the controller.
  - Sets:
    - `original_active` to `ha_active_host` (initial active from line 107).
    - `original_passive` to `ha_passive_host` (initial passive from line 108).
  - **Lines 348–350** – `Check current HA roles after upgrades`:
    - Runs `panos_facts` (HA subset) via a loop across `[original_active, original_passive]`.
    - Registers the result as `final_ha_view`, which includes each device’s current role.
  - **Lines 352–358** – `Derive current active host after upgrades`:
    - Builds `current_active_host` by selecting which loop item in `final_ha_view.results` has `ansible_net_ha_localstate == 'active'`.
    - This tells us who is active right now.
  - **Lines 360–370** – `Suspend current active to fail back to original active`:
    - If `current_active_host` is defined and **not** equal to `original_active`, then:
      - Uses `panos_op` on `current_active_host` to run `request high-availability state suspend`.
    - This forces a failback: the currently active node gives up the active role so the original active can reclaim it.
  - **Lines 372–386** – `Wait for original active to become active again after failback`:
    - If a different node was suspended (same conditions as above), the play:
      - Polls `panos_facts` (HA subset) on `original_active` until its role becomes `active`.
  - **Lines 388–398** – `Return suspended firewall to functional state after failback`:
    - Under the same conditions, uses `panos_op` on `current_active_host` to run `request high-availability state functional`.
    - This brings the temporarily suspended peer back into the cluster as the passive device.
  - This entire block ensures that, regardless of HA election/preemption behavior during upgrades, the HA pair ends with the original active firewall back in the active role and the original passive as passive.

---

## Final HA Role Checks and Summary (Lines 400–425)

### Wait for Original Roles (Lines 400–418)

- **Lines 400–407** – `Wait for original active role to return`:
  - Uses `panos_facts` (HA subset) per device to check `ansible_net_ha_localstate`.
  - The `when: is_initial_active` condition (set at lines 110–113) ensures this runs only on the host that started as active.
  - Loops until that host’s role is `active` again.
- **Lines 410–418** – `Wait for original passive role to return`:
  - Similar pattern, but runs only on hosts where `is_initial_passive` is true.
  - Loops until that host’s role is `passive` again.
  - Together, these confirm that the cluster has fully returned to its original role assignment.

### Final Debug Summary (Lines 420–425)

- **Lines 420–425** – `Report HA upgrade result`:
  - `run_once: true` – executes only once on the controller.
  - Prints a multi‑line message stating:
    - The original active host (`ha_active_host` from line 107) is active again.
    - The original passive host (`ha_passive_host` from line 108) is passive again.
    - The path of the backups directory (`backup_directory` from line 13) where running configs were saved.
  - This provides a concise executive‑level summary that the upgrade completed, HA is healthy, roles are correct, and backups are available.

---

In summary, every line in `ha_os_upgrade.yml` contributes to a careful, staged HA upgrade flow:
- Lines 1–21 define scope and global variables.
- Lines 22–113 validate inputs and map out the HA pair.
- Lines 115–193 update content and secure configuration backups.
- Lines 195–219 temporarily disable HA config sync and verify HA remains healthy.
- Lines 221–316 orchestrate a passive‑first, controller‑driven upgrade and failover.
- Lines 318–399 restore config sync and actively fail back to the original active.
- Lines 400–425 double‑check HA roles and report final status.

