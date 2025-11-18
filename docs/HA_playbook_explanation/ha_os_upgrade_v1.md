# HA PAN‑OS Upgrade Playbook – Executive Explanation

This document explains, in plain language, what `ha_os_upgrade.yml` does, why each step exists, and how earlier variables are reused later in the flow.

The goal of the playbook is to upgrade a PAN‑OS **high‑availability (HA) pair** safely, with:
- A configuration backup before any change.
- Content (threat/app) updates applied first on both devices.
- An **upgrade of the passive firewall first**, then a controlled failover.
- An upgrade of the previously active firewall while it is out of the traffic path.
- Restoration of the original HA roles and configuration sync.

## Play & Global Variables

1. **Play header and target hosts**
   - The play is named “PAN‑OS HA Content and Software Upgrade with Config Backup”.
   - It runs against the inventory group `PA-HA` by default, which should contain the two firewalls in the HA pair.
   - Corresponding code: `ha_os_upgrade.yml:1-5`.

2. **Connection and credentials**
   - `connection: local` means the Ansible control node (or execution environment) connects to the firewalls over HTTPS/SSH; it does not SSH into the firewalls directly.
   - The `device` variable (step 3) bundles three inputs which must be provided per host through inventory or a job template:
     - `ip_address`
     - `username`
     - `password`
   - This `device` variable is reused in many later tasks that talk to the firewalls’ APIs.
   - Corresponding code: `ha_os_upgrade.yml:4-11`.

3. **Backup location**
   - `backup_directory` is set to an environment variable (`PANOS_BACKUP_DIR`) if present, or `/runner/backups` otherwise. `/runner` is the default working directory inside the automation container.
   - `backup_filename` is built from `backup_directory` and the Ansible `inventory_hostname` (for example, `backups/121UPGRADE-running-config.xml`).
   - These variables are later used in the configuration backup task, so they define where every pre‑upgrade backup file will be stored on the controller.
   - Corresponding code: `ha_os_upgrade.yml:13-15`.

4. **Control flags**
   - `reboot_between_steps` and `quiet_polling` are declared for clarity and future use, but the current upgrade logic is driven by a dedicated task file `tasks/upgrade_step_v2.yml` which implements the actual reboot and polling behavior.
   - Corresponding code: `ha_os_upgrade.yml:16-17` and `tasks/upgrade_step_v2.yml`.

5. **Collection selection**
   - The play declares that it uses the official `paloaltonetworks.panos` Ansible collection. All PAN‑OS‑specific tasks (facts, backups, upgrades, HA checks) come from this collection.
   - Corresponding code: `ha_os_upgrade.yml:19-20`.

## Validation & HA Discovery

6. **Validate that an upgrade path is provided**
   - This step checks that `upgrade_path` is defined and not empty.
   - `upgrade_path` is an ordered list of PAN‑OS versions (for example `["11.1.6-h10", "11.1.6-h14"]`) and must be passed into the job as an extra variable.
   - The task runs only once (`run_once: true`) to fail fast if that critical input is missing; later upgrade tasks depend on having this list.
   - Corresponding code: `ha_os_upgrade.yml:22-29`.

7. **Collect HA and system facts**
   - For each firewall, the play calls `panos_facts` with `gather_subset: ["system", "ha"]`.
   - This returns structured data including: hostname, serial number, whether HA is enabled, the HA mode (active‑passive), the device’s current HA role (active or passive), and the HA group ID.
   - The result is stored in `ha_facts` and used in the next step to create a per‑device summary.
   - Corresponding code: `ha_os_upgrade.yml:31-35`.

8. **Collect the full running configuration**
   - For each firewall, the play calls `panos_facts` again with `gather_subset: ["config"]`.
   - This returns the full device configuration as XML in `ha_cfg.ansible_facts.ansible_net_config`.
   - Later steps extract the HA1 interface and peer settings from this XML so that HA changes are aligned with the live configuration and not with guesses in inventory.
   - Corresponding code: `ha_os_upgrade.yml:37-41`.

