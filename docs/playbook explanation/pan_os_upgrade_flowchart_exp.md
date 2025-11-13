# PAN-OS Upgrade Playbook Flowchart

<div style="display: flex; gap: 2rem;">
<div style="flex: 2;">

```mermaid
flowchart TD
    Start([Start Playbook]) --> ValidatePath{Validate upgrade_path<br/>provided?}

    ValidatePath -->|No| FailValidation[Fail: upgrade_path required]
    ValidatePath -->|Yes| CheckReady1[Check Device Ready]

    FailValidation --> End1([End - Failed])

    %% Content Update Section
    CheckReady1 --> RetryReady1{Device Ready?}
    RetryReady1 -->|No, retry < 10| CheckReady1
    RetryReady1 -->|Failed after retries| End2([End - Failed])
    RetryReady1 -->|Yes| RefreshContent[Refresh Content Update Idx]

    RefreshContent --> DownloadContent[Download Latest Content]
    DownloadContent --> ExtractDLJobID[Extract Download Job ID]

    ExtractDLJobID --> HasDLJobID{Job ID exists?}
    HasDLJobID -->|No| InstallContent
    HasDLJobID -->|Yes| WaitDLComplete[Poll Download Job Status]

    WaitDLComplete --> DLComplete{Status FIN?}
    DLComplete -->|No, retry < 300| WaitDLComplete
    DLComplete -->|FAIL result| End3([End - Failed])
    DLComplete -->|Success| InstallContent[Install Latest Content]

    InstallContent --> ExtractInstJobID[Extract Install Job ID]
    ExtractInstJobID --> HasInstJobID{Job ID exists?}

    HasInstJobID -->|No| WaitReadyContent
    HasInstJobID -->|Yes| WaitInstComplete[Poll Install Job Status]

    WaitInstComplete --> InstComplete{Status FIN<br/>or FAIL?}
    InstComplete -->|No, retry < 300| WaitInstComplete
    InstComplete -->|FIN + FAIL result| End4([End - Failed])
    InstComplete -->|FAIL status| End5([End - Failed])
    InstComplete -->|FIN + Success| WaitReadyContent[Wait for Device Ready<br/>after Content Install]

    WaitReadyContent --> ReadyContent{Device Ready?}
    ReadyContent -->|No, retry < 60| WaitReadyContent
    ReadyContent -->|Failed| End6([End - Failed])
    ReadyContent -->|Yes| LoopStart{More versions<br/>in upgrade_path?}

    %% Staged OS Upgrade Loop
    LoopStart -->|No| FinalVerify
    LoopStart -->|Yes| GetNextVersion[Get Next upgrade_path
    Version]

    GetNextVersion --> UpgradeTaskEntry[/"Task: upgrade_step_v2.yml<br/>Target Version"/]

    %% ========================================================================
    %% SUBGRAPH: upgrade_step_v2.yml Task Details
    %% ========================================================================
    subgraph UpgradeStepTask["📋 upgrade_step_v2.yml"]
        direction TB

        UpgradeTaskEntry --> Task1["Task 1: Download PAN-OS<br/>Target Version"]

        Task1 --> Task1Retry{Download<br/>successful?}
        Task1Retry -->|No, retry < 3<br/>wait 60s| Task1
        Task1Retry -->|Failed after 3 retries| End7([End - Failed])
        Task1Retry -->|Yes| Task2["Task 2: Install PAN-OS<br/>Target Version<br/>no restart"]

        Task2 --> Task2Details["panos_software module<br/>download: false<br/>install: true<br/>restart: false"]

        Task2Details --> Task3["Task 3: Restart device<br/>to apply Target Version"]
        Task3 --> Task3Details["panos_op module<br/>request restart system<br/>async: 45, poll: 0"]

        Task3Details --> Task4[Task 4: Wait for port 443<br/>to stop responding]
        Task4 --> Task4Details["wait_for module<br/>port 443 state: stopped<br/>timeout: 300s"]

        Task4Details --> Task4Check{Port 443<br/>stopped?}
        Task4Check -->|Timeout 300s| End8([End - Failed])
        Task4Check -->|Success| Task5[Task 5: Wait for port 443<br/>to start responding]

        Task5 --> Task5Details["wait_for module<br/>port 443 state: started<br/>timeout: 900s"]

        Task5Details --> Task5Check{Port 443<br/>started?}
        Task5Check -->|Timeout 900s| End9([End - Failed])
        Task5Check -->|Success| Task6[Task 6: Wait for device<br/>readiness after upgrade]

        Task6 --> Task6Details["panos_check module<br/>retries: 100<br/>delay: 15s"]

        Task6Details --> Task6Check{Device<br/>ready?}
        Task6Check -->|No, retry < 100| Task6
        Task6Check -->|Failed after retries| End10([End - Failed])
        Task6Check -->|Success| Task7["Task 7: Verify installed
        version is Target Version"]

        Task7 --> Task7Details["panos_facts module<br/>gather_subset: system"]

        Task7Details --> Task8["Task 8: Assert Target Version<br/>installed successfully"]

        Task8 --> Task8Details["Assert:<br/>ansible_net_version<br/>== Target Version"]

        Task8Details --> Task8Check{Version<br/>matches?}
        Task8Check -->|No| End11([End - Failed:<br/>Version mismatch])
        Task8Check -->|Yes| UpgradeTaskExit[/"Return to main playbook"/]
    end

    UpgradeTaskExit --> LoopStart

    %% Final Verification
    FinalVerify[Gather Final System Facts]
    FinalVerify --> DisplayFinal[Display Final Version]
    DisplayFinal --> End12([End - Success])

    %% Styling
    classDef successNode fill:#90EE90,stroke:#006400,stroke-width:2px
    classDef failNode fill:#FFB6C6,stroke:#8B0000,stroke-width:2px
    classDef decisionNode fill:#FFE4B5,stroke:#FF8C00,stroke-width:2px
    classDef processNode fill:#B0E0E6,stroke:#4682B4,stroke-width:2px
    classDef loopNode fill:#DDA0DD,stroke:#8B008B,stroke-width:2px
    classDef taskNode fill:#98FB98,stroke:#228B22,stroke-width:3px
    classDef detailNode fill:#E6E6FA,stroke:#6A5ACD,stroke-width:1px
    classDef entryExit fill:#FFE4E1,stroke:#FF6347,stroke-width:2px

    class End12 successNode
    class End1,End2,End3,End4,End5,End6,End7,End8,End9,End10,End11 failNode
    class ValidatePath,RetryReady1,HasDLJobID,DLComplete,HasInstJobID,InstComplete,ReadyContent,LoopStart,Task1Retry,Task4Check,Task5Check,Task6Check,Task8Check decisionNode
    class Task1,Task2,Task3,Task4,Task5,Task6,Task7,Task8 taskNode
    class Task1Reg,Task2Details,Task3Details,Task4Details,Task5Details,Task6Details,Task6Reg,Task7Details,Task7Reg,Task8Details detailNode
    class GetNextVersion loopNode
    class UpgradeTaskEntry,UpgradeTaskExit entryExit
```

