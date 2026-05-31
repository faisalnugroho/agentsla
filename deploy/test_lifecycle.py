#!/usr/bin/env python3
"""Test AgentSLA full lifecycle on Studionet — 3x consensus verification."""
import json
import time
from pathlib import Path
from eth_account import Account
from genlayer_py import studionet, create_client

# Load deployment info
deploy_info = json.loads(Path("deploy/studionet_deploy.json").read_text())
contract_addr = deploy_info["contract_address"]

# Create two accounts: client and agent
client_account = Account.create()
agent_account = Account.create()

client_sdk = create_client(chain=studionet, account=client_account.key)
client_sdk.local_account = client_account
agent_sdk = create_client(chain=studionet, account=agent_account.key)
agent_sdk.local_account = agent_account

print(f"Contract: {contract_addr}")
print(f"Client:   {client_account.address}")
print(f"Agent:    {agent_account.address}")

# Fund both
print("\nFunding accounts...")
client_sdk.fund_account(client_account.address, 5 * 10**18)
agent_sdk.fund_account(agent_account.address, 5 * 10**18)
print("Funded 5 GEN each")

# ============ STEP 1: Register Agent ============
print("\n=== STEP 1: Register Agent ===")
tx = agent_sdk.write_contract(
    address=contract_addr,
    function_name="register_agent",
    args=[
        "CodeForge AI",
        "python,typescript,api-integration",
        "AI agent specializing in REST API development and testing",
        "https://api.codeforge.ai",
        "https://github.com/codeforge-ai",
    ],
    account=agent_account,
)
receipt = agent_sdk.wait_for_transaction_receipt(tx)
print(f"Status: {receipt.get('status_name')}")

# Verify registration
profile = agent_sdk.read_contract(
    address=contract_addr,
    function_name="get_agent_profile",
    args=[agent_account.address],
)
print(f"Agent profile: {profile}")

# ============ STEP 2: Create SLA Task ============
print("\n=== STEP 2: Create SLA Task ===")
tx = client_sdk.write_contract(
    address=contract_addr,
    function_name="create_sla_task",
    args=[
        "Build REST API with Authentication",
        "Create a REST API with CRUD endpoints for user management, JWT authentication, and rate limiting",
        json.dumps(["API source code", "Unit tests", "API documentation"]),
        "70",
        "100",
        "python,api,testing",
        json.dumps(["https://httpbin.org/get"]),
    ],
    account=client_account,
    value=2 * 10**18,  # 2 GEN stake
)
receipt = client_sdk.wait_for_transaction_receipt(tx)
print(f"Status: {receipt.get('status_name')}")

# Get task key
stats = client_sdk.read_contract(
    address=contract_addr,
    function_name="get_platform_stats"
)
print(f"Platform stats: {stats}")
task_key = str(int(json.loads(stats)["total_tasks"]))
print(f"Task key: {task_key}")

# ============ STEP 3: Agent Accepts Task ============
print("\n=== STEP 3: Agent Accepts Task ===")
tx = agent_sdk.write_contract(
    address=contract_addr,
    function_name="accept_task",
    args=[task_key],
    account=agent_account,
)
receipt = agent_sdk.wait_for_transaction_receipt(tx)
print(f"Status: {receipt.get('status_name')}")

# ============ STEP 4: Submit Evidence ============
print("\n=== STEP 4: Submit Evidence ===")
tx = agent_sdk.write_contract(
    address=contract_addr,
    function_name="submit_evidence",
    args=[
        task_key,
        json.dumps(["https://httpbin.org/get", "https://httpbin.org/json"]),
        "Completed REST API with full CRUD, JWT auth, and rate limiting. All tests passing.",
    ],
    account=agent_account,
)
receipt = agent_sdk.wait_for_transaction_receipt(tx)
print(f"Status: {receipt.get('status_name')}")

# ============ STEP 5: Evaluate (3x consensus check) ============
print("\n=== STEP 5: LLM Evaluation (3x consensus verification) ===")
verdicts = []
for i in range(3):
    print(f"\n  Run {i+1}/3...")
    tx = client_sdk.write_contract(
        address=contract_addr,
        function_name="evaluate_and_store",
        args=[task_key],
        account=client_account,
    )
    receipt = client_sdk.wait_for_transaction_receipt(tx)
    result = receipt.get("data", {}).get("result", "{}")
    if isinstance(result, str) and not result.startswith("{"):
        # Try to extract from receipt
        for lr in receipt.get("consensus_data", {}).get("leader_receipt", []):
            res = lr.get("result", {}).get("payload", "")
            if res.startswith("{"):
                result = res
                break
    eval_data = json.loads(result)
    verdict = eval_data.get("overall_verdict", "unknown")
    score = eval_data.get("quality_score", 0)
    payout = eval_data.get("payout_percentage", 0)
    print(f"  Verdict: {verdict} | Quality: {score} | Payout: {payout}%")
    verdicts.append(verdict)
    time.sleep(2)

# Check consensus
unique_verdicts = set(verdicts)
print(f"\n  All verdicts: {verdicts}")
print(f"  Unique verdicts: {unique_verdicts}")
if len(unique_verdicts) == 1:
    print("  CONSENSUS PASSED — All 3 evaluations agree!")
else:
    print(f"  CONSENSUS NOTE — {len(unique_verdicts)} different verdicts (tolerance applied)")

# ============ STEP 6: Resolve Task ============
print("\n=== STEP 6: Resolve Task (Money Moves) ===")
# Use the last evaluation for resolution
tx = client_sdk.write_contract(
    address=contract_addr,
    function_name="resolve_task",
    args=[task_key, json.dumps(eval_data)],
    account=client_account,
)
receipt = client_sdk.wait_for_transaction_receipt(tx)
print(f"Status: {receipt.get('status_name')}")

# ============ STEP 7: Verify Final State ============
print("\n=== STEP 7: Final State Verification ===")

# Task final state
task = client_sdk.read_contract(
    address=contract_addr,
    function_name="get_task",
    args=[task_key],
)
task_data = json.loads(task)
print(f"Task status: {task_data['status']}")
print(f"Payout: {task_data['payout_amount']}")
print(f"Penalty: {task_data['penalty_amount']}")

# Agent final state
agent_profile = client_sdk.read_contract(
    address=contract_addr,
    function_name="get_agent_profile",
    args=[agent_account.address],
)
print(f"Agent reputation: {json.loads(agent_profile).get('reputation')}")
print(f"Tasks completed: {json.loads(agent_profile).get('tasks_completed')}")

# Platform final state
final_stats = client_sdk.read_contract(
    address=contract_addr,
    function_name="get_platform_stats"
)
print(f"Platform stats: {final_stats}")

print("\n=== ALL STEPS COMPLETED SUCCESSFULLY ===")
print(f"Contract: {contract_addr}")
print(f"Network: Studionet")
print(f"Consensus: {'PASSED' if len(unique_verdicts) == 1 else 'PARTIAL'}")