9. **Record a per‑device HA snapshot (`ha_runtime`)**
   - Using the facts gathered in steps 7 and 8, the play sets an Ansible fact called `ha_runtime` for each host.
   - `ha_runtime` contains:
     - `inventory_hostname` (Ansible’s name for the host),
     - `hostname` (device hostname),
     - `serial` (device serial number),
     - `ha_enabled` (whether HA is turned on),
     - `ha_mode` (e.g., `active-passive`),
     - `ha_initial_role` (current role: `active` or `passive`),
     - `ha_group_id` (numeric HA group ID, e.g., `20`).
   - This snapshot is later used in the “topology view” step to understand which device is currently active and which is passive.
   - Corresponding code: `ha_os_upgrade.yml:43-52`.

10. **Discover HA1 interface and peer IP from the running config**
    - The play parses the XML configuration captured in step 8 to find:
      - The IP address, netmask, and physical port associated with HA1 (`ha1_ip_address`, `ha1_netmask`, `ha1_port`).
      - The HA peer’s IP address (`ha_peer_ip`), as stored under the HA group settings.
    - These values are read from the device, not from inventory, so they always reflect the actual HA wiring.
    - While `ha_peer_ip` is discovered here, the upgraded flow no longer relies on passing this back into any high‑level configuration module; it is mostly a safety check to confirm we understand the HA layout.
    - Corresponding code: `ha_os_upgrade.yml:54-75`.

11. **Validate that HA1 and peer information were discovered**
    - This assert checks that all four derived values are non‑empty:
      - `ha1_ip_address`,
      - `ha1_netmask`,
      - `ha1_port`,
      - `ha_peer_ip`.
    - If any are missing, the play stops with a clear error, because attempting to automate HA changes without understanding the HA wiring would be unsafe.
    - Corresponding code: `ha_os_upgrade.yml:77-86`.

12. **Build an overall HA topology view**
    - This block runs only once, delegated to the controller, and works with all devices at once.
    - It creates `ha_view`, a list of the `ha_runtime` snapshots built in step 9 for each host.
    - First, it asserts that:
      - There are exactly two firewalls in the group.
      - Both report HA enabled.
      - Both report the same mode, and that mode is `active-passive`.
      - Exactly one node reports an initial role of `active`.
      - Exactly one node reports an initial role of `passive`.
    - Next, it sets:
      - `ha_active_host` to the inventory name of the node reported as initial `active`.
      - `ha_passive_host` to the inventory name of the node reported as initial `passive`.
    - These two variables (introduced in this step) are used later in the controller‑driven block (step 25) to decide which IP to upgrade first and which to suspend.
    - Corresponding code: `ha_os_upgrade.yml:88-108`.

13. **Mark initial role flags on each device**
    - For each firewall, the play sets two simple booleans:
      - `is_initial_active` is true if this host’s `ha_initial_role` (from step 9) is `active`.
      - `is_initial_passive` is true if it is `passive`.
    - These flags are used later in some conditional steps (for example, in the final HA role checks in steps 37–38) to ensure the play treats each device according to its starting role.
    - Corresponding code: `ha_os_upgrade.yml:110-113`.

## Content Update & Backup (Per Device)

14. **Ensure the device is healthy before starting**
    - For each host, `panos_check` is used to confirm the firewall reports itself as ready.
    - The task retries several times, pausing between checks, and only continues when the device is in a “Device is ready” state.
    - This reduces the risk of starting content or software changes while a device is already busy or in a warning state.
    - Corresponding code: `ha_os_upgrade.yml:115-121`.

15–18. **Refresh and install the latest content (threat database)**
    - The play:
      - Asks the firewall to check for the latest content package (`request content upgrade check`).
      - Requests the download of the latest content (`request content upgrade download latest`) and records the resulting job ID.
      - Polls that job ID until the download job finishes and does not report a failure.
      - Starts the installation of the downloaded content (`request content upgrade install version latest`) and again polls a job ID until completion, treating any “FAIL” result as an error.
    - These steps ensure both HA peers are up‑to‑date with signatures and threat intelligence before any version upgrade is attempted.
    - Corresponding code: `ha_os_upgrade.yml:123-177`.

19. **Confirm device readiness after content install**
    - After content installation, the play again uses `panos_check` per host to wait until each firewall reports “Device is ready.”
    - This prevents the upgrade sequence from starting while a device is still settling after a content update.
    - Corresponding code: `ha_os_upgrade.yml:179-186`.

