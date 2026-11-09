# Multi-agent large language models — Literature Review

- 생성일: 2026-11-05
- 분석 대상 논문 수: 8
- 선정 기준: 관련성 우선, 최신성 차순위
- 보고서 ID: 1cd0f4e232c74517b1b6796080bf1c09 / revision 0
- 검증 상태: Supervisor Evidence 검증 대기

**예시 데이터 보고서: 실제 원문 발췌를 사용하는 그룹 2 인터페이스 시험용 입력입니다. 그룹 2의 실제 분석 결과가 아닙니다.**

## 1. Introduction

예시: 해당 섹션의 원문 발췌 — AI agents are increasingly being deployed in multi-agent systems, in which agents communicate, interact, and cooperate to complete tasks. Multi-agent systems have been shown to improve over single agents across a variety of domains and task types ( Wu et al., 2023 ; Guo et al., 2024 ; Hong et al., 2024 ; Qian et al., 2024 ; Du et al., 2024 ; Kim et al., 2024 ; Agashe et al., 2025 ) . However, comparatively little is known about their collective dynamics, such as emergent or nonlinear behavior; a [example-0-overview](#ev-443e7ea232689afe)

예시: 해당 섹션의 원문 발췌 — Multi-Agent Systems (MAS) built from Large Language Models (LLMs) are emerging as a powerful paradigm for complex tasks. Agents in this context may be LLMs, ML models, or tools ( Ye et al., 2025 ; Wang et al., 2025b ; He and others, 2024 ; Yang et al., 2024 ; Team, 2025 ) , each taking structured inputs and producing outputs such as text, code, or tool calls. Unlike classical RL agents with compact, repetitive action spaces ( Bamford and Ovalle, 2021 ; Li et al., 2021a ; Hubert and others, 2021  [example-5-overview](#ev-4deb7f8cc9cd8aea)

예시: 해당 섹션의 원문 발췌 — Large language models (LLMs) have demonstrated remarkable capabilities across a wide range of natural language tasks, driven by advances in model scaling ( Zhao et al. 2025 ) . However, the monolithic approach of scaling a single, massive model faces challenges such as hallucination ( Maynez et al. 2020 ) and catastrophic forgetting ( Kirkpatrick et al. 2017 ) , limiting its ability to achieve robust performance across all domains. In response, a multi-agent approach based on LLMs has emerged as [example-6-overview](#ev-976d0398ffd6e87b)

예시: 해당 섹션의 원문 발췌 — Large Language Models (LLMs) have proven adept at generation, problem-solving, translation, and summarization, performing well on various benchmarks. An LLM’s capability to learn from vast amounts of data allows it to handle complex tasks logically and fluently. Although LLMs have demonstrated competency in handling diverse tasks, their performance is often hurt by inaccuracies ( Zhang et al., 2023 ) .<br><br>Multi-agent systems (MAS) have been explored as a solution to combat this issue. These system [example-7-overview](#ev-79b0b45bc4e09c54)

예시: 해당 섹션의 원문 발췌 — Modern uses of large language models (LLMs) are inherently conversational and iterative, as users and agents co-construct tasks over multiple turns, revise goals, and recover from mistakes. Recent multi-turn evaluations show that single-turn prowess does not guarantee long-horizon reliability: agentic setups reveal gaps in reasoning and decision-making Liu et al. (2023) , tool use and natural-language feedback help but interact idiosyncratically with training and instruction tuning Wang et al. ( [example-1-overview](#ev-d1ee655942f90d9a)

예시: 해당 섹션의 원문 발췌 — As software projects evolve rapidly, they often lead to incomplete, outdated, or inconsistent documentation. This friction slows on-boarding, complicates maintenance, and increases the risk of defects and architectural drift. To address these problems, considerable efforts have been dedicated to automated code summarization, such as identifying class stereotypes and retrieving functional keywords ( Zhu and Pan, 2019 ) . More recently, deep learning approaches have advanced this field by utilizin [example-2-overview](#ev-c2a58bd1ea3c9c7d)

예시: 해당 섹션의 원문 발췌 — Recent advances in artificial intelligence (AI) have expanded its role in scientific research, enabling systems to analyze data, identify patterns, and even propose hypotheses. \[ 6 \] Yet, most of these models operate within fixed objectives and have limited ability to deliberate about scientific questions or adapt their strategies based on outcomes. Reasoning, the process of evaluating competing hypotheses and designing informative experiments, is central to genuine scientific exploration. In ma [example-3-overview](#ev-0aeaae33d206990c)

예시: 해당 섹션의 원문 발췌 — As AI agents based on large language models (LLMs) take on longer-horizon, project-scale tasks with multiple specialized agents, maintaining alignment with stakeholder preferences becomes increasingly critical ( Masters et al. 2025 ) . Prior research has shown how cooperation can falter under partial observability, shifting incentives, or social feedback loops ( Leibo et al. 2017 ; Jaques et al. 2019 ; Carichon et al. 2025 , e.g.) . Recent studies on LLM-based debate and collaborative reasoning  [example-4-overview](#ev-e7bd9ffb3c80c539)

## 2. Overview of Selected Papers

### Absorbing State Phase Transitions in Multi-Agent Search

[arxiv:2609.38327](https://arxiv.org/abs/2609.38327v2) / 최초 제출 2026-09-29

예시: 해당 섹션의 원문 발췌 — AI agents are increasingly being deployed in multi-agent systems, in which agents communicate, interact, and cooperate to complete tasks. Multi-agent systems have been shown to improve over single agents across a variety of domains and task types ( Wu et al., 2023 ; Guo et al., 2024 ; Hong et al., 2024 ; Qian et al., 2024 ; Du et al., 2024 ; Kim et al., 2024 ; Agashe et al., 2025 ) . However, comparatively little is known about their collective dynamics, such as emergent or nonlinear behavior; a [example-0-overview](#ev-443e7ea232689afe)

### Delay-of-Gratification as a Multi-Agent Survival Micro-benchmark for Long-Horizon LLMs: Social Exposure, Personas, and Tool Use Budgets

[arxiv:2609.29509](https://arxiv.org/abs/2609.29509v1) / 최초 제출 2026-08-26

예시: 해당 섹션의 원문 발췌 — Modern uses of large language models (LLMs) are inherently conversational and iterative, as users and agents co-construct tasks over multiple turns, revise goals, and recover from mistakes. Recent multi-turn evaluations show that single-turn prowess does not guarantee long-horizon reliability: agentic setups reveal gaps in reasoning and decision-making Liu et al. (2023) , tool use and natural-language feedback help but interact idiosyncratically with training and instruction tuning Wang et al. ( [example-1-overview](#ev-d1ee655942f90d9a)

### Agent4cs: A Multi-agent System for Code Summarization in Large Hierarchical Codebases

[arxiv:2607.01425](https://arxiv.org/abs/2607.01425v2) / 최초 제출 2026-07-01

예시: 해당 섹션의 원문 발췌 — As software projects evolve rapidly, they often lead to incomplete, outdated, or inconsistent documentation. This friction slows on-boarding, complicates maintenance, and increases the risk of defects and architectural drift. To address these problems, considerable efforts have been dedicated to automated code summarization, such as identifying class stereotypes and retrieving functional keywords ( Zhu and Pan, 2019 ) . More recently, deep learning approaches have advanced this field by utilizin [example-2-overview](#ev-c2a58bd1ea3c9c7d)

### Hierarchical Multi-agent Large Language Model Reasoning for Autonomous Functional Materials Discovery

[arxiv:2512.13930](https://arxiv.org/abs/2512.13930v1) / 최초 제출 2025-12-15

예시: 해당 섹션의 원문 발췌 — Recent advances in artificial intelligence (AI) have expanded its role in scientific research, enabling systems to analyze data, identify patterns, and even propose hypotheses. \[ 6 \] Yet, most of these models operate within fixed objectives and have limited ability to deliberate about scientific questions or adapt their strategies based on outcomes. Reasoning, the process of evaluating competing hypotheses and designing informative experiments, is central to genuine scientific exploration. In ma [example-3-overview](#ev-0aeaae33d206990c)

### ARCANE: A Multi-Agent Framework for Interpretable and Configurable Alignment

[arxiv:2512.06196](https://arxiv.org/abs/2512.06196v1) / 최초 제출 2025-12-05

예시: 해당 섹션의 원문 발췌 — As AI agents based on large language models (LLMs) take on longer-horizon, project-scale tasks with multiple specialized agents, maintaining alignment with stakeholder preferences becomes increasingly critical ( Masters et al. 2025 ) . Prior research has shown how cooperation can falter under partial observability, shifting incentives, or social feedback loops ( Leibo et al. 2017 ; Jaques et al. 2019 ; Carichon et al. 2025 , e.g.) . Recent studies on LLM-based debate and collaborative reasoning  [example-4-overview](#ev-e7bd9ffb3c80c539)

### Who Gets the Reward & Who Gets the Blame? Evaluation-Aligned Training Signals for Multi-LLM Agents

[arxiv:2511.10687](https://arxiv.org/abs/2511.10687v3) / 최초 제출 2025-11-11

예시: 해당 섹션의 원문 발췌 — Multi-Agent Systems (MAS) built from Large Language Models (LLMs) are emerging as a powerful paradigm for complex tasks. Agents in this context may be LLMs, ML models, or tools ( Ye et al., 2025 ; Wang et al., 2025b ; He and others, 2024 ; Yang et al., 2024 ; Team, 2025 ) , each taking structured inputs and producing outputs such as text, code, or tool calls. Unlike classical RL agents with compact, repetitive action spaces ( Bamford and Ovalle, 2021 ; Li et al., 2021a ; Hubert and others, 2021  [example-5-overview](#ev-4deb7f8cc9cd8aea)

### The Geometry of Dialogue: Graphing Language Models to Reveal Synergistic Teams for Multi-Agent Collaboration

[arxiv:2510.26352](https://arxiv.org/abs/2510.26352v2) / 최초 제출 2025-10-30

예시: 해당 섹션의 원문 발췌 — Large language models (LLMs) have demonstrated remarkable capabilities across a wide range of natural language tasks, driven by advances in model scaling ( Zhao et al. 2025 ) . However, the monolithic approach of scaling a single, massive model faces challenges such as hallucination ( Maynez et al. 2020 ) and catastrophic forgetting ( Kirkpatrick et al. 2017 ) , limiting its ability to achieve robust performance across all domains. In response, a multi-agent approach based on LLMs has emerged as [example-6-overview](#ev-976d0398ffd6e87b)

### SMAGDi: Socratic Multi Agent Interaction Graph Distillation for Efficient High Accuracy Reasoning

[arxiv:2511.05528](https://arxiv.org/abs/2511.05528v1) / 최초 제출 2025-10-29

예시: 해당 섹션의 원문 발췌 — Large Language Models (LLMs) have proven adept at generation, problem-solving, translation, and summarization, performing well on various benchmarks. An LLM’s capability to learn from vast amounts of data allows it to handle complex tasks logically and fluently. Although LLMs have demonstrated competency in handling diverse tasks, their performance is often hurt by inaccuracies ( Zhang et al., 2023 ) .<br><br>Multi-agent systems (MAS) have been explored as a solution to combat this issue. These system [example-7-overview](#ev-79b0b45bc4e09c54)

## 3. Comparative Analysis

| 논문 | 방법론 | 데이터셋 | 주요 결과 |
|---|---|---|---|
| arxiv:2609.38327 | 입력 근거 없음 | 입력 근거 없음 | 예시: 해당 섹션의 원문 발췌 — We theoretically derive d c d\_{c} for all four search task classes. We show that needle and chain search tasks will never reach a phase transition in communication degree (Section 3.1 ), whereas d c d\_{c} exists for tree and factorizable search (Section 3.2 ). [example-0-results](#ev-a22f2ced80ac8b85) |
| arxiv:2609.29509 | 예시: 해당 섹션의 원문 발췌 — Experimental Factors. We implement a factorial design that crosses several core dimensions, with independent randomization per experimental cell and replicated trials: social context: isolated vs. broadcast; hedonic drive: crave vs. like vs. neutral; age persona: child vs. adult vs. senior; tool-use policy: MUST vs. MAY. Optional toggles in the run plan include budget visibility (visible vs. hidden). The default total time is set to max\_steps = 20 (minutes), with a fixed answer format and final  [example-1-methods](#ev-dd945fc75d99c76c) | 입력 근거 없음 | 예시: 해당 섹션의 원문 발췌 — Sample and Data Quality. We ran 19,200 agent trajectories across 64 experimental cells (6 agents per cell, with a time horizon of T = 19 T=19 ). The data quality was high, with 99.9% of trajectories being valid and only 0.1% invalid. The aggregate behavior of agents shows a strong impulse to eat in the first minute, followed by a long tail of waiting. Key metrics include an initial eat rate ≈ 0.125 \\approx 0.125 , a total eat rate ≈ 0.241 \\approx 0.241 , and a winners rate ≈ 0.759 \\approx 0.759  [example-1-results](#ev-4937223dfb697723) |
| arxiv:2607.01425 | 입력 근거 없음 | 입력 근거 없음 | 예시: 해당 섹션의 원문 발췌 — Beyond generating summaries, recent research has explored leveraging language models as automated evaluators to judge the quality of code understanding and summarization. CodeJudge-Eval establishes a benchmark for measuring LLMs’ code understanding abilities through their performance in judging code solution correctness ( Zhao et al., 2025 ) , while CODERPE integrates multi-role prompts into LLMs to automatically evaluate code summaries across coherence, fluency, and relevance ( Wu et al., 2025  [example-2-results](#ev-3441ac8656296453) |
| arxiv:2512.13930 | 예시: 해당 섹션의 원문 발췌 — The MASTER framework integrates LLM reasoning with autonomous electronic-structure simulation in a closed loop that emulates the operation of a scientific research team (Fig. 1 a). The system is organized into three tightly coupled yet functionally distinct layers. The design layer comprises a team of LLM agents that use natural language to formulate hypotheses and deliberate, individually or collectively, on which material to evaluate next based on the accumulated simulation history. Once a can [example-3-methods](#ev-f3df995d06e5e870) | 입력 근거 없음 | 입력 근거 없음 |
| arxiv:2512.06196 | 예시: 해당 섹션의 원문 발췌 — ARCANE is a framework for learning structured, interpretable proxy utilities that align workers’ behavior with stakeholder preferences. ARCANE instantiates the abstract alignment setting from Section 3 by representing the manager’s coordination signal as a rubric : a decomposable, verifiable, and dynamically configurable approximation of the stakeholder’s true utility function U ∗ ​ ( y ∣ x ) U^{\*}(y\\mid x) .<br><br>The core idea is to have our manager M learn a rubric decomposer 𝔇 ϕ \\mathfrak{D}\_{\\ph [example-4-methods](#ev-0bdaba3552468ab5) | 입력 근거 없음 | 예시: 해당 섹션의 원문 발췌 — Our experiments aim to answer three research questions:<br><br>RQ1 (Usefulness): Does guiding the worker team with learned rubrics increase the utility of their outputs versus unguided generation?<br><br>RQ2 (Faithfulness): Does the manager agent learn to rank candidates at test time in a manner consistent with the rankings computed from the stakeholder utility U ⋆ U^{\\star} ?<br><br>RQ3 (Interpretability & Efficiency): Are the rubrics generated by the manager agent compact, legible, and practical to verify? [example-4-results](#ev-874afc84dd2a0e1b) |
| arxiv:2511.10687 | 입력 근거 없음 | 입력 근거 없음 | 입력 근거 없음 |
| arxiv:2510.26352 | 입력 근거 없음 | 입력 근거 없음 | 예시: 해당 섹션의 원문 발췌 — We conducted a series of experiments to validate our proposed method. First, we tested whether the language model graph could reveal latent model specializations by evaluating its ability to cluster models according to their known capabilities. Second, to validate the effectiveness of our team composition approach, we benchmarked the collective downstream task performance of teams constructed from the identified clusters against several baselines. [example-6-results](#ev-955e4bf3d85eccd8) |
| arxiv:2511.05528 | 예시: 해당 섹션의 원문 발췌 — In this work, we developed SMAGDi (Socratic Multi-Agent Interaction Graph Distillation), enabling efficient deliberation over multi-step problems by simulating domain-specific personas through SCoT (Socratic Chain-of-Thought) to mimic these analysis processes. These domain-specific personas differ from the traditional use of interchangeable agents, as each has a specific alignment and purpose ( Wei et al., 2023 ) . [example-7-methods](#ev-c0ad4ed279111d71) | 입력 근거 없음 | 입력 근거 없음 |

## 4. Common References

집계 기준: 선정 논문 중 서로 다른 인용 논문 수. 단일 논문 내 반복 인용은 한 번으로 집계합니다.

| 문헌 | 인용 논문 수 | 인용한 선정 논문 |
|---|---:|---|
| Wu et al. (2023) Q. Wu, G. Bansal, J. Zhang, Y. Wu, B. Li, E. Zhu, L. Jiang, X. Zhang, S. Zhang, J. Liu, et al. AutoGen: enabling next-gen llm applications via multi-agent conversation . External Links: 2308.08155 , Link Cited by: Models and Implementation . | 2 | arxiv:2510.26352, arxiv:2609.38327 |
| Grattafiori et al. (2024) A. Grattafiori, A. Dubey, A. Jauhri, A. Pandey, A. Kadian, A. Al-Dahle, A. Letman, A. Mathur, A. Schelten, A. Vaughan, et al. The llama 3 herd of models . External Links: 2407.21783 , Link Cited by: Models and Implementation . | 2 | arxiv:2510.26352, arxiv:2511.05528 |
| Team et al. (2025) G. Team, A. Kamath, J. Ferret, S. Pathak, N. Vieillard, R. Merhej, S. Perrin, T. Matejovicova, A. Ramé, M. Rivière, et al. Gemma 3 technical report . External Links: 2503.19786 , Link Cited by: Models and Implementation . | 2 | arxiv:2510.26352, arxiv:2607.01425 |

## 5. Connections and Conflicts

연결/상충 분석 입력이 없습니다. 결과를 추정하지 않습니다.

## 6. Research Gaps

제공된 근거가 없습니다.

## 7. Limitations

예시: 해당 섹션의 원문 발췌 — Preventing credit hoarding. A key risk in cooperative multi-agent systems is that one agent might dominate the workflow, suppressing others to inflate its own marginal credit. Our framework mitigates this through two mechanisms. First, Shapley values enforce efficiency and symmetry, ensuring that duplicated or suppressive behavior yields little marginal gain. Second, message-level PRM supervision distributes an agent’s credit across its responses, so redundant or uninformative steps receive near [example-5-limitations](#ev-0328298d2a7823ae)

예시: 해당 섹션의 원문 발췌 — Training Data Due to computational constraints, we did not train our models on the full auxiliary train split of MMLU. Further testing will be needed to confirm that SMAGDi will perform better than other models if trained on all data.<br><br>Large-Scale Setups Since SMAGDi was tested on lightweight models, we lack proof of its scalability to larger environments. In application, alternatives that provide similar results with minimal computational costs would prove to be more efficient.<br><br>Dynamic Weighti [example-7-limitations](#ev-e9f41b2ba234165c)

구조·인용 위치 검증은 사실 검증을 대체하지 않습니다. 주장의 원문 함의와 상충 여부는 Supervisor/Reader가 확인해야 합니다.

미충족 영역:

- methods:arxiv:2609.38327
- datasets:arxiv:2609.38327
- limitations:arxiv:2609.38327
- datasets:arxiv:2609.29509
- limitations:arxiv:2609.29509
- methods:arxiv:2607.01425
- datasets:arxiv:2607.01425
- limitations:arxiv:2607.01425
- datasets:arxiv:2512.13930
- results:arxiv:2512.13930
- limitations:arxiv:2512.13930
- datasets:arxiv:2512.06196
- limitations:arxiv:2512.06196
- methods:arxiv:2511.10687
- datasets:arxiv:2511.10687
- results:arxiv:2511.10687
- methods:arxiv:2510.26352
- datasets:arxiv:2510.26352
- limitations:arxiv:2510.26352
- datasets:arxiv:2511.05528
- results:arxiv:2511.05528
- connections
- research\_gaps

## 8. References

- [Absorbing State Phase Transitions in Multi-Agent Search](https://arxiv.org/abs/2609.38327v2) — arxiv:2609.38327

- [Delay-of-Gratification as a Multi-Agent Survival Micro-benchmark for Long-Horizon LLMs: Social Exposure, Personas, and Tool Use Budgets](https://arxiv.org/abs/2609.29509v1) — arxiv:2609.29509

- [Agent4cs: A Multi-agent System for Code Summarization in Large Hierarchical Codebases](https://arxiv.org/abs/2607.01425v2) — arxiv:2607.01425

- [Hierarchical Multi-agent Large Language Model Reasoning for Autonomous Functional Materials Discovery](https://arxiv.org/abs/2512.13930v1) — arxiv:2512.13930

- [ARCANE: A Multi-Agent Framework for Interpretable and Configurable Alignment](https://arxiv.org/abs/2512.06196v1) — arxiv:2512.06196

- [Who Gets the Reward & Who Gets the Blame? Evaluation-Aligned Training Signals for Multi-LLM Agents](https://arxiv.org/abs/2511.10687v3) — arxiv:2511.10687

- [The Geometry of Dialogue: Graphing Language Models to Reveal Synergistic Teams for Multi-Agent Collaboration](https://arxiv.org/abs/2510.26352v2) — arxiv:2510.26352

- [SMAGDi: Socratic Multi Agent Interaction Graph Distillation for Efficient High Accuracy Reasoning](https://arxiv.org/abs/2511.05528v1) — arxiv:2511.05528

- [arxiv:2308.08155](https://arxiv.org/abs/2308.08155)

- [arxiv:2407.21783](https://arxiv.org/abs/2407.21783)

- [arxiv:2503.19786](https://arxiv.org/abs/2503.19786)

### Evidence Map

<a id="ev-443e7ea232689afe"></a>

- example-0-overview: [arxiv:2609.38327 / S1](https://arxiv.org/html/2609.38327v2)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[1\]
  - 발췌: AI agents are increasingly being deployed in multi-agent systems, in which agents communicate, interact, and cooperate to complete tasks. Multi-agent systems have been shown to improve over single agents across a variety of domains and task types ( Wu et al., 2023 ; Guo et al., 2024 ; Hong et al., 2024 ; Qian et al., 2024 ; Du et al., 2024 ; Kim et al., 2024 ; Agashe et al., 2025 ) . However, comparatively little is known about their collective dynamics, such as emergent or nonlinear behavior; a

<a id="ev-a22f2ced80ac8b85"></a>

- example-0-results: [arxiv:2609.38327 / S3](https://arxiv.org/html/2609.38327v2)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[3\]
  - 발췌: We theoretically derive d c d\_{c} for all four search task classes. We show that needle and chain search tasks will never reach a phase transition in communication degree (Section 3.1 ), whereas d c d\_{c} exists for tree and factorizable search (Section 3.2 ).

<a id="ev-d1ee655942f90d9a"></a>

- example-1-overview: [arxiv:2609.29509 / S1](https://arxiv.org/html/2609.29509v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[1\]
  - 발췌: Modern uses of large language models (LLMs) are inherently conversational and iterative, as users and agents co-construct tasks over multiple turns, revise goals, and recover from mistakes. Recent multi-turn evaluations show that single-turn prowess does not guarantee long-horizon reliability: agentic setups reveal gaps in reasoning and decision-making Liu et al. (2023) , tool use and natural-language feedback help but interact idiosyncratically with training and instruction tuning Wang et al. (

<a id="ev-dd945fc75d99c76c"></a>

- example-1-methods: [arxiv:2609.29509 / S4](https://arxiv.org/html/2609.29509v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[4\]
  - 발췌: Experimental Factors. We implement a factorial design that crosses several core dimensions, with independent randomization per experimental cell and replicated trials: social context: isolated vs. broadcast; hedonic drive: crave vs. like vs. neutral; age persona: child vs. adult vs. senior; tool-use policy: MUST vs. MAY. Optional toggles in the run plan include budget visibility (visible vs. hidden). The default total time is set to max\_steps = 20 (minutes), with a fixed answer format and final 

<a id="ev-4937223dfb697723"></a>

- example-1-results: [arxiv:2609.29509 / S5](https://arxiv.org/html/2609.29509v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[5\]
  - 발췌: Sample and Data Quality. We ran 19,200 agent trajectories across 64 experimental cells (6 agents per cell, with a time horizon of T = 19 T=19 ). The data quality was high, with 99.9% of trajectories being valid and only 0.1% invalid. The aggregate behavior of agents shows a strong impulse to eat in the first minute, followed by a long tail of waiting. Key metrics include an initial eat rate ≈ 0.125 \\approx 0.125 , a total eat rate ≈ 0.241 \\approx 0.241 , and a winners rate ≈ 0.759 \\approx 0.759 

<a id="ev-c2a58bd1ea3c9c7d"></a>

- example-2-overview: [arxiv:2607.01425 / S1](https://arxiv.org/html/2607.01425v2)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[1\]
  - 발췌: As software projects evolve rapidly, they often lead to incomplete, outdated, or inconsistent documentation. This friction slows on-boarding, complicates maintenance, and increases the risk of defects and architectural drift. To address these problems, considerable efforts have been dedicated to automated code summarization, such as identifying class stereotypes and retrieving functional keywords ( Zhu and Pan, 2019 ) . More recently, deep learning approaches have advanced this field by utilizin

<a id="ev-3441ac8656296453"></a>

- example-2-results: [arxiv:2607.01425 / S3.SS4](https://arxiv.org/html/2607.01425v2)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[3\]/section\[4\]
  - 발췌: Beyond generating summaries, recent research has explored leveraging language models as automated evaluators to judge the quality of code understanding and summarization. CodeJudge-Eval establishes a benchmark for measuring LLMs’ code understanding abilities through their performance in judging code solution correctness ( Zhao et al., 2025 ) , while CODERPE integrates multi-role prompts into LLMs to automatically evaluate code summaries across coherence, fluency, and relevance ( Wu et al., 2025 

<a id="ev-0aeaae33d206990c"></a>

- example-3-overview: [arxiv:2512.13930 / Sx1](https://arxiv.org/html/2512.13930v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[1\]
  - 발췌: Recent advances in artificial intelligence (AI) have expanded its role in scientific research, enabling systems to analyze data, identify patterns, and even propose hypotheses. \[ 6 \] Yet, most of these models operate within fixed objectives and have limited ability to deliberate about scientific questions or adapt their strategies based on outcomes. Reasoning, the process of evaluating competing hypotheses and designing informative experiments, is central to genuine scientific exploration. In ma

<a id="ev-f3df995d06e5e870"></a>

- example-3-methods: [arxiv:2512.13930 / Sx2.SSx1](https://arxiv.org/html/2512.13930v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[2\]/section\[1\]
  - 발췌: The MASTER framework integrates LLM reasoning with autonomous electronic-structure simulation in a closed loop that emulates the operation of a scientific research team (Fig. 1 a). The system is organized into three tightly coupled yet functionally distinct layers. The design layer comprises a team of LLM agents that use natural language to formulate hypotheses and deliberate, individually or collectively, on which material to evaluate next based on the accumulated simulation history. Once a can

<a id="ev-e7bd9ffb3c80c539"></a>

- example-4-overview: [arxiv:2512.06196 / S1](https://arxiv.org/html/2512.06196v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[1\]
  - 발췌: As AI agents based on large language models (LLMs) take on longer-horizon, project-scale tasks with multiple specialized agents, maintaining alignment with stakeholder preferences becomes increasingly critical ( Masters et al. 2025 ) . Prior research has shown how cooperation can falter under partial observability, shifting incentives, or social feedback loops ( Leibo et al. 2017 ; Jaques et al. 2019 ; Carichon et al. 2025 , e.g.) . Recent studies on LLM-based debate and collaborative reasoning 

<a id="ev-0bdaba3552468ab5"></a>

- example-4-methods: [arxiv:2512.06196 / S4](https://arxiv.org/html/2512.06196v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[4\]
  - 발췌: ARCANE is a framework for learning structured, interpretable proxy utilities that align workers’ behavior with stakeholder preferences. ARCANE instantiates the abstract alignment setting from Section 3 by representing the manager’s coordination signal as a rubric : a decomposable, verifiable, and dynamically configurable approximation of the stakeholder’s true utility function U ∗ ​ ( y ∣ x ) U^{\*}(y\\mid x) .<br><br>The core idea is to have our manager M learn a rubric decomposer 𝔇 ϕ \\mathfrak{D}\_{\\ph

<a id="ev-874afc84dd2a0e1b"></a>

- example-4-results: [arxiv:2512.06196 / S5](https://arxiv.org/html/2512.06196v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[5\]
  - 발췌: Our experiments aim to answer three research questions:<br><br>RQ1 (Usefulness): Does guiding the worker team with learned rubrics increase the utility of their outputs versus unguided generation?<br><br>RQ2 (Faithfulness): Does the manager agent learn to rank candidates at test time in a manner consistent with the rankings computed from the stakeholder utility U ⋆ U^{\\star} ?<br><br>RQ3 (Interpretability & Efficiency): Are the rubrics generated by the manager agent compact, legible, and practical to verify?

<a id="ev-4deb7f8cc9cd8aea"></a>

- example-5-overview: [arxiv:2511.10687 / S1](https://arxiv.org/html/2511.10687v3)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[1\]
  - 발췌: Multi-Agent Systems (MAS) built from Large Language Models (LLMs) are emerging as a powerful paradigm for complex tasks. Agents in this context may be LLMs, ML models, or tools ( Ye et al., 2025 ; Wang et al., 2025b ; He and others, 2024 ; Yang et al., 2024 ; Team, 2025 ) , each taking structured inputs and producing outputs such as text, code, or tool calls. Unlike classical RL agents with compact, repetitive action spaces ( Bamford and Ovalle, 2021 ; Li et al., 2021a ; Hubert and others, 2021 

<a id="ev-0328298d2a7823ae"></a>

- example-5-limitations: [arxiv:2511.10687 / S6](https://arxiv.org/html/2511.10687v3)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[6\]
  - 발췌: Preventing credit hoarding. A key risk in cooperative multi-agent systems is that one agent might dominate the workflow, suppressing others to inflate its own marginal credit. Our framework mitigates this through two mechanisms. First, Shapley values enforce efficiency and symmetry, ensuring that duplicated or suppressive behavior yields little marginal gain. Second, message-level PRM supervision distributes an agent’s credit across its responses, so redundant or uninformative steps receive near

<a id="ev-976d0398ffd6e87b"></a>

- example-6-overview: [arxiv:2510.26352 / Sx1](https://arxiv.org/html/2510.26352v2)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[1\]
  - 발췌: Large language models (LLMs) have demonstrated remarkable capabilities across a wide range of natural language tasks, driven by advances in model scaling ( Zhao et al. 2025 ) . However, the monolithic approach of scaling a single, massive model faces challenges such as hallucination ( Maynez et al. 2020 ) and catastrophic forgetting ( Kirkpatrick et al. 2017 ) , limiting its ability to achieve robust performance across all domains. In response, a multi-agent approach based on LLMs has emerged as

<a id="ev-955e4bf3d85eccd8"></a>

- example-6-results: [arxiv:2510.26352 / Sx3](https://arxiv.org/html/2510.26352v2)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[3\]
  - 발췌: We conducted a series of experiments to validate our proposed method. First, we tested whether the language model graph could reveal latent model specializations by evaluating its ability to cluster models according to their known capabilities. Second, to validate the effectiveness of our team composition approach, we benchmarked the collective downstream task performance of teams constructed from the identified clusters against several baselines.

<a id="ev-79b0b45bc4e09c54"></a>

- example-7-overview: [arxiv:2511.05528 / S1](https://arxiv.org/html/2511.05528v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[1\]
  - 발췌: Large Language Models (LLMs) have proven adept at generation, problem-solving, translation, and summarization, performing well on various benchmarks. An LLM’s capability to learn from vast amounts of data allows it to handle complex tasks logically and fluently. Although LLMs have demonstrated competency in handling diverse tasks, their performance is often hurt by inaccuracies ( Zhang et al., 2023 ) .<br><br>Multi-agent systems (MAS) have been explored as a solution to combat this issue. These system

<a id="ev-c0ad4ed279111d71"></a>

- example-7-methods: [arxiv:2511.05528 / S3](https://arxiv.org/html/2511.05528v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[3\]
  - 발췌: In this work, we developed SMAGDi (Socratic Multi-Agent Interaction Graph Distillation), enabling efficient deliberation over multi-step problems by simulating domain-specific personas through SCoT (Socratic Chain-of-Thought) to mimic these analysis processes. These domain-specific personas differ from the traditional use of interchangeable agents, as each has a specific alignment and purpose ( Wei et al., 2023 ) .

<a id="ev-e9f41b2ba234165c"></a>

- example-7-limitations: [arxiv:2511.05528 / S7](https://arxiv.org/html/2511.05528v1)
  - 원문 위치: /html/body/div\[2\]/div\[2\]/article/section\[7\]
  - 발췌: Training Data Due to computational constraints, we did not train our models on the full auxiliary train split of MMLU. Further testing will be needed to confirm that SMAGDi will perform better than other models if trained on all data.<br><br>Large-Scale Setups Since SMAGDi was tested on lightweight models, we lack proof of its scalability to larger environments. In application, alternatives that provide similar results with minimal computational costs would prove to be more efficient.<br><br>Dynamic Weighti