</div>
<div style="flex: 1; padding: 1rem; background-color: #f8f9fa; border-left: 3px solid #4682B4; font-size: 0.9em;">

## Step-by-Step Execution Flow

### 🚀 Start

**1. Start Playbook** - Execution begins

**2. Validate upgrade_path provided?** (Decision)

- ❌ **No** → Fail: upgrade_path required → **End - Failed**
- ✅ **Yes** → Continue to Step 3

### 📋 Initial Readiness Check

**3. Check Device Ready** - Verify device is operational

**4. Device Ready?** (Decision)

- ❌ **No, retry < 10** → Loop back to Step 3
- ❌ **Failed after retries** → **End - Failed**
- ✅ **Yes** → Continue to Step 5

### 📦 Content Update Phase

**5. Refresh Content Update Idx** - Refresh content index

**6. Download Latest Content** - Initiate content download

**7. Extract Download Job ID** - Get job tracking ID

**8. Job ID exists?** (Decision)

- ❌ **No** → Skip to Step 13 (Install Content)
- ✅ **Yes** → Continue to Step 9

**9. Poll Download Job Status** - Monitor download progress

**10. Status FIN?** (Decision)

- 🔄 **No, retry < 300** → Loop back to Step 9
- ❌ **FAIL result** → **End - Failed**
- ✅ **Success** → Continue to Step 11