20. **Take a configuration backup**
    - Using the `backup_filename` set in step 3, the play runs `panos_export` with `category: configuration`.
    - For each host, the current running configuration is exported to the controller under the backups directory.
    - These backups are crucial: they provide a recovery point if anything in the subsequent upgrade or failover process goes wrong.
    - Corresponding code: `ha_os_upgrade.yml:188-193`.

## Config Sync Disable (Per Device)

21. **Disable HA configuration sync on each firewall**
    - Rather than using a high‑level HA module, the play uses `panos_type_cmd` to change a single HA setting:
      - It runs a `set` operation to modify the HA XML path:  
        `/config/devices/entry[@name='localhost.localdomain']/deviceconfig/high-availability/group/configuration-synchronization`
      - It sets the `<enabled>` element under that path to `no`.
    - This change tells each firewall to stop automatically pushing configuration changes to its HA peer while the upgrade is in progress, reducing the risk of unwanted config propagation mid‑maintenance.
    - The decision to use `panos_type_cmd` here is based on earlier experience: a more general HA module tried to modify HA interfaces and other settings, which is not desirable in this environment.
    - Corresponding code: `ha_os_upgrade.yml:195-200`.

22. **Commit the “config sync disabled” change**
    - `panos_commit_firewall` is called for each host with a clear description.
    - PAN‑OS only applies configuration changes after a commit, so this step is what actually activates the “config sync disabled” state on both devices.
    - Corresponding code: `ha_os_upgrade.yml:202-205`.

23–24. **Sanity check HA state after disabling config sync**
    - The play re‑runs `panos_facts` for the HA subset and stores the result in `ha_post_disable`.
    - It then asserts that:
      - HA is still enabled.
      - HA mode is still `active-passive`.
      - The local HA role is still either `active` or `passive` (i.e., not “suspended” or some unexpected state).
    - This verifies that the config‑sync change did not break the fundamental HA relationship.
    - Corresponding code: `ha_os_upgrade.yml:207-219`.

## Passive‑First Upgrade Orchestration (Controller‑Driven)

25. **Start the “passive‑first” upgrade block**
    - This block runs once on the controller, using the `ha_active_host` and `ha_passive_host` variables defined in step 12.
    - Inside the block, the play refers directly to these two hostnames to decide which device to talk to at each step.
    - Corresponding code: `ha_os_upgrade.yml:221-226`.

26. **Ensure no commit is currently running on the passive**
    - Before upgrading the passive, the play uses `panos_op` to run `show jobs all` on the passive device.
    - It checks the returned XML to confirm there is no commitment job in an active or pending state.
    - This step loops until no commit is in progress, which prevents overlap between normal configuration commits and the upgrade actions.
    - Corresponding code: `ha_os_upgrade.yml:227-238`.

27. **Upgrade the passive firewall through the full upgrade path**
    - This step calls `include_tasks: tasks/upgrade_step_v2.yml` once for each version in `upgrade_path`.
    - It passes:
      - `version_item` – the specific target version for that loop iteration.
      - A `device` provider pointing at the passive firewall’s IP, username, and password (the same values provided in inventory and grouped earlier).
    - `upgrade_step_v2.yml` (defined elsewhere in the repo) performs, for each version:
      - Software image download.
      - Software installation without immediate restart.
      - Controlled restart of the firewall.
      - Waiting for the device to go down and come back up on the management port.
      - A readiness check (`panos_check` for “Device is ready”).
      - A final version check with `panos_facts` and an assertion that the expected PAN‑OS version is installed.
    - After this loop completes, the previously passive firewall has been fully upgraded to the final target version, while the original active firewall is still carrying traffic.
    - Corresponding code: `ha_os_upgrade.yml:240-250` and `tasks/upgrade_step_v2.yml`.

28. **Suspend the original active firewall to trigger failover**
    - Using `panos_op` with the credentials of `active_host`, the play runs:
      - `request high-availability state suspend`
    - This moves the original active firewalls into a suspended HA state so that the newly upgraded passive can take over as the active device.
    - Corresponding code: `ha_os_upgrade.yml:252-258`.

