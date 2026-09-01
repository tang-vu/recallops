// SPDX-License-Identifier: MIT
pragma solidity 0.8.36;

import { RecallOpsReceiptRegistry } from "../src/RecallOpsReceiptRegistry.sol";

interface VmLocalDeploy {
    function envOr(string calldata name, address defaultValue) external view returns (address);
    function startBroadcast() external;
    function stopBroadcast() external;
}

contract DeployLocal {
    VmLocalDeploy private constant vm =
        VmLocalDeploy(address(uint160(uint256(keccak256("hevm cheat code")))));

    function run() external returns (RecallOpsReceiptRegistry registry) {
        require(block.chainid == 31_337, "LOCAL_ANVIL_ONLY");
        address submitter = vm.envOr("RECALLOPS_RECEIPT_SUBMITTER", address(0xA11CE));
        vm.startBroadcast();
        registry = new RecallOpsReceiptRegistry(submitter, 31_337);
        vm.stopBroadcast();
    }
}
