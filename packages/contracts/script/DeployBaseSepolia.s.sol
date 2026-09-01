// SPDX-License-Identifier: MIT
pragma solidity 0.8.36;

import { RecallOpsReceiptRegistry } from "../src/RecallOpsReceiptRegistry.sol";

interface VmBaseDeploy {
    function envAddress(string calldata name) external view returns (address);
    function startBroadcast() external;
    function stopBroadcast() external;
}

contract DeployBaseSepolia {
    VmBaseDeploy private constant vm =
        VmBaseDeploy(address(uint160(uint256(keccak256("hevm cheat code")))));

    function run() external returns (RecallOpsReceiptRegistry registry) {
        require(block.chainid == 84_532, "BASE_SEPOLIA_ONLY");
        address submitter = vm.envAddress("RECALLOPS_RECEIPT_SUBMITTER");
        require(submitter != address(0), "SUBMITTER_REQUIRED");
        vm.startBroadcast();
        registry = new RecallOpsReceiptRegistry(submitter, 84_532);
        vm.stopBroadcast();
    }
}