29–30. **Wait until the upgraded firewall is active and healthy**
    - Step 29 uses `panos_facts` on the upgraded firewall (the former passive) to poll its HA role until it reports `active`.
    - Step 30 uses `panos_check` on that same firewall until it reports “Device is ready.”
    - These two tasks ensure the upgraded firewall is both in control of the traffic (role) and fully operational (health) before moving forward.
    - Corresponding code: `ha_os_upgrade.yml:260-283`.

31. **Ensure the original active firewall has no running commit**
    - Similar to step 26, the play uses `panos_op` and `show jobs all` on the original active device.
    - It waits until no commit job is running on that node.
    - This prevents any conflicting configuration operations during the subsequent upgrade of this device.
    - Corresponding code: `ha_os_upgrade.yml:285-296`.

32. **Upgrade the (now suspended) original active firewall**
    - The play again loops over `upgrade_path`, including `tasks/upgrade_step_v2.yml`.
    - This time, it passes a `device` provider built from the credentials of `active_host`.
    - The same download, install, restart, readiness, and version checks are performed as for the passive.
    - Because this firewall is suspended in HA, it is not actively handling production traffic during the upgrade and reboot.
    - Corresponding code: `ha_os_upgrade.yml:298-308` and `tasks/upgrade_step_v2.yml`.

33. **Bring the suspended firewall back to a functional HA state**
    - Once the former active has been upgraded and is ready, the play runs:
      - `request high-availability state functional` on that device.
    - This returns the upgraded firewall to a normal HA role (active or passive, depending on the cluster’s behavior and preemption settings).
    - Corresponding code: `ha_os_upgrade.yml:310-316`.

## Config Sync Re‑enable and Final Role Checks

34. **Re‑enable configuration sync on each firewall**
    - Using the same targeted approach as the disable step, the play runs `panos_type_cmd` per host:
      - `cmd: set`
      - `xpath: "/config/devices/entry[@name='localhost.localdomain']/deviceconfig/high-availability/group/configuration-synchronization"`
      - `element: "<enabled>yes</enabled>"`
    - This turns HA configuration synchronization back on but does not yet commit it.
    - Corresponding code: `ha_os_upgrade.yml:318-323`.

35. **Commit the “config sync enabled” change**
    - `panos_commit_firewall` is executed per device to make the re‑enablement effective.
    - From this point on, future configuration changes can be synchronized between peers again.
    - Corresponding code: `ha_os_upgrade.yml:325-328`.

36. **Sync the running configuration from the original active to its peer**
    - On the device that was originally active (identified earlier in step 12 as `ha_active_host`), the play sends:
      - `request high-availability sync-to-remote running-config`.
    - This ensures the peer’s running configuration is aligned with the newly upgraded active device.
    - Corresponding code: `ha_os_upgrade.yml:330-334`.

37–38. **Wait for the original roles to return**
    - Step 37 uses `panos_facts` (HA subset) on each device that started as active (`is_initial_active` = true) to wait until its HA role returns to `active`.
    - Step 38 does the same for nodes that started as passive (`is_initial_passive` = true), waiting until their role returns to `passive`.
    - These loops confirm that, after all upgrades and failovers, the HA pair has settled back into the same pattern it had at the beginning (unless your HA policy intentionally shifts it).
    - Corresponding code: `ha_os_upgrade.yml:336-354`.

39. **Final summary**
    - A `debug` message (run once) prints:
      - The original active host’s name and reports that it is active again.
      - The original passive host’s name and reports that it is passive again.
      - The backup directory location where configuration backups were stored.
    - This provides an at‑a‑glance summary confirming:
      - Both nodes have been upgraded through the requested versions.
      - HA is healthy and roles are as expected.
      - Backups exist for both devices.
    - Corresponding code: `ha_os_upgrade.yml:356-361`.

---

In short, `ha_os_upgrade.yml` implements an HA‑aware, passive‑first upgrade with explicit safety rails at each stage:
- It refuses to run without an explicit upgrade path.
- It discovers and verifies HA topology and wiring before making changes.
- It backs up configuration before touching content or software.
- It pauses to ensure devices are ready at every major step.
- It disables config sync in a narrow, controlled way and commits the change.
- It upgrades the passive first, then carefully fails over and upgrades the original active.
- It re‑enables config sync, synchronizes configuration, and confirms the HA pair returns to a known good state.
