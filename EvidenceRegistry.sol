// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

contract EvidenceRegistry is Ownable {
    enum Status {
        Pending,
        Approved,
        Rejected
    }

    struct Evidence {
        uint256 id;
        string caseId;
        string fileHash;
        string fileName;
        address uploader;
        uint256 timestamp;
        Status status;
        address reviewedBy;
        uint256 reviewedAt;
        string reviewNote;
        bool exists;
    }

    uint256 public nextEvidenceId = 1;

    mapping(uint256 => Evidence) private evidenceRecords;
    mapping(string => uint256[]) private evidenceIdsByCase;
    mapping(address => uint256[]) private evidenceIdsByUser;
    uint256[] private allEvidenceIds;

    mapping(address => bool) public authorizedUsers;
    mapping(address => uint256) public trustScores;
    mapping(address => uint256) public lastResetTime;
    mapping(address => uint256) public postsInWindow;

    mapping(address => uint256) public approvedCounts;
    mapping(address => uint256) public rejectedCounts;
    mapping(address => uint256) public pendingCounts;

    address[] private registeredUsers;
    mapping(address => bool) private isRegistered;

    event EvidenceSubmitted(
        uint256 indexed evidenceId,
        string caseId,
        string fileHash,
        string fileName,
        address indexed uploader,
        uint256 timestamp,
        uint8 status
    );

    event EvidenceReviewed(
        uint256 indexed evidenceId,
        address indexed reviewer,
        bool approved,
        string reviewNote,
        uint256 reviewedAt
    );

    event UserAuthorized(address indexed user);
    event UserRevoked(address indexed user);
    event TrustScoreUpdated(address indexed user, uint256 newScore);

    constructor(address initialOwner) Ownable(initialOwner) {
        _registerUser(initialOwner);
        authorizedUsers[initialOwner] = true;
        trustScores[initialOwner] = 100;
    }

    modifier onlyAuthorized() {
        require(
            authorizedUsers[msg.sender] || msg.sender == owner(),
            "Not authorized to submit evidence"
        );
        _;
    }

    modifier onlyReviewer() {
        bool isOwner = msg.sender == owner();
        bool isHighTrustReviewer = authorizedUsers[msg.sender] && trustScores[msg.sender] >= 90;

        require(isOwner || isHighTrustReviewer, "Not allowed to review evidence");
        _;
    }

    function _registerUser(address user) internal {
        if (!isRegistered[user]) {
            isRegistered[user] = true;
            registeredUsers.push(user);
        }
    }

    function authorizeUser(address user) external onlyOwner {
        require(user != address(0), "Invalid user address");

        authorizedUsers[user] = true;
        _registerUser(user);

        if (trustScores[user] == 0) {
            trustScores[user] = 50;
            emit TrustScoreUpdated(user, 50);
        }

        emit UserAuthorized(user);
    }

    function revokeUser(address user) external onlyOwner {
        authorizedUsers[user] = false;
        emit UserRevoked(user);
    }

    // Demo helper: lets owner set role scores like 95 reviewer / 75 regular / 50 new
    function adminSetTrustScore(address user, uint256 score) external onlyOwner {
        require(score <= 100, "Score must be <= 100");
        _registerUser(user);
        trustScores[user] = score;
        emit TrustScoreUpdated(user, score);
    }

    function _increaseScore(address user, uint256 amount) internal {
        uint256 newScore = trustScores[user] + amount;
        if (newScore > 100) {
            newScore = 100;
        }
        trustScores[user] = newScore;
        emit TrustScoreUpdated(user, newScore);
    }

    function _decreaseScore(address user, uint256 amount) internal {
        uint256 current = trustScores[user];
        uint256 newScore = amount >= current ? 0 : current - amount;
        trustScores[user] = newScore;
        emit TrustScoreUpdated(user, newScore);
    }

    function _checkAndUpdatePostingLimit(address user) internal {
        if (trustScores[user] >= 90) {
            return;
        }

        if (block.timestamp >= lastResetTime[user] + 1 days) {
            lastResetTime[user] = block.timestamp;
            postsInWindow[user] = 0;
        }

        require(postsInWindow[user] < 3, "Posting limit reached for 24h");
        postsInWindow[user] += 1;
    }

    function submitEvidence(
        string memory caseId,
        string memory fileHash,
        string memory fileName
    ) external onlyAuthorized {
        require(bytes(caseId).length > 0, "Case ID required");
        require(bytes(fileHash).length > 0, "File hash required");
        require(bytes(fileName).length > 0, "File name required");

        if (trustScores[msg.sender] == 0) {
            trustScores[msg.sender] = 50;
            emit TrustScoreUpdated(msg.sender, 50);
        }

        require(trustScores[msg.sender] >= 30, "User banned from posting");

        _registerUser(msg.sender);
        _checkAndUpdatePostingLimit(msg.sender);

        uint256 evidenceId = nextEvidenceId;
        nextEvidenceId += 1;

        Status initialStatus = trustScores[msg.sender] >= 70
            ? Status.Approved
            : Status.Pending;

        evidenceRecords[evidenceId] = Evidence({
            id: evidenceId,
            caseId: caseId,
            fileHash: fileHash,
            fileName: fileName,
            uploader: msg.sender,
            timestamp: block.timestamp,
            status: initialStatus,
            reviewedBy: address(0),
            reviewedAt: 0,
            reviewNote: initialStatus == Status.Approved ? "Auto-approved by trust score" : "",
            exists: true
        });

        evidenceIdsByCase[caseId].push(evidenceId);
        evidenceIdsByUser[msg.sender].push(evidenceId);
        allEvidenceIds.push(evidenceId);

        if (initialStatus == Status.Pending) {
            pendingCounts[msg.sender] += 1;
        } else {
            approvedCounts[msg.sender] += 1;
            _increaseScore(msg.sender, 10);
        }

        emit EvidenceSubmitted(
            evidenceId,
            caseId,
            fileHash,
            fileName,
            msg.sender,
            block.timestamp,
            uint8(initialStatus)
        );
    }

    function reviewEvidence(
        uint256 evidenceId,
        bool approve,
        string memory reviewNote
    ) external onlyReviewer {
        require(evidenceRecords[evidenceId].exists, "Evidence does not exist");

        Evidence storage e = evidenceRecords[evidenceId];

        require(e.status == Status.Pending, "Evidence is not pending");
        require(e.uploader != msg.sender, "Cannot review your own evidence");

        if (pendingCounts[e.uploader] > 0) {
            pendingCounts[e.uploader] -= 1;
        }

        e.reviewedBy = msg.sender;
        e.reviewedAt = block.timestamp;
        e.reviewNote = reviewNote;

        if (approve) {
            e.status = Status.Approved;
            approvedCounts[e.uploader] += 1;
            _increaseScore(e.uploader, 10);
        } else {
            e.status = Status.Rejected;
            rejectedCounts[e.uploader] += 1;
            _decreaseScore(e.uploader, 15);
        }

        emit EvidenceReviewed(
            evidenceId,
            msg.sender,
            approve,
            reviewNote,
            block.timestamp
        );
    }

    function verifyEvidence(
        uint256 evidenceId,
        string memory hashToCheck
    ) external view returns (bool) {
        require(evidenceRecords[evidenceId].exists, "Evidence does not exist");

        return keccak256(abi.encodePacked(evidenceRecords[evidenceId].fileHash)) ==
            keccak256(abi.encodePacked(hashToCheck));
    }

    function getEvidence(
        uint256 evidenceId
    )
        external
        view
        returns (
            uint256,
            string memory,
            string memory,
            string memory,
            address,
            uint256,
            uint8,
            address,
            uint256,
            string memory
        )
    {
        require(evidenceRecords[evidenceId].exists, "Evidence does not exist");

        Evidence memory e = evidenceRecords[evidenceId];

        return (
            e.id,
            e.caseId,
            e.fileHash,
            e.fileName,
            e.uploader,
            e.timestamp,
            uint8(e.status),
            e.reviewedBy,
            e.reviewedAt,
            e.reviewNote
        );
    }

    function getEvidenceIdsByCase(
        string memory caseId
    ) external view returns (uint256[] memory) {
        return evidenceIdsByCase[caseId];
    }

    function getEvidenceIdsByUser(
        address user
    ) external view returns (uint256[] memory) {
        return evidenceIdsByUser[user];
    }

    function getAllEvidenceIds() external view returns (uint256[] memory) {
        return allEvidenceIds;
    }

    function getRegisteredUsers() external view returns (address[] memory) {
        return registeredUsers;
    }

    function getUserStats(
        address user
    )
        external
        view
        returns (
            bool isAuthorized,
            uint256 score,
            uint256 approved,
            uint256 rejected,
            uint256 pending,
            uint256 totalUploads
        )
    {
        return (
            authorizedUsers[user],
            trustScores[user],
            approvedCounts[user],
            rejectedCounts[user],
            pendingCounts[user],
            evidenceIdsByUser[user].length
        );
    }

    function canPost(address user) external view returns (bool) {
        if (trustScores[user] < 30) {
            return false;
        }

        if (trustScores[user] >= 90) {
            return true;
        }

        if (block.timestamp >= lastResetTime[user] + 1 days) {
            return true;
        }

        return postsInWindow[user] < 3;
    }
}