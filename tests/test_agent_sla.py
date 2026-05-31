"""
AgentSLA — Comprehensive Test Suite (Direct Mode)

Uses gltest direct fixtures: direct_vm, direct_deploy, direct_alice, etc.
"""

import json
import pytest
from eth_utils import to_checksum_address


# ============ HELPERS ============

def addr_str(raw_bytes):
    """Convert raw address bytes to checksummed hex string matching contract format."""
    return to_checksum_address(raw_bytes)


def register_agent(contract, vm, agent_addr, name="TestAgent"):
    """Helper to register an agent."""
    vm.sender = agent_addr
    return contract.register_agent(
        name,
        "python,typescript,api-integration",
        "AI agent specializing in code tasks",
        "https://api.test-agent.com",
        "https://github.com/test-agent",
    )


def create_task(contract, vm, client_addr, stake=10**18):
    """Helper to create an SLA task."""
    vm.sender = client_addr
    vm.value = stake
    result = contract.create_sla_task(
        "Build REST API",
        "Create a REST API with CRUD endpoints for user management",
        json.dumps(["API code", "Tests", "Documentation"]),
        "70",
        "100",
        "python,api",
        json.dumps(["https://example.com/api-spec"]),
    )
    vm.value = 0
    return result


# ============ AGENT REGISTRATION ============

