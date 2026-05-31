# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json


class AgentSLA(gl.Contract):
    """Autonomous Service Level Agreement Oracle for AI Agents.

    Agents register with capabilities and stake collateral.
    Clients create SLA tasks with specific deliverables, deadlines, and quality thresholds.
    LLM evaluates submitted evidence against SLA terms with multi-step reasoning.
    Graduated penalty system: partial completion gets partial payment.
    Dynamic reputation score affects future task pricing and acceptance.
    """

    owner: Address
    platform_fee_bps: u256
    total_agents: u256
    total_tasks: u256
    total_resolved: u256
    platform_balance: u256
    agents: TreeMap[str, str]
    tasks: TreeMap[str, str]
    disputes: TreeMap[str, str]
    reputation: TreeMap[str, str]
    agent_stats: TreeMap[str, str]
    next_task_id: u256
    next_dispute_id: u256

    def __init__(self):
        self.owner = gl.message.sender_address
        self.platform_fee_bps = u256(500)
        self.total_agents = u256(0)
        self.total_tasks = u256(0)
        self.total_resolved = u256(0)
        self.platform_balance = u256(0)
        self.agents = TreeMap()
        self.tasks = TreeMap()
        self.disputes = TreeMap()
        self.reputation = TreeMap()
        self.agent_stats = TreeMap()
        self.next_task_id = u256(1)
        self.next_dispute_id = u256(1)

    @gl.public.write
    def register_agent(self, name: str, capabilities: str, description: str, api_endpoint: str, portfolio_url: str) -> str:
        agent_key = str(gl.message.sender_address)
        if agent_key in self.agents:
            return json.dumps({"error": "Agent already registered"})
        profile = json.dumps({
            "name": name, "capabilities": capabilities, "description": description,
            "api_endpoint": api_endpoint, "portfolio_url": portfolio_url,
            "is_active": "true", "total_earned": "0", "total_penalized": "0",
        })
        self.agents[agent_key] = profile
        self.reputation[agent_key] = "500"
        self.agent_stats[agent_key] = json.dumps({"completed": "0", "failed": "0"})
        self.total_agents = u256(int(self.total_agents) + 1)
        return json.dumps({"status": "registered", "agent": str(gl.message.sender_address), "initial_reputation": "500"})

    @gl.public.write
    def update_agent_profile(self, name: str, capabilities: str, description: str, api_endpoint: str, portfolio_url: str) -> str:
        agent_key = str(gl.message.sender_address)
        if agent_key not in self.agents:
            return json.dumps({"error": "Agent not registered"})
        profile = json.loads(self.agents[agent_key])
        profile.update({"name": name, "capabilities": capabilities, "description": description, "api_endpoint": api_endpoint, "portfolio_url": portfolio_url})
        self.agents[agent_key] = json.dumps(profile)
        return json.dumps({"status": "updated"})

    @gl.public.write.payable
    def create_sla_task(self, title: str, description: str, deliverables: str, quality_threshold: str, deadline_blocks: str, required_capabilities: str, evidence_urls: str) -> str:
        task_id = self.next_task_id
        task_key = str(task_id)
        task = json.dumps({
            "title": title, "description": description, "deliverables": deliverables,
            "quality_threshold": quality_threshold,
            "deadline_blocks": str(int(self.total_tasks) + int(deadline_blocks)),
            "required_capabilities": required_capabilities, "evidence_urls": evidence_urls,
            "client": str(gl.message.sender_address), "agent": "",
            "stake": str(gl.message.value), "status": "open",
            "created_at": str(self.total_tasks), "accepted_at": "0", "submitted_at": "0",
            "evidence_submitted": "", "evaluation_result": "", "payout_amount": "0", "penalty_amount": "0",
        })
        self.tasks[task_key] = task
        self.next_task_id = u256(int(task_id) + 1)
        self.total_tasks = u256(int(self.total_tasks) + 1)
        return task_key

    @gl.public.write
    def accept_task(self, task_key: str) -> str:
        agent_key = str(gl.message.sender_address)
        if task_key not in self.tasks:
            return json.dumps({"error": "Task not found"})
        task_data = json.loads(self.tasks[task_key])
        if task_data["status"] != "open":
            return json.dumps({"error": "Task not open"})
        if agent_key not in self.agents:
            return json.dumps({"error": "Agent not registered"})
        if int(self.reputation[agent_key]) < 200:
            return json.dumps({"error": "Reputation too low"})
        task_data["agent"] = str(gl.message.sender_address)
        task_data["status"] = "accepted"
        task_data["accepted_at"] = str(self.total_tasks)
        self.tasks[task_key] = json.dumps(task_data)
        return json.dumps({"status": "accepted", "task_key": task_key})

    @gl.public.write
    def submit_evidence(self, task_key: str, evidence_urls: str, summary: str) -> str:
        agent_key = str(gl.message.sender_address)
        if task_key not in self.tasks:
            return json.dumps({"error": "Task not found"})
        task_data = json.loads(self.tasks[task_key])
        if task_data["status"] != "accepted":
            return json.dumps({"error": "Task not in accepted state"})
        if task_data["agent"] != str(gl.message.sender_address):
            return json.dumps({"error": "Not the assigned agent"})
        task_data["status"] = "submitted"
        task_data["submitted_at"] = str(self.total_tasks)
        task_data["evidence_submitted"] = json.dumps({"evidence_urls": evidence_urls, "summary": summary})
        self.tasks[task_key] = json.dumps(task_data)
        return json.dumps({"status": "submitted", "task_key": task_key})

    @gl.public.write
    def evaluate_and_store(self, task_key: str) -> str:
        """LLM evaluates task completion and stores result. Write method for full consensus."""
        if task_key not in self.tasks:
            return json.dumps({"error": "Task not found"})
        task_data = json.loads(self.tasks[task_key])
        if task_data["status"] != "submitted":
            return json.dumps({"error": "No evidence to evaluate"})

        def leader_fn():
            submitted_evidence = ""
            evidence_data = json.loads(task_data["evidence_submitted"])
            for url in json.loads(evidence_data["evidence_urls"]):
                try:
                    resp = gl.nondet.web.get(url.strip())
                    body = resp.body.decode("utf-8")[:4000]
                    submitted_evidence += f"\n--- Deliverable: {url} ---\n{body}"
                except Exception:
                    submitted_evidence += f"\n--- Deliverable: {url} --- [FETCH FAILED]"

            reference_evidence = ""
            if task_data["evidence_urls"]:
                for url in json.loads(task_data["evidence_urls"]):
                    try:
                        resp = gl.nondet.web.get(url.strip())
                        body = resp.body.decode("utf-8")[:2000]
                        reference_evidence += f"\n--- Reference: {url} ---\n{body}"
                    except Exception:
                        pass

            submitted_at = int(task_data["submitted_at"])
            deadline = int(task_data["deadline_blocks"])
            on_time = submitted_at <= deadline

            prompt = f"""You are an impartial SLA evaluator for AI agent contracts.
Evaluate the agent's work against the Service Level Agreement.

## SLA TERMS
Title: {task_data['title']}
Description: {task_data['description']}
Required Deliverables: {task_data['deliverables']}
Quality Threshold: {task_data['quality_threshold']}/100
Required Capabilities: {task_data['required_capabilities']}

## DEADLINE COMPLIANCE
On Time: {on_time}

## SUBMITTED EVIDENCE
{submitted_evidence}

## REFERENCE MATERIAL
{reference_evidence}

## SUBMITTED SUMMARY
{evidence_data['summary']}

Return ONLY valid JSON:
{{
    "quality_score": <0-100>,
    "completeness_score": <0-100>,
    "deadline_met": true or false,
    "deliverables_found": <number>,
    "deliverables_required": <number>,
    "overall_verdict": "excellent" or "acceptable" or "partial" or "failed",
    "payout_percentage": <0-100>,
    "issues": ["issue1"],
    "strengths": ["str1"],
    "reasoning": "detailed explanation"
}}"""
            return gl.nondet.exec_prompt(prompt, response_format="json")

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            my_result = leader_fn()
            leader_data = leader_result.calldata
            return (
                leader_data["overall_verdict"] == my_result["overall_verdict"]
                and abs(leader_data["quality_score"] - my_result["quality_score"]) <= 10
                and abs(leader_data["payout_percentage"] - my_result["payout_percentage"]) <= 15
            )

        result = gl.vm.run_nondet(leader_fn, validator_fn)
        task_data["evaluation_result"] = json.dumps(result)
        self.tasks[task_key] = json.dumps(task_data)
        return json.dumps(result)

    @gl.public.write
    def resolve_task(self, task_key: str, evaluation_json: str) -> str:
        if task_key not in self.tasks:
            return json.dumps({"error": "Task not found"})
        task_data = json.loads(self.tasks[task_key])
        if task_data["status"] != "submitted":
            return json.dumps({"error": "Task not submitted"})
        evaluation = json.loads(evaluation_json)
        stake = int(task_data["stake"])
        agent_key = task_data["agent"]
        verdict = evaluation["overall_verdict"]
        payout_pct = evaluation["payout_percentage"]
        platform_fee = stake * int(self.platform_fee_bps) // 10000
        available = stake - platform_fee
        if verdict == "excellent":
            payout = available; rep_change = 50
        elif verdict == "acceptable":
            payout = available * 95 // 100; rep_change = 20
        elif verdict == "partial":
            payout = available * payout_pct // 100; rep_change = 0
        else:
            payout = available * 30 // 100; rep_change = -100
        penalty = available - payout
        task_data["status"] = "resolved"
        task_data["evaluation_result"] = evaluation_json
        task_data["payout_amount"] = str(payout)
        task_data["penalty_amount"] = str(penalty)
        self.tasks[task_key] = json.dumps(task_data)
        current_rep = int(self.reputation[agent_key])
        new_rep = max(0, min(1000, current_rep + rep_change))
        self.reputation[agent_key] = str(new_rep)
        stats = json.loads(self.agent_stats[agent_key])
        if verdict in ("excellent", "acceptable"):
            stats["completed"] = str(int(stats["completed"]) + 1)
        else:
            stats["failed"] = str(int(stats["failed"]) + 1)
        self.agent_stats[agent_key] = json.dumps(stats)
        self.total_resolved = u256(int(self.total_resolved) + 1)
        self.platform_balance = u256(int(self.platform_balance) + platform_fee)
        return json.dumps({
            "status": "resolved", "verdict": verdict, "payout": str(payout),
            "penalty": str(penalty), "platform_fee": str(platform_fee),
            "new_reputation": str(new_rep), "reputation_change": str(rep_change),
        })

    @gl.public.write.payable
    def raise_dispute(self, task_key: str, reason: str, evidence_urls: str) -> str:
        dispute_id = self.next_dispute_id
        dispute_key = str(dispute_id)
        self.disputes[dispute_key] = json.dumps({
            "task_key": task_key, "challenger": str(gl.message.sender_address),
            "reason": reason, "evidence_urls": evidence_urls,
            "stake": str(gl.message.value), "status": "open", "resolution": "",
        })
        self.next_dispute_id = u256(int(dispute_id) + 1)
        return dispute_key

    @gl.public.write
    def resolve_dispute(self, dispute_key: str) -> str:
        """LLM evaluates dispute. Write method for full consensus."""
        if dispute_key not in self.disputes:
            return json.dumps({"error": "Dispute not found"})
        dispute_data = json.loads(self.disputes[dispute_key])
        task_key = dispute_data["task_key"]
        if task_key not in self.tasks:
            return json.dumps({"error": "Original task not found"})
        task_data = json.loads(self.tasks[task_key])

        def leader_fn():
            dispute_evidence = ""
            for url in json.loads(dispute_data["evidence_urls"]):
                try:
                    resp = gl.nondet.web.get(url.strip())
                    body = resp.body.decode("utf-8")[:3000]
                    dispute_evidence += f"\n--- Dispute Evidence: {url} ---\n{body}"
                except Exception:
                    pass
            original_eval = task_data.get("evaluation_result", "{}")
            prompt = f"""You are an impartial dispute arbitrator for an AI agent SLA system.
## ORIGINAL TASK
Title: {task_data['title']}
Description: {task_data['description']}
Deliverables: {task_data['deliverables']}
## ORIGINAL EVALUATION
{original_eval}
## DISPUTE REASON
{dispute_data['reason']}
## DISPUTE EVIDENCE
{dispute_evidence}
Return ONLY valid JSON:
{{
    "original_was_fair": true or false,
    "dispute_valid": true or false,
    "recommended_adjustment": "none" or "increase_payout" or "decrease_payout" or "full_refund",
    "adjustment_percentage": <0-100>,
    "reasoning": "detailed explanation"
}}"""
            return gl.nondet.exec_prompt(prompt, response_format="json")

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            my_result = leader_fn()
            leader_data = leader_result.calldata
            return (
                leader_data["dispute_valid"] == my_result["dispute_valid"]
                and leader_data["recommended_adjustment"] == my_result["recommended_adjustment"]
            )

        result = gl.vm.run_nondet(leader_fn, validator_fn)
        dispute_data["resolution"] = json.dumps(result)
        dispute_data["status"] = "resolved"
        self.disputes[dispute_key] = json.dumps(dispute_data)
        return json.dumps(result)

    @gl.public.view
    def get_agent_profile(self, agent_addr: str) -> str:
        if agent_addr not in self.agents:
            return json.dumps({"error": "Agent not found"})
        profile = json.loads(self.agents[agent_addr])
        profile["reputation"] = self.reputation[agent_addr]
        stats = json.loads(self.agent_stats[agent_addr])
        profile["tasks_completed"] = stats["completed"]
        profile["tasks_failed"] = stats["failed"]
        return json.dumps(profile)

    @gl.public.view
    def get_task(self, task_key: str) -> str:
        if task_key not in self.tasks:
            return json.dumps({"error": "Task not found"})
        return self.tasks[task_key]

    @gl.public.view
    def get_platform_stats(self) -> str:
        return json.dumps({
            "total_agents": str(self.total_agents), "total_tasks": str(self.total_tasks),
            "total_resolved": str(self.total_resolved), "platform_fee_bps": str(self.platform_fee_bps),
            "platform_balance": str(self.platform_balance),
        })

    @gl.public.view
    def get_dispute(self, dispute_key: str) -> str:
        if dispute_key not in self.disputes:
            return json.dumps({"error": "Dispute not found"})
        return self.disputes[dispute_key]

    @gl.public.view
    def get_open_tasks(self) -> str:
        open_tasks = []
        for i in range(1, int(self.next_task_id)):
            key = str(i)
            if key in self.tasks:
                task = json.loads(self.tasks[key])
                if task["status"] == "open":
                    open_tasks.append({"task_key": key, "title": task["title"], "stake": task["stake"], "required_capabilities": task["required_capabilities"]})
        return json.dumps({"open_tasks": open_tasks})

    @gl.public.write
    def set_platform_fee(self, new_fee_bps: u256) -> str:
        if gl.message.sender_address != self.owner:
            return json.dumps({"error": "Not owner"})
        if int(new_fee_bps) > 1000:
            return json.dumps({"error": "Fee too high (max 10%)"})
        self.platform_fee_bps = new_fee_bps
        return json.dumps({"status": "updated", "new_fee_bps": str(new_fee_bps)})

    @gl.public.write
    def withdraw_platform_fees(self) -> str:
        if gl.message.sender_address != self.owner:
            return json.dumps({"error": "Not owner"})
        amount = int(self.platform_balance)
        if amount == 0:
            return json.dumps({"error": "No fees to withdraw"})
        self.platform_balance = u256(0)
        return json.dumps({"status": "withdrawn", "amount": str(amount)})
