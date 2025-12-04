# Azure AD and On-Premises AD Hybrid Architecture

## Overview

This architecture diagram illustrates a hybrid Active Directory environment with Azure AD (Entra ID) in the cloud synchronized with multiple on-premises Active Directory sites.

## Architecture Diagram

```mermaid
graph TB
    subgraph "Azure Cloud"
        AAD["Azure AD (Entra ID)<br/>Cloud Identity Platform"]
        AADUsers["Cloud Users<br/>Synced from On-Prem"]
        AADConnect["Azure AD Connect<br/>Sync Service"]
        
        AAD --> AADUsers
    end
    
    subgraph "On-Premises Environment"
        subgraph "Site 1 - Primary DC"
            DC1["Primary Domain Controller<br/>AD DS + DNS + GC"]
            Site1Users["Site 1 Users<br/>& Computers"]
            Site1RODC["Read-Only DC<br/>(Optional)"]
            
            DC1 --> Site1Users
            DC1 -.Replication.-> Site1RODC
        end
        
        subgraph "Site 2 - Branch Office"
            DC2["Domain Controller<br/>AD DS + DNS + GC"]
            Site2Users["Site 2 Users<br/>& Computers"]
            Site2RODC["Read-Only DC<br/>(Optional)"]
            
            DC2 --> Site2Users
            DC2 -.Replication.-> Site2RODC
        end
        
        subgraph "Site 3 - Branch Office"
            DC3["Domain Controller<br/>AD DS + DNS + GC"]
            Site3Users["Site 3 Users<br/>& Computers"]
            Site3RODC["Read-Only DC<br/>(Optional)"]
            
            DC3 --> Site3Users
            DC3 -.Replication.-> Site3RODC
        end
        
        subgraph "Sync Infrastructure"
            SyncServer["Azure AD Connect Server<br/>Installed at Primary Site"]
        end
    end
    
    subgraph "Client Access"
        OnPremClients["On-Premises Clients<br/>Domain Joined"]
        CloudClients["Cloud/Remote Clients<br/>Azure AD Joined"]
    end
    
    %% Replication between DCs
    DC1 <==AD Replication==> DC2
    DC2 <==AD Replication==> DC3
    DC3 <==AD Replication==> DC1
    
    %% Sync to Azure AD
    SyncServer -->|Reads User/Group Data| DC1
    SyncServer -->|Password Hash Sync<br/>or Pass-through Auth| AADConnect
    AADConnect -->|HTTPS 443| AAD
    
    %% Client Authentication
    OnPremClients -->|Kerberos/NTLM| DC1
    OnPremClients -->|Kerberos/NTLM| DC2
    OnPremClients -->|Kerberos/NTLM| DC3
    
    CloudClients -->|OAuth 2.0/SAML| AAD
    
    %% Styling
    classDef azureClass fill:#0078D4,stroke:#004578,stroke-width:2px,color:#fff
    classDef dcClass fill:#00A4EF,stroke:#006BA6,stroke-width:2px,color:#fff
    classDef userClass fill:#50E6FF,stroke:#00B7C3,stroke-width:2px,color:#000
    classDef syncClass fill:#FFB900,stroke:#D39400,stroke-width:2px,color:#000
    classDef clientClass fill:#00CC6A,stroke:#008A4C,stroke-width:2px,color:#fff
    
    class AAD,AADUsers,AADConnect azureClass
    class DC1,DC2,DC3,Site1RODC,Site2RODC,Site3RODC dcClass
    class Site1Users,Site2Users,Site3Users userClass
    class SyncServer syncClass
    class OnPremClients,CloudClients clientClass
```

## Key Components

### Azure Cloud
- **Azure AD (Entra ID)**: Cloud-based identity and access management service
- **Cloud Users**: User accounts synchronized from on-premises AD
- **Azure AD Connect**: Synchronization service that bridges on-prem and cloud

### On-Premises Sites
Each site contains:
- **Domain Controller (DC)**: Hosts Active Directory Domain Services, DNS, and Global Catalog
- **Users & Computers**: Local objects managed within each site
- **Read-Only DC (Optional)**: For branch offices with limited physical security

### Synchronization Infrastructure
- **Azure AD Connect Server**: Installed at the primary site, reads from on-prem AD and syncs to Azure AD

### Client Types
- **On-Premises Clients**: Traditional domain-joined devices using Kerberos/NTLM
- **Cloud Clients**: Azure AD-joined devices for cloud-only scenarios

## Authentication Methods

The architecture supports multiple authentication methods:

1. **Password Hash Synchronization (PHS)**: Most common, syncs password hashes to Azure AD
2. **Pass-through Authentication (PTA)**: Validates passwords against on-prem AD in real-time

## Replication & Synchronization

- **AD Replication**: Multi-master replication between all domain controllers across sites
- **Azure AD Connect Sync**: One-way sync from on-prem AD to Azure AD (typically every 30 minutes)
- **Site Links**: Configure site link costs and replication schedules based on WAN bandwidth

## High Availability Considerations

- Multiple domain controllers per site for redundancy
- Azure AD Connect can be configured in staging mode for failover

## Security Best Practices

- Use Azure AD Conditional Access policies
- Implement MFA for cloud access
- Secure Azure AD Connect server (dedicated, hardened)
- Use Read-Only DCs in branch offices with limited security
- Enable Azure AD Connect Health for monitoring
- Implement least-privilege access for sync accounts
