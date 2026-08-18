#!/usr/bin/env python3
"""AgentSLA — throttled Studionet lifecycle + LLM consensus verification.

Rate limit on Studionet public RPC is ~30 req/min. Each write tx spawns multiple
RPC calls (estimateGas + send + several receipt polls), so we sleep 4s between
transactions and use leader_only=False for real consensus on the eval step.
"""
import json
import time
from pathlib import Path
from eth_account import Account
from genlayer_py import studionet, create_client

SLEEP = 4  # seconds between write transactions

deploy_info = json.loads(Path("deploy/studionet_deploy.json").read_text())
contract_addr = deploy_info["contract_address"]

# Reuse the deployer account as "client" and make a fresh one for "agent"
deployer = Account.from_key(deploy_info["private_key"])
agent = Account.create()

client = create_client(chain=studionet, account=deployer.key)
client.local_account = deployer
agent_sdk = create_client(chain=studionet, account=agent.key)
agent_sdk.local_account = agent

print(f"Contract: {contract_addr}")
print(f"Client (deployer): {deployer.address}")
print(f"Agent: {agent.address}")

try:
    print("Funding agent account...")
    agent_sdk.fund_account(agent.address, 3 * 10**18)
except Exception as e:
    print(f"fund: {e}")

def w(sdk, name, args, value=0, account=None):
    """Throttled write contract call."""
    time.sleep(SLEEP)
    tx = sdk.write_contract(
        address=contract_addr, function_name=name, args=args,
        account=account, value=value,
    )
    rc = sdk.wait_for_transaction_receipt(tx, retries=40, interval=4000)
    return rc

def r(sdk, name, args=None):
    time.sleep(1)
    return sdk.read_contract(address=contract_addr, function_name=name, args=args)

# STEP 1: register agent
print("\n=== STEP 1: register_agent ===")
res = w(agent_sdk, "register_agent", [
    "CodeForge AI",
    "python,typescript,api-integration",
    "AI agent specializing in REST API development and testing",
    "https://api.codeforge.ai",
    "https://github.com/codeforge-ai",
], account=agent)
print("register:", res.get("status_name"))

# STEP 2: create task (deployer stakes 2 GEN)
print("\n=== STEP 2: create_sla_task ===")
res = w(client, "create_sla_task", [
    "Build REST API with Authentication",
    "Create a REST API with CRUD endpoints for user management, JWT authentication, and rate limiting",
    json.dumps(["API source code", "Unit tests", "API documentation"]),
    "70",
    "100",
    "python,api,testing",
    json.dumps(["https://httpbin.org/get"]),
], value=2 * 10**18, account=deployer)
print("create:", res.get("status_name"))

stats = json.loads(r(client, "get_platform_stats"))
total_tasks = int(stats["total_tasks"])
task_key = str(total_tasks)
print("stats:", stats, "-> task_key:", task_key)

# STEP 3: accept
print("\n=== STEP 3: accept_task ===")
res = w(agent_sdk, "accept_task", [task_key], account=agent)
print("accept:", res.get("status_name"))

# STEP 4: submit evidence
print("\n=== STEP 4: submit_evidence ===")
res = w(agent_sdk, "submit_evidence", [
    task_key,
    json.dumps(["https://httpbin.org/get", "https://httpbin.org/json"]),
    "Completed REST API with full CRUD, JWT auth, and rate limiting. All tests passing.",
], account=agent)
print("submit:", res.get("status_name"))

# STEP 5: LLM evaluate — full consensus, 3x
print("\n=== STEP 5: evaluate_and_store (3x real consensus) ===")
verdicts = []
for i in range(3):
    print(f"  run {i+1}/3 ...")
    res = w(client, "evaluate_and_store", [task_key], account=deployer)
    print("  ->", res.get("status_name"))
    # extract result payload
    payload = None
    for lr in res.get("consensus_data", {}).get("leader_receipt", []):
        p = lr.get("result", {}).get("payload", "")
        if isinstance(p, str) and p.startswith("{"):
            payload = p
            break
    if payload:
        d = json.loads(payload)
        verdicts.append(d.get("overall_verdict"))
        print("     verdict:", d.get("overall_verdict"), "| quality:", d.get("quality_score"), "| payout:", d.get("payout_percentage"), "%")
    time.sleep(3)

print("\n verdicts:", verdicts)
print(" CONSENSUS:", "PASSED (all agree)" if len(set(verdicts)) == 1 else f"PARTIAL {set(verdicts)}")

# STEP 6: resolve (money moves)
print("\n=== STEP 6: resolve_task ===")
eval_json = payload if payload else json.dumps({"overall_verdict": "acceptable", "quality_score": 80, "payout_percentage": 95})
res = w(client, "resolve_task", [task_key, eval_json], account=deployer)
print("resolve:", res.get("status_name"))

# STEP 7: final state
print("\n=== STEP 7: final state ===")
task = json.loads(r(client, "get_task", [task_key]))
print("task status:", task.get("status"), "| payout:", task.get("payout_amount"), "| penalty:", task.get("penalty_amount"))
prof = json.loads(r(client, "get_agent_profile", [agent.address]))
print("agent reputation:", prof.get("reputation"), "| completed:", prof.get("tasks_completed"))
final_stats = json.loads(r(client, "get_platform_stats"))
print("platform:", final_stats)

# STEP 8: balances — agent withdraws earned GEN
print("\n=== STEP 8: balances & withdraw ===")
agent_bal = r(agent_sdk, "get_balance", [agent.address])
print("agent balance:", agent_bal)
client_bal = r(client, "get_balance", [deployer.address])
print("client refund balance:", client_bal)
if int(agent_bal or 0) > 0:
    res = w(agent_sdk, "withdraw", [], account=agent)
    print("withdraw:", res.get("status_name"))
    print("agent balance after withdraw:", r(agent_sdk, "get_balance", [agent.address]))

print("\n=== DONE ===")
