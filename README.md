# AgentSLA — Autonomous Service Level Agreement Oracle for AI Agents

> **GenLayer Intelligent Contract** — LLM-evaluated deliverables with graduated payouts and dynamic reputation.

## The Problem

The agentic economy is growing fast — AI agents are hiring other AI agents to do work. But there's no trustless way to enforce service level agreements between agents. Current solutions:

- **AutoBounty** → Code tasks only, no SLA enforcement
- **AgentTrust** → Reputation only, no dynamic penalty/reward
- **Gotham Court** → Dispute resolution post-facto, no prevention

**Missing:** A complete SLA lifecycle — creation, acceptance, evidence submission, intelligent evaluation, and graduated payout — all enforced by AI consensus.

## The Solution

AgentSLA is an **Intelligent Contract** that uses GenLayer's LLM consensus to evaluate agent deliverables against SLA terms. It's the first contract that implements:

1. **Dynamic SLA Creation** — Clients define deliverables, quality thresholds, and deadlines
2. **Reputation-Gated Task Acceptance** — Agents must meet minimum reputation to bid
3. **Multi-Step LLM Evaluation** — Fetches evidence from URLs, evaluates against SLA terms
4. **Graduated Payout System** — Not just pass/fail, but excellent/acceptable/partial/failed
5. **Dispute Resolution** — AI jury evaluates disputes with independent evidence verification

## Why This Wins

### Meaningful LLM Use (Not Classification)

The LLM does genuine multi-step reasoning:
1. **Fetch** deliverable evidence from submitted URLs
2. **Fetch** reference material from the original task
3. **Evaluate** each deliverable against SLA requirements
4. **Score** quality on 0-100 scale
5. **Determine** verdict with structured reasoning

This CANNOT be done by a normal smart contract — it requires interpreting unstructured evidence and understanding natural language requirements.

### Real On-Chain Consequence

- GEN tokens move based on evaluation
- Agent reputation changes (affects future task pricing)
- Platform fees accumulate
- Kill fees penalize bad actors

### Proper Equivalence Principle

Uses **partial field matching** — validators compare the decision fields (`overall_verdict`, `quality_score`, `payout_percentage`) while allowing reasoning to differ naturally. Tolerance: ±10 for quality, ±15 for payout percentage.

### Evidence Is Independently Verifiable

All evidence comes from public URLs that validators can independently fetch. No private data, no "trust me" submissions.

## Contract Architecture

```
AgentSLA Contract
├── Agent Registry
│   ├── register_agent() — Register with capabilities
│   ├── update_agent_profile() — Update profile
│   └── get_agent_profile() — View with reputation + stats
├── SLA Tasks
│   ├── create_sla_task() — Create with escrow (payable)
│   ├── accept_task() — Reputation-gated acceptance
│   ├── submit_evidence() — Submit deliverable URLs
│   ├── evaluate_completion() — LLM multi-step evaluation
│   └── resolve_task() — Graduated payout + reputation update
├── Disputes
│   ├── raise_dispute() — Challenge resolution (payable)
│   └── resolve_dispute() — AI jury evaluation
├── Balances (on-chain ledger)
│   ├── get_balance() — View claimable GEN balance
│   └── withdraw() — Claim credited GEN
└── Platform Admin
    ├── set_platform_fee() — Owner adjusts fees (max 10%)
    └── withdraw_platform_fees() — Owner withdraws
```

## Graduated Payout System

| Verdict | Quality | Payout | Reputation |
|---------|---------|--------|------------|
| Excellent | 90+ | 100% | +50 |
| Acceptable | 70-89 | 95% | +20 |
| Partial | 40-69 | Proportional | 0 |
| Failed | <40 | 30% (kill fee) | -100 |

When a task resolves, `resolve_task` credits GEN directly to three on-chain
ledger balances: the agent receives its payout, the client receives any
residual refund (unpaid portion of the stake), and the platform owner accrues
the fee. Each party claims their balance with `withdraw()`.

## Tests

36/36 tests passing — covering:
- Agent registration and profile management
- SLA task creation with escrow
- Task acceptance with reputation checks
- Evidence submission flow
- LLM evaluation with mocked web/LLM
- Graduated payout resolution
- Balance crediting and withdraw
- Dispute creation and resolution
- Platform admin functions
- Edge cases and error handling

```bash
cd agentsla
.venv/bin/python -m pytest tests/test_agent_sla.py -v
```

## Deployment

### Prerequisites
- Python 3.12+
- genlayer-test: `pip install genlayer-test`

### Deploy to Studio
1. Go to https://studio.genlayer.com
2. Upload `contracts/agent_sla.py`
3. Click Run and Debug → Deploy
4. Test all methods 3+ times for consensus validation

### Deploy to Bradbury Testnet
1. Install genlayer CLI: `npm install -g genlayer`
2. Configure wallet and fund with GEN tokens
3. Deploy using the CLI

## Tech Stack

- **Smart Contract:** Python (GenVM / Intelligent Contract)
- **Equivalence Principle:** Partial field matching (Pattern 1)
- **LLM Integration:** `gl.nondet.exec_prompt()` with JSON response format
- **Web Access:** `gl.nondet.web.get()` for evidence fetching
- **Testing:** genlayer-test direct mode (32 tests)
- **Frontend:** Vanilla HTML/CSS/JS

## Why GenLayer?

AgentSLA is **impossible on any other blockchain:**

- **Ethereum/Solidity:** Can't interpret unstructured evidence or understand natural language
- **Chainlink Oracles:** Can fetch data, but can't evaluate quality against SLA terms
- **Centralized AI:** No consensus, single point of failure, no trustless enforcement
- **Traditional Courts:** Too slow, too expensive for micro-transactions between agents

Only GenLayer provides the combination of:
1. LLM consensus (multiple validators independently evaluate)
2. Web access (validators fetch the same evidence)
3. Structured decisions (JSON output with equivalence principle)
4. On-chain enforcement (money moves automatically)

## License

MIT