**11. Install Latest Content** - Install downloaded content

**12. Extract Install Job ID** - Get install job tracking ID

**13. Job ID exists?** (Decision)

- ❌ **No** → Skip to Step 16 (Wait for Device Ready)
- ✅ **Yes** → Continue to Step 14

**14. Poll Install Job Status** - Monitor install progress

**15. Status FIN or FAIL?** (Decision)

- 🔄 **No, retry < 300** → Loop back to Step 14
- ❌ **FIN + FAIL result** → **End - Failed**
- ❌ **FAIL status** → **End - Failed**
- ✅ **FIN + Success** → Continue to Step 16

**16. Wait for Device Ready after Content Install**

**17. Device Ready?** (Decision)

- 🔄 **No, retry < 60** → Loop back to Step 16
- ❌ **Failed** → **End - Failed**
- ✅ **Yes** → Continue to Step 18

### 🔄 Staged OS Upgrade Loop

**18. More versions in upgrade_path?** (Decision)

- ❌ **No** → Skip to Step 37 (Final Verify)
- ✅ **Yes** → Continue to Step 19

**19. Get Next upgrade_path Version** - Retrieve next target version

**20. Task: upgrade_step_v2.yml** - Enter upgrade task for target version

---

### 📋 upgrade_step_v2.yml Task (Steps 21-36)

**21. Task 1: Download PAN-OS Target Version** - Download OS image

**22. Download successful?** (Decision)

- 🔄 **No, retry < 3 (wait 60s)** → Loop back to Step 21
- ❌ **Failed after 3 retries** → **End - Failed**
- ✅ **Yes** → Continue to Step 23

**23. Task 2: Install PAN-OS Target Version (no restart)**

- Uses: `panos_software` module
- Parameters: `download: false`, `install: true`, `restart: false`

**24. Task 3: Restart device to apply Target Version**

- Uses: `panos_op` module
- Command: `request restart system`
- Parameters: `async: 45`, `poll: 0`

**25. Task 4: Wait for port 443 to stop responding**

- Uses: `wait_for` module
- Port: `443`, State: `stopped`, Timeout: `300s`

**26. Port 443 stopped?** (Decision)

- ❌ **Timeout 300s** → **End - Failed**
- ✅ **Success** → Continue to Step 27

**27. Task 5: Wait for port 443 to start responding**

- Uses: `wait_for` module
- Port: `443`, State: `started`, Timeout: `900s` (15 min)

**28. Port 443 started?** (Decision)

- ❌ **Timeout 900s** → **End - Failed**
- ✅ **Success** → Continue to Step 29

**29. Task 6: Wait for device readiness after upgrade**

- Uses: `panos_check` module
- Parameters: `retries: 100`, `delay: 15s`

**30. Device ready?** (Decision)

- 🔄 **No, retry < 100** → Loop back to Step 29
- ❌ **Failed after retries** → **End - Failed**
- ✅ **Success** → Continue to Step 31

**31. Task 7: Verify installed version is Target Version**

- Uses: `panos_facts` module
- Parameter: `gather_subset: system`

**32. Task 8: Assert Target Version installed successfully**

- Assert: `ansible_net_version == Target Version`

**33. Version matches?** (Decision)

- ❌ **No** → **End - Failed: Version mismatch**
- ✅ **Yes** → Continue to Step 34

**34. Return to main playbook** - Exit upgrade_step_v2.yml task

---

**35. Loop back to Step 18** - Check for more versions to upgrade

### ✅ Final Verification

**36. Gather Final System Facts** - Collect final device information

**37. Display Final Version** - Show successfully installed version

**38. End - Success** 🎉 - Playbook completed successfully

---

### 🛡️ Failure Points Summary

The playbook can fail and halt at:

- Missing upgrade_path parameter
- Initial device readiness check (10 retries)
- Content download job failure (300 retries)
- Content install job failure (300 retries)
- Device not ready after content install (60 retries)
- OS download failure (3 retries per version)
- Port 443 not stopping (300s timeout)
- Port 443 not starting (900s timeout)
- Device not ready after upgrade (100 retries)
- Version mismatch after upgrade

</div>
</div>
