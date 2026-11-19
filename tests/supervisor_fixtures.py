"""Test data for the supervisor: sample evidence restated in other words, the way a paper reader would write claims."""

# Sample evidence ID -> the same point in different words (each checked against its full quote).

REWORDED_CLAIMS = {
    "example-0-overview": "Systems with several cooperating AI agents often outperform a single agent on many kinds of tasks.",
    "example-0-results": "The authors show theoretically that needle and chain search never show a phase transition in communication degree, while tree and factorizable search do.",
    "example-1-overview": "Doing well on single-turn prompts does not guarantee good performance in multi-turn conversations with LLMs.",
    "example-1-methods": "The study uses a factorial experiment varying social context, hedonic drive and the agent's age persona.",
    "example-1-results": "19,200 agent runs were collected over 64 experimental conditions, and almost all of them were valid.",
    "example-2-overview": "Fast-changing software projects end up with missing or stale documentation, which slows onboarding and maintenance.",
    "example-2-results": "Prior work has used LLMs as automatic judges to rate code understanding and code summaries.",
    "example-3-overview": "Most AI models used in science work toward fixed objectives and cannot easily reason about scientific questions or change strategy based on results.",
    "example-3-methods": "MASTER connects LLM reasoning to automated electronic-structure simulations in a closed loop modeled on a research team.",
    "example-4-overview": "Staying aligned with stakeholder preferences matters more as teams of LLM agents take on longer, project-scale tasks.",
    "example-4-methods": "ARCANE learns interpretable rubrics that the manager uses to steer worker agents toward stakeholder preferences.",
    "example-4-results": "The experiments test whether rubric guidance makes worker outputs more useful and whether the manager ranks candidates faithfully.",
    "example-5-overview": "LLM-based multi-agent systems are becoming a strong approach for complex tasks, with agents that can be models or tools.",
    "example-5-limitations": "Shapley-value credit assignment helps stop one agent from taking over the work to claim more credit.",
    "example-6-overview": "Scaling a single huge LLM runs into problems such as hallucination and catastrophic forgetting, which has led to multi-agent approaches.",
    "example-6-results": "Experiments checked whether the model graph groups models by their known skills.",
    "example-7-overview": "LLMs are good at generation, problem solving, translation and summarization, and do well on many benchmarks.",
    "example-7-methods": "SMAGDi simulates domain-specific personas with Socratic chain-of-thought so that multi-step problems can be deliberated efficiently.",
    "example-7-limitations": "Because of limited compute, the models were not trained on the full MMLU auxiliary training set.",
}