// SPDX-License-Identifier: MIT
pragma solidity 0.8.36;

/// @title RecallOpsReceiptRegistry
/// @notice Anchors non-sensitive policy decision digests after RecallOps authorization.
/// @dev This registry is an audit anchor. Sibyl Memory remains the policy authority.
contract RecallOpsReceiptRegistry {
    enum Decision {
        APPROVE,
        DENY,
        ESCALATE
    }

    struct Anchor {
        bytes32 recordHash;
        uint64 anchoredAt;
        Decision decision;
        bool exists;
    }

    uint256 public constant LOCAL_ANVIL_CHAIN_ID = 31_337;
    uint256 public constant BASE_SEPOLIA_CHAIN_ID = 84_532;

    address public immutable authorizedSubmitter;
    uint256 public immutable deployedChainId;
    uint256 public anchorCount;

    mapping(bytes32 receiptIdDigest => Anchor anchor) private _anchors;

    event ReceiptAnchored(
        bytes32 indexed receiptIdDigest,
        bytes32 indexed decisionDigest,
        Decision decision,
        address indexed actor,
        uint64 anchoredAt,
        bytes32 acpJobReferenceDigest
    );

    error UnauthorizedSubmitter(address caller);
    error ZeroAddress();
    error ZeroReceiptIdDigest();
    error ZeroDecisionDigest();
    error UnsupportedChain(uint256 chainId);
    error DeploymentChainIdMismatch(uint256 expected, uint256 actual);
    error RuntimeChainIdMismatch(uint256 expected, uint256 actual);
    error ReceiptConflict(
        bytes32 receiptIdDigest, bytes32 existingRecordHash, bytes32 newRecordHash
    );

    constructor(address submitter, uint256 expectedChainId) {
        if (submitter == address(0)) revert ZeroAddress();
        if (expectedChainId != LOCAL_ANVIL_CHAIN_ID && expectedChainId != BASE_SEPOLIA_CHAIN_ID) {
            revert UnsupportedChain(expectedChainId);
        }
        if (block.chainid != expectedChainId) {
            revert DeploymentChainIdMismatch(expectedChainId, block.chainid);
        }
        authorizedSubmitter = submitter;
        deployedChainId = expectedChainId;
    }

    /// @notice Anchor one receipt, returning false for an exact idempotent replay.
    function anchorReceipt(
        bytes32 receiptIdDigest,
        bytes32 decisionDigest,
        Decision decision,
        bytes32 acpJobReferenceDigest
    ) external returns (bool created) {
        _checkRuntimeChain();
        if (msg.sender != authorizedSubmitter) revert UnauthorizedSubmitter(msg.sender);
        if (receiptIdDigest == bytes32(0)) revert ZeroReceiptIdDigest();
        if (decisionDigest == bytes32(0)) revert ZeroDecisionDigest();

        bytes32 recordHash = computeRecordHash(decisionDigest, decision, acpJobReferenceDigest);
        Anchor storage existing = _anchors[receiptIdDigest];
        if (existing.exists) {
            if (existing.recordHash != recordHash) {
                revert ReceiptConflict(receiptIdDigest, existing.recordHash, recordHash);
            }
            return false;
        }

        uint64 anchoredAt = uint64(block.timestamp);
        _anchors[receiptIdDigest] = Anchor({
            recordHash: recordHash, anchoredAt: anchoredAt, decision: decision, exists: true
        });
        unchecked {
            ++anchorCount;
        }
        emit ReceiptAnchored(
            receiptIdDigest, decisionDigest, decision, msg.sender, anchoredAt, acpJobReferenceDigest
        );
        return true;
    }

    function getAnchor(bytes32 receiptIdDigest) external view returns (Anchor memory) {
        return _anchors[receiptIdDigest];
    }

    function isAnchored(bytes32 receiptIdDigest) external view returns (bool) {
        return _anchors[receiptIdDigest].exists;
    }

    function computeRecordHash(
        bytes32 decisionDigest,
        Decision decision,
        bytes32 acpJobReferenceDigest
    ) public pure returns (bytes32) {
        return keccak256(abi.encode(decisionDigest, decision, acpJobReferenceDigest));
    }

    function _checkRuntimeChain() private view {
        if (block.chainid != deployedChainId) {
            revert RuntimeChainIdMismatch(deployedChainId, block.chainid);
        }
    }
}
