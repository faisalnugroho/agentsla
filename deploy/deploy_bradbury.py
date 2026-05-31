#!/usr/bin/env python3
"""Deploy AgentSLA to Bradbury testnet."""
import json
import time
from pathlib import Path
from eth_account import Account
from genlayer_py import create_client

from genlayer_py import testnet_bradbury as bradbury

code = Path("contracts/agent_sla.py").read_text()
account = Account.create()
pk = account.key
client = create_client(chain=bradbury, account=pk)
client.local_account = account

print(f"Deployer: {account.address}")
print(f"Network: Bradbury Testnet (chain 4221)")

# Fund account (Bradbury faucet)
print("Funding account from faucet...")
try:
    client.fund_account(account.address, 10**18)
    print("Funded 1 GEN")
except Exception as e:
    print(f"Fund result: {e}")

# Deploy
print("Deploying AgentSLA contract...")
try:
    tx = client.deploy_contract(code=code, account=account, leader_only=True)
    print(f"TX Hash: {tx}")
    
    receipt = client.wait_for_transaction_receipt(tx, retries=30, interval=5000)
    print(f"Status: {receipt.get('status_name', 'unknown')}")
    
    addr = receipt.get('data', {}).get('contract_address')
    if addr:
        print(f"Contract deployed at: {addr}")
        
        # Check for errors
        for lr in receipt.get('consensus_data', {}).get('leader_receipt', []):
            g = lr.get('genvm_result', {})
            if g.get('stderr'):
                print(f"STDERR: {g['stderr']}")
        
        # Test
        print("\nTesting get_platform_stats...")
        result = client.read_contract(address=addr, function_name="get_platform_stats")
        print(f"Platform stats: {result}")
        
        # Save
        deploy_info = {
            "contract_address": addr,
            "deployer": account.address,
            "private_key": pk.hex(),
            "network": "bradbury",
            "chain_id": 4221,
            "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        Path("deploy/bradbury_deploy.json").write_text(json.dumps(deploy_info, indent=2))
        print(f"\nDeployment saved to deploy/bradbury_deploy.json")
        print(f"\n=== BRADBURY DEPLOYMENT SUCCESSFUL ===")
        print(f"Contract: {addr}")
        print(f"Explorer: https://genlayer-explorer.vercel.app/address/{addr}")
    else:
        print(f"No contract address. Receipt: {json.dumps(receipt, indent=2, default=str)[:1000]}")
except Exception as e:
    print(f"Deploy failed: {e}")
    import traceback
    traceback.print_exc()
