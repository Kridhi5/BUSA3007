const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("EvidenceRegistry", function () {
  let contract;
  let owner;
  let user1;

  beforeEach(async function () {
    [owner, user1] = await ethers.getSigners();

    const EvidenceRegistry = await ethers.getContractFactory("EvidenceRegistry");
    contract = await EvidenceRegistry.deploy(owner.address);

    await contract.waitForDeployment();
  });

  it("should authorize a user", async function () {
    await contract.authorizeUser(user1.address);

    expect(await contract.authorizedUsers(user1.address)).to.equal(true);
    expect(await contract.trustScores(user1.address)).to.equal(40);
  });

  it("should allow authorized user to submit evidence", async function () {
    await contract.authorizeUser(user1.address);

    await contract.connect(user1).submitEvidence("CASE001", "hash123");

    const evidence = await contract.getEvidence("CASE001");

    expect(evidence[0]).to.equal("CASE001");
    expect(evidence[1]).to.equal("hash123");
    expect(evidence[2]).to.equal(user1.address);
  });

  it("should verify evidence correctly", async function () {
    await contract.authorizeUser(user1.address);
    await contract.connect(user1).submitEvidence("CASE001", "hash123");

    expect(await contract.verifyEvidence("CASE001", "hash123")).to.equal(true);
    expect(await contract.verifyEvidence("CASE001", "wronghash")).to.equal(false);
  });

  it("should prevent duplicate case IDs", async function () {
    await contract.authorizeUser(user1.address);
    await contract.connect(user1).submitEvidence("CASE001", "hash123");

    await expect(
      contract.connect(user1).submitEvidence("CASE001", "anotherhash")
    ).to.be.revertedWith("Case ID already exists");
  });

  it("should enforce posting limit for low trust users", async function () {
    await contract.authorizeUser(user1.address);

    await contract.connect(user1).submitEvidence("CASE001", "hash1");
    await contract.connect(user1).submitEvidence("CASE002", "hash2");
    await contract.connect(user1).submitEvidence("CASE003", "hash3");

    await expect(
      contract.connect(user1).submitEvidence("CASE004", "hash4")
    ).to.be.revertedWith("Posting limit reached for 24h");
  });

  it("should allow unlimited posts for high trust users", async function () {
    await contract.authorizeUser(user1.address);

    await contract.setTrustScore(user1.address, 95);

    await contract.connect(user1).submitEvidence("CASE001", "hash1");
    await contract.connect(user1).submitEvidence("CASE002", "hash2");
    await contract.connect(user1).submitEvidence("CASE003", "hash3");
    await contract.connect(user1).submitEvidence("CASE004", "hash4");

    const evidence = await contract.getEvidence("CASE004");

    expect(evidence[0]).to.equal("CASE004");
  });
});