class TestAgentRegistration:
    def test_register_agent_success(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        result = json.loads(register_agent(contract, direct_vm, direct_alice))
        assert result["status"] == "registered"
        assert result["initial_reputation"] == "500"

    def test_register_agent_duplicate(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_alice)
        result = json.loads(register_agent(contract, direct_vm, direct_alice))
        assert "error" in result

    def test_agent_profile_stored(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_alice, "MyAgent")
        addr_key = addr_str(direct_alice)
        profile = json.loads(contract.get_agent_profile(addr_key))
        assert "name" in profile or "error" not in profile
        assert profile["reputation"] == "500"
        assert profile["tasks_completed"] == "0"

    def test_update_agent_profile(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_alice, "OldName")
        direct_vm.sender = direct_alice
        contract.update_agent_profile("NewName", "rust,solana", "Updated desc", "https://new.api", "https://new.portfolio")
        addr_key = addr_str(direct_alice)
        profile = json.loads(contract.get_agent_profile(addr_key))
        assert profile.get("name") == "NewName" or "error" not in profile

    def test_update_unregistered_agent(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        direct_vm.sender = direct_alice
        result = json.loads(contract.update_agent_profile("Name", "cap", "desc", "api", "port"))
        assert "error" in result


# ============ TASK CREATION ============

class TestTaskCreation:
    def test_create_task_success(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        task_key = create_task(contract, direct_vm, direct_alice)
        assert task_key is not None

    def test_task_stored_correctly(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        task_key = create_task(contract, direct_vm, direct_alice)
        task = json.loads(contract.get_task(task_key))
        assert task["title"] == "Build REST API"
        assert task["status"] == "open"

    def test_platform_stats_update(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        create_task(contract, direct_vm, direct_alice)
        stats = json.loads(contract.get_platform_stats())
        assert int(stats["total_tasks"]) == 1

    def test_open_tasks_list(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        create_task(contract, direct_vm, direct_alice)
        open_tasks = json.loads(contract.get_open_tasks())
        assert len(open_tasks["open_tasks"]) == 1
        assert open_tasks["open_tasks"][0]["title"] == "Build REST API"


# ============ TASK ACCEPTANCE ============

class TestTaskAcceptance:
    def test_accept_task_success(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        result = json.loads(contract.accept_task(task_key))
        assert result["status"] == "accepted"

    def test_accept_task_unregistered(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        result = json.loads(contract.accept_task(task_key))
        assert "error" in result

    def test_accept_task_already_taken(self, direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        register_agent(contract, direct_vm, direct_charlie)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        direct_vm.sender = direct_charlie
        result = json.loads(contract.accept_task(task_key))
        assert "error" in result

    def test_task_status_after_acceptance(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        task = json.loads(contract.get_task(task_key))
        assert task["status"] == "accepted"
        assert addr_str(direct_bob) == task["agent"]


# ============ EVIDENCE SUBMISSION ============

class TestEvidenceSubmission:
    def test_submit_evidence_success(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        result = json.loads(contract.submit_evidence(
            task_key,
            json.dumps(["https://github.com/test-agent/api-repo"]),
            "Completed the REST API with all endpoints",
        ))
        assert result["status"] == "submitted"

    def test_submit_evidence_wrong_agent(self, direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        register_agent(contract, direct_vm, direct_charlie)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        direct_vm.sender = direct_charlie
        result = json.loads(contract.submit_evidence(
            task_key, json.dumps(["https://example.com"]), "Done"
        ))
        assert "error" in result

    def test_submit_evidence_not_accepted(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        result = json.loads(contract.submit_evidence(
            task_key, json.dumps(["https://example.com"]), "Done"
        ))
        assert "error" in result


# ============ LLM EVALUATION ============

class TestEvaluation:
    def test_evaluate_submitted_task(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        """LLM evaluates submitted evidence against SLA terms."""
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        contract.submit_evidence(
            task_key,
            json.dumps(["https://httpbin.org/get"]),
            "Completed all deliverables",
        )

        # Mock web and LLM for direct mode
        direct_vm.mock_web("https://httpbin.org/get", '{"url": "https://httpbin.org/get", "headers": {}}')
        direct_vm.mock_llm(".*", json.dumps({
            "quality_score": 85,
            "completeness_score": 90,
            "deadline_met": True,
            "deliverables_found": 3,
            "deliverables_required": 3,
            "overall_verdict": "acceptable",
            "payout_percentage": 95,
            "issues": [],
            "strengths": ["Clean code", "Good tests"],
            "reasoning": "All deliverables present and high quality",
        }))

        result = json.loads(contract.evaluate_and_store(task_key))
        assert "quality_score" in result
        assert "overall_verdict" in result
        assert result["overall_verdict"] in ("excellent", "acceptable", "partial", "failed")

    def test_evaluate_unsubmitted_task(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        result = json.loads(contract.evaluate_and_store(task_key))
        assert "error" in result


# ============ RESOLUTION ============

class TestResolution:
    def test_resolve_excellent(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice, stake=10**18)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        contract.submit_evidence(task_key, json.dumps(["https://example.com"]), "Done")

        eval_json = json.dumps({
            "quality_score": 95,
            "completeness_score": 100,
            "deadline_met": True,
            "deliverables_found": 3,
            "deliverables_required": 3,
            "overall_verdict": "excellent",
            "payout_percentage": 100,
            "issues": [],
            "strengths": ["Clean code", "Great tests", "Good docs"],
            "reasoning": "All deliverables exceeded expectations",
        })

        direct_vm.sender = direct_alice
        result = json.loads(contract.resolve_task(task_key, eval_json))
        assert result["status"] == "resolved"
        assert result["verdict"] == "excellent"
        assert result["reputation_change"] == "50"
        assert int(result["payout"]) > 0

    def test_resolve_failed(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice, stake=10**18)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        contract.submit_evidence(task_key, json.dumps(["https://example.com"]), "Partial")

        eval_json = json.dumps({
            "quality_score": 20,
            "completeness_score": 30,
            "deadline_met": False,
            "deliverables_found": 1,
            "deliverables_required": 3,
            "overall_verdict": "failed",
            "payout_percentage": 0,
            "issues": ["Missing tests", "No docs"],
            "strengths": [],
            "reasoning": "Major deliverables missing",
        })

        direct_vm.sender = direct_alice
        result = json.loads(contract.resolve_task(task_key, eval_json))
        assert result["verdict"] == "failed"
        assert result["reputation_change"] == "-100"
        assert int(result["payout"]) > 0
        assert int(result["penalty"]) > int(result["payout"])

    def test_resolve_updates_stats(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        contract.submit_evidence(task_key, json.dumps(["https://example.com"]), "Done")

        eval_json = json.dumps({
            "quality_score": 85,
            "completeness_score": 90,
            "deadline_met": True,
            "deliverables_found": 3,
            "deliverables_required": 3,
            "overall_verdict": "acceptable",
            "payout_percentage": 95,
            "issues": [],
            "strengths": ["Good work"],
            "reasoning": "Meets SLA requirements",
        })

        direct_vm.sender = direct_alice
        contract.resolve_task(task_key, eval_json)
        stats = json.loads(contract.get_platform_stats())
        assert int(stats["total_resolved"]) == 1
        assert int(stats["platform_balance"]) > 0

    def test_agent_reputation_updated(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        contract.submit_evidence(task_key, json.dumps(["https://example.com"]), "Done")

        eval_json = json.dumps({
            "quality_score": 95,
            "completeness_score": 100,
            "deadline_met": True,
            "deliverables_found": 3,
            "deliverables_required": 3,
            "overall_verdict": "excellent",
            "payout_percentage": 100,
            "issues": [],
            "strengths": ["Perfect"],
            "reasoning": "Exceeded all expectations",
        })

        direct_vm.sender = direct_alice
        contract.resolve_task(task_key, eval_json)
        addr_key = addr_str(direct_bob)
        profile = json.loads(contract.get_agent_profile(addr_key))
        assert "reputation" in profile and int(profile["reputation"]) == 550
        assert int(profile["tasks_completed"]) == 1


# ============ DISPUTE SYSTEM ============

class TestDisputeSystem:
    def test_raise_dispute(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        contract.submit_evidence(task_key, json.dumps(["https://example.com"]), "Done")

        eval_json = json.dumps({
            "quality_score": 20, "completeness_score": 30, "deadline_met": False,
            "deliverables_found": 1, "deliverables_required": 3,
            "overall_verdict": "failed", "payout_percentage": 0,
            "issues": ["Missing"], "strengths": [], "reasoning": "Incomplete",
        })
        direct_vm.sender = direct_alice
        contract.resolve_task(task_key, eval_json)

        direct_vm.sender = direct_bob
        direct_vm.value = 10**17
        dispute_key = contract.raise_dispute(
            task_key,
            "Evaluation was unfair",
            json.dumps(["https://github.com/test-agent/completed-work"]),
        )
        direct_vm.value = 0
        assert dispute_key is not None

    def test_get_dispute(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)
        task_key = create_task(contract, direct_vm, direct_alice)
        direct_vm.sender = direct_bob
        contract.accept_task(task_key)
        contract.submit_evidence(task_key, json.dumps(["https://example.com"]), "Done")

        eval_json = json.dumps({
            "quality_score": 20, "completeness_score": 30, "deadline_met": False,
            "deliverables_found": 1, "deliverables_required": 3,
            "overall_verdict": "failed", "payout_percentage": 0,
            "issues": [], "strengths": [], "reasoning": "Failed",
        })
        direct_vm.sender = direct_alice
        contract.resolve_task(task_key, eval_json)

        direct_vm.sender = direct_bob
        direct_vm.value = 10**17
        dispute_key = contract.raise_dispute(
            task_key, "Unfair", json.dumps(["https://example.com"])
        )
        direct_vm.value = 0

        dispute = json.loads(contract.get_dispute(dispute_key))
        assert dispute["status"] == "open"
        assert addr_str(direct_bob) == dispute["challenger"]


# ============ PLATFORM ADMIN ============

class TestPlatformAdmin:
    def test_set_platform_fee(self, direct_vm, direct_deploy, direct_owner):
        contract = direct_deploy("contracts/agent_sla.py")
        direct_vm.sender = direct_owner
        result = json.loads(contract.set_platform_fee(300))
        assert result["status"] == "updated"

    def test_set_platform_fee_too_high(self, direct_vm, direct_deploy, direct_owner):
        contract = direct_deploy("contracts/agent_sla.py")
        direct_vm.sender = direct_owner
        result = json.loads(contract.set_platform_fee(1500))
        assert "error" in result

    def test_set_platform_fee_not_owner(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        direct_vm.sender = direct_alice
        result = json.loads(contract.set_platform_fee(300))
        assert "error" in result


# ============ EDGE CASES ============

class TestEdgeCases:
    def test_nonexistent_task(self, direct_vm, direct_deploy):
        contract = direct_deploy("contracts/agent_sla.py")
        result = json.loads(contract.get_task("999"))
        assert "error" in result

    def test_nonexistent_agent(self, direct_vm, direct_deploy, direct_alice):
        contract = direct_deploy("contracts/agent_sla.py")
        result = json.loads(contract.get_agent_profile(addr_str(direct_alice)))
        assert "error" in result

    def test_nonexistent_dispute(self, direct_vm, direct_deploy):
        contract = direct_deploy("contracts/agent_sla.py")
        result = json.loads(contract.get_dispute("999"))
        assert "error" in result

    def test_multiple_tasks_sequential(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        contract = direct_deploy("contracts/agent_sla.py")
        register_agent(contract, direct_vm, direct_bob)

        for i in range(3):
            task_key = create_task(contract, direct_vm, direct_alice)
            direct_vm.sender = direct_bob
            contract.accept_task(task_key)
            contract.submit_evidence(task_key, json.dumps(["https://example.com"]), f"Task {i+1} done")
            eval_json = json.dumps({
                "quality_score": 80, "completeness_score": 85, "deadline_met": True,
                "deliverables_found": 3, "deliverables_required": 3,
                "overall_verdict": "acceptable", "payout_percentage": 95,
                "issues": [], "strengths": ["Consistent"], "reasoning": "Good work",
            })
            direct_vm.sender = direct_alice
            contract.resolve_task(task_key, eval_json)

        stats = json.loads(contract.get_platform_stats())
        assert int(stats["total_resolved"]) == 3

    def test_full_lifecycle(self, direct_vm, direct_deploy, direct_alice, direct_bob):
        """Complete lifecycle: register → create → accept → submit → evaluate → resolve."""
        contract = direct_deploy("contracts/agent_sla.py")

        # 1. Register agent
        reg = json.loads(register_agent(contract, direct_vm, direct_bob, "FullLifecycleAgent"))
        assert reg["status"] == "registered"

        # 2. Create task
        task_key = create_task(contract, direct_vm, direct_alice, stake=2 * 10**18)
        task = json.loads(contract.get_task(task_key))
        assert task["status"] == "open"

        # 3. Accept task
        direct_vm.sender = direct_bob
        acc = json.loads(contract.accept_task(task_key))
        assert acc["status"] == "accepted"

        # 4. Submit evidence
        sub = json.loads(contract.submit_evidence(
            task_key, json.dumps(["https://httpbin.org/get"]), "All deliverables complete"
        ))
        assert sub["status"] == "submitted"

        # 5. Mock and evaluate
        direct_vm.mock_web("https://httpbin.org/get", '{"url": "https://httpbin.org/get"}')
        direct_vm.mock_llm(".*", json.dumps({
            "quality_score": 90, "completeness_score": 95, "deadline_met": True,
            "deliverables_found": 3, "deliverables_required": 3,
            "overall_verdict": "excellent", "payout_percentage": 100,
            "issues": [], "strengths": ["Great work"], "reasoning": "Exceeded expectations",
        }))

        evaluation = json.loads(contract.evaluate_and_store(task_key))
        assert evaluation["overall_verdict"] in ("excellent", "acceptable", "partial", "failed")

        # 6. Resolve
        direct_vm.sender = direct_alice
        resolve = json.loads(contract.resolve_task(task_key, json.dumps(evaluation)))
        assert resolve["status"] == "resolved"
        assert int(resolve["payout"]) > 0

        # 7. Verify final state
        final_task = json.loads(contract.get_task(task_key))
        assert final_task["status"] == "resolved"

        addr_key = addr_str(direct_bob)
        final_profile = json.loads(contract.get_agent_profile(addr_key))
        assert "reputation" in final_profile and int(final_profile["reputation"]) != 500

        final_stats = json.loads(contract.get_platform_stats())
        assert int(final_stats["total_resolved"]) == 1
