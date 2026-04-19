This documentation is regarding the file EvidenceRegistry.js
This test suite ensures that the smart contract works using Hardhat, Ethers.js and Chai. 
# Purpose 
## User Authorisation 
* Verifies that the contract owner can authorise users
* Ensures authorised users are correctly stored.
* Assigns an initial score which is 40.
## Evidence Submission
Confirms that only authorised users can submit evidence. 
## Evidence Verification
* Checks whether submitted evidence matches stored hashes
* Returns:
  * true for valid evidence
  * false for tampered or incorrect data

It simulates real world usage where evidence must remain tamper proof, traceable, and secure. It is not deployed on the blockchain, used by end users and does not store real data. 
