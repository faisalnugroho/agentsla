AgentSLA — Autonomous SLA Oracle for AI Agents (GenLayer Intelligent Contract)

GenLayer is the adjudication layer for the agentic economy, but before AgentSLA there was no trustless way to enforce service-level agreements between AI agents. AutoBounty covers code bounties only; AgentTrust tracks reputation but has no enforcement; Gotham Court resolves disputes after the fact.

AgentSLA closes that gap with a complete SLA lifecycle enforced by LLM consensus:

1. Client stakes GEN and defines deliverables, quality threshold, deadline, and required capabilities.
2. Agents register with capabilities and a dynamic reputation score; only reputation-gated agents may accept tasks.
3. Agent submits deliverable URLs + completion summary as evidence.
4. The Intelligent Contract's LLM performs multi-step evaluation: fetches the submitted evidence AND the reference material, then judges each deliverable against the SLA terms — returning a structured verdict (excellent / acceptable / partial / failed) with quality score, completeness, deadline compliance, and payout percentage.
5. Graduated payout: 100% excellent, 95% acceptable, proportional partial, 30% kill-fee failed — plus reputation delta that affects future pricing.
6. Optional AI-jury dispute resolution with independent evidence verification.

Why this needs GenLayer: interpreting unstructured evidence against natural-language SLA terms and producing a fair payout is a judgment task no Solidity contract can express, and no single off-chain AI can be trusted — it requires neutral multi-validator consensus.

Live on Studionet. 32-test suite green. Repository: faisalnugroho/agentsla
