#!/usr/bin/env python3
"""Deploy AgentSLA to GenLayer Studionet."""
import json
import sys
import time
from pathlib import Path
from eth_account import Account
from genlayer_py import studionet, create_client

# Setup
code = Path("contracts/agent_sla.py").read_text()
account = Account.create()
pk = account.key
client = create_client(chain=studionet, account=pk)
client.local_account = account

print(f"Deployer: {account.address}")
print(f"Network: Studionet (chain {studionet.id})")

# Fund account
print("Funding account...")
try:
    client.fund_account(account.address, 10**18)
    print("Funded 1 GEN")
except Exception as e:
    print(f"Fund failed (may already be funded): {e}")

# Deploy
print("Deploying AgentSLA contract...")
try:
    tx = client.deploy_contract(code=code, account=account, leader_only=True)
    print(f"TX Hash: {tx}")
    
    receipt = client.wait_for_transaction_receipt(tx)
    print(f"Status: {receipt.get('status_name', 'unknown')}")
    
    # Get contract address
    addr = receipt.get('data', {}).get('contract_address')
    if addr:
        print(f"Contract deployed at: {addr}")
        
        # Check for errors
        for lr in receipt.get('consensus_data', {}).get('leader_receipt', []):
            g = lr.get('genvm_result', {})
            if g.get('stderr'):
                print(f"STDERR: {g['stderr']}")
            if lr.get('execution_result') == 'ERROR':
                print(f"ERROR: {lr.get('result', {}).get('payload')}")
        
        # Test: read platform stats
        print("\nTesting get_platform_stats...")
        result = client.read_contract(
            address=addr,
            function_name="get_platform_stats"
        )
        print(f"Platform stats: {result}")
        
        # Save deployment info
        deploy_info = {
            "contract_address": addr,
            "deployer": account.address,
            "private_key": pk.hex(),
            "network": "studionet",
            "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        Path("deploy/studionet_deploy.json").write_text(json.dumps(deploy_info, indent=2))
        print(f"\nDeployment info saved to deploy/studionet_deploy.json")
    else:
        print(f"No contract address in receipt")
        print(f"Full receipt: {json.dumps(receipt, indent=2, default=str)}")
        
except Exception as e:
    print(f"Deploy failed: {e}")
    import traceback
    traceback.print_exc()
