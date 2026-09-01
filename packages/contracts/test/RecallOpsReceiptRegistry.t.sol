// SPDX-License-Identifier: MIT
pragma solidity 0.8.36;

import { RecallOpsReceiptRegistry } from "../src/RecallOpsReceiptRegistry.sol";

interface Vm {
    function assume(bool condition) external;
    function chainId(uint256 newChainId) external;
    function expectEmit(bool, bool, bool, bool, address emitter) external;
    function expectRevert(bytes calldata revertData) external;
    function expectRevert(bytes4 selector) external;
    function prank(address caller) external;
    function warp(uint256 timestamp) external;
}

contract RecallOpsReceiptRegistryTest {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    address private constant SUBMITTER = address(0xA11CE);
    address private constant STRANGER = address(0xB0B);
    bytes32 private constant RECEIPT_ID_DIGEST = keccak256("receipt-id");
    bytes32 private constant DECISION_DIGEST = keccak256("decision");
    bytes32 private constant ACP_JOB_DIGEST = keccak256("acp-job");

    RecallOpsReceiptRegistry private registry;

    event ReceiptAnchored(
        bytes32 indexed receiptIdDigest,
        bytes32 indexed decisionDigest,
        RecallOpsReceiptRegistry.Decision decision,
        address indexed actor,
        uint64 anchoredAt,
        bytes32 acpJobReferenceDigest
    );

    function setUp() public {
        vm.chainId(31_337);
        registry = new RecallOpsReceiptRegistry(SUBMITTER, 31_337);
    }

    function testAnchorStoresOnlyDigestsAndEmitsAuditEvent() public {
        vm.warp(1_788_220_800);
        vm.expectEmit(true, true, true, true, address(registry));
        emit ReceiptAnchored(
            RECEIPT_ID_DIGEST,
            DECISION_DIGEST,
            RecallOpsReceiptRegistry.Decision.APPROVE,
            SUBMITTER,
            uint64(block.timestamp),
            ACP_JOB_DIGEST
        );

        vm.prank(SUBMITTER);
        bool created = registry.anchorReceipt(
            RECEIPT_ID_DIGEST,
            DECISION_DIGEST,
            RecallOpsReceiptRegistry.Decision.APPROVE,
            ACP_JOB_DIGEST
        );

        RecallOpsReceiptRegistry.Anchor memory anchor = registry.getAnchor(RECEIPT_ID_DIGEST);
        bytes32 expectedHash = registry.computeRecordHash(
            DECISION_DIGEST, RecallOpsReceiptRegistry.Decision.APPROVE, ACP_JOB_DIGEST
        );
        _assertTrue(created);
        _assertTrue(anchor.exists);
        _assertEq(anchor.recordHash, expectedHash);
        _assertEq(uint256(anchor.anchoredAt), block.timestamp);
        _assertEq(uint256(anchor.decision), 0);
        _assertEq(registry.anchorCount(), 1);
    }

    function testExactReplayIsIdempotentAndDoesNotIncrementCount() public {
        vm.prank(SUBMITTER);
        _assertTrue(
            registry.anchorReceipt(
                RECEIPT_ID_DIGEST,
                DECISION_DIGEST,
                RecallOpsReceiptRegistry.Decision.DENY,
                bytes32(0)
            )
        );

        vm.prank(SUBMITTER);
        bool created = registry.anchorReceipt(
            RECEIPT_ID_DIGEST, DECISION_DIGEST, RecallOpsReceiptRegistry.Decision.DENY, bytes32(0)
        );

        _assertFalse(created);
        _assertEq(registry.anchorCount(), 1);
    }

    function testConflictingReplayReverts() public {
        vm.prank(SUBMITTER);
        registry.anchorReceipt(
            RECEIPT_ID_DIGEST,
            DECISION_DIGEST,
            RecallOpsReceiptRegistry.Decision.APPROVE,
            ACP_JOB_DIGEST
        );
        bytes32 existingHash = registry.computeRecordHash(
            DECISION_DIGEST, RecallOpsReceiptRegistry.Decision.APPROVE, ACP_JOB_DIGEST
        );
        bytes32 conflictingDigest = keccak256("conflict");
        bytes32 newHash = registry.computeRecordHash(
            conflictingDigest, RecallOpsReceiptRegistry.Decision.APPROVE, ACP_JOB_DIGEST
        );

        vm.expectRevert(
            abi.encodeWithSelector(
                RecallOpsReceiptRegistry.ReceiptConflict.selector,
                RECEIPT_ID_DIGEST,
                existingHash,
                newHash
            )
        );
        vm.prank(SUBMITTER);
        registry.anchorReceipt(
            RECEIPT_ID_DIGEST,
            conflictingDigest,
            RecallOpsReceiptRegistry.Decision.APPROVE,
            ACP_JOB_DIGEST
        );
    }

    function testUnauthorizedCallerReverts() public {
        vm.expectRevert(
            abi.encodeWithSelector(
                RecallOpsReceiptRegistry.UnauthorizedSubmitter.selector, STRANGER
            )
        );
        vm.prank(STRANGER);
        registry.anchorReceipt(
            RECEIPT_ID_DIGEST,
            DECISION_DIGEST,
            RecallOpsReceiptRegistry.Decision.APPROVE,
            bytes32(0)
        );
    }

    function testZeroDigestsRevert() public {
        vm.expectRevert(RecallOpsReceiptRegistry.ZeroReceiptIdDigest.selector);
        vm.prank(SUBMITTER);
        registry.anchorReceipt(
            bytes32(0), DECISION_DIGEST, RecallOpsReceiptRegistry.Decision.ESCALATE, bytes32(0)
        );

        vm.expectRevert(RecallOpsReceiptRegistry.ZeroDecisionDigest.selector);
        vm.prank(SUBMITTER);
        registry.anchorReceipt(
            RECEIPT_ID_DIGEST, bytes32(0), RecallOpsReceiptRegistry.Decision.ESCALATE, bytes32(0)
        );
    }

    function testConstructorRejectsZeroSubmitter() public {
        vm.expectRevert(RecallOpsReceiptRegistry.ZeroAddress.selector);
        new RecallOpsReceiptRegistry(address(0), 31_337);
    }

    function testConstructorRejectsUnsupportedChain() public {
        vm.chainId(1);
        vm.expectRevert(
            abi.encodeWithSelector(RecallOpsReceiptRegistry.UnsupportedChain.selector, 1)
        );
        new RecallOpsReceiptRegistry(SUBMITTER, 1);
    }

    function testConstructorRejectsChainMismatch() public {
        vm.chainId(84_532);
        vm.expectRevert(
            abi.encodeWithSelector(
                RecallOpsReceiptRegistry.DeploymentChainIdMismatch.selector, 31_337, 84_532
            )
        );
        new RecallOpsReceiptRegistry(SUBMITTER, 31_337);
    }

    function testBaseSepoliaIsAllowlisted() public {
        vm.chainId(84_532);
        RecallOpsReceiptRegistry baseRegistry = new RecallOpsReceiptRegistry(SUBMITTER, 84_532);
        _assertEq(baseRegistry.deployedChainId(), 84_532);
    }

    function testRuntimeChainChangeReverts() public {
        vm.chainId(84_532);
        vm.expectRevert(
            abi.encodeWithSelector(
                RecallOpsReceiptRegistry.RuntimeChainIdMismatch.selector, 31_337, 84_532
            )
        );
        vm.prank(SUBMITTER);
        registry.anchorReceipt(
            RECEIPT_ID_DIGEST,
            DECISION_DIGEST,
            RecallOpsReceiptRegistry.Decision.APPROVE,
            bytes32(0)
        );
    }

    function testInvalidDecisionEncodingReverts() public {
        bytes memory callData = abi.encodeWithSelector(
            registry.anchorReceipt.selector,
            RECEIPT_ID_DIGEST,
            DECISION_DIGEST,
            uint8(3),
            bytes32(0)
        );
        vm.prank(SUBMITTER);
        (bool success,) = address(registry).call(callData);
        _assertFalse(success);
    }

    function testFuzzReceiptUniqueness(
        bytes32 receiptIdDigest,
        bytes32 decisionDigest,
        bytes32 acpJobDigest,
        uint8 decisionValue
    ) public {
        if (receiptIdDigest == bytes32(0)) {
            receiptIdDigest = bytes32(uint256(1));
        }
        if (decisionDigest == bytes32(0)) decisionDigest = bytes32(uint256(1));
        RecallOpsReceiptRegistry.Decision decision =
            RecallOpsReceiptRegistry.Decision(decisionValue % 3);

        vm.prank(SUBMITTER);
        _assertTrue(registry.anchorReceipt(receiptIdDigest, decisionDigest, decision, acpJobDigest));
        vm.prank(SUBMITTER);
        _assertFalse(
            registry.anchorReceipt(receiptIdDigest, decisionDigest, decision, acpJobDigest)
        );
        _assertTrue(registry.isAnchored(receiptIdDigest));
        _assertEq(registry.anchorCount(), 1);
    }

    function testFuzzUnauthorizedCallers(address caller) public {
        vm.assume(caller != SUBMITTER && caller != address(0));
        vm.expectRevert(
            abi.encodeWithSelector(RecallOpsReceiptRegistry.UnauthorizedSubmitter.selector, caller)
        );
        vm.prank(caller);
        registry.anchorReceipt(
            RECEIPT_ID_DIGEST,
            DECISION_DIGEST,
            RecallOpsReceiptRegistry.Decision.APPROVE,
            bytes32(0)
        );
    }

    function _assertTrue(bool value) private pure {
        require(value, "assert true failed");
    }

    function _assertFalse(bool value) private pure {
        require(!value, "assert false failed");
    }

    function _assertEq(bytes32 left, bytes32 right) private pure {
        require(left == right, "bytes32 equality failed");
    }

    function _assertEq(uint256 left, uint256 right) private pure {
        require(left == right, "uint256 equality failed");
    }
}
