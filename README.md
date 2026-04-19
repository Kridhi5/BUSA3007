# BUSA3007
Blockchain Group Assignment 
The files uploaded are the smart contract, application codes and the evidence registery where all the files uploaded to the blockchain will stored. It stores the cyptographic file hashes on chain by avoidng the dependence on centralised storage and preventing post submission tampering. 

## Key Features 
* Tamper resistant evidence logging through blockchain immutability.
* SHA -256 file hashing for integrity verification.
* Smart Contrcat based access control with role authorisation. The role authorisation means there is an admin who can control the activities for the blockchain in terms of approving or rejecting submissions for users that have a score less than 70.
* Deterministic evidence verification through hash comparision. The file uploaded initially will have a hash and if it needs to be verified, the user has to upload the same file whereby the system will cross check the hash for the both the files.

## System Architecture 
There is 3 layers in the web application:
* Smart Contract ( found in the EvidenceRegistery.sol file) enforces system logic and store evidence metadata.
* Frontend(developed using Streamlit) provides an interface for evidence upload and verfication.
* Local Blockchain(Hardhat) used for development, testing and deployment.
Only evidence metadata(case ID, filehash, uploader address, timestamp) is stored in the system, while the actual files are processed off chain to maintain scalability.

## Smart Contrcat Capabilities 
* submitEvidence(): submit hashed evidence which is only for authorised users only.
* verifyEvidence(): verify file authenticity using hash comparison.
* getEvidence() : retrive stored evidence metadata.
* Role based user management with authoris/revoke functionaility.

## Trust & Activity Control
The trust based scoring system limits evidence submission to:
* prevent abuse and over submission.
* enforce posting limits based on user. So a user can only submit three files in every 24 hours regardless of the user status in the system.

## Workflow Overview 

```mermaid
flowchart LR
    A[User uploads file] --> B[File hashed using SHA-256]
    B --> C[Hash & metadata stored on-chain]
    C --> D[Future file uploaded]
    D --> E[Rehash file]
    E --> F{Hash matches on-chain record?}
    F -->|Yes| G[File verified as authentic ✅]
    F -->|
