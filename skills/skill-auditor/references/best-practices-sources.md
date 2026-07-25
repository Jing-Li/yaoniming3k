# Best Practices Sources — Cited Frameworks & Data

## Academic Frameworks

### PEEM (Prompt Engineering Evaluation Metrics)
- **Source**: Hong et al., arxiv 2603.10477, Dongguk University, March 2026
- **Validation**: 7 benchmarks × 5 task models × 4 evaluator models
- **Key data**:
  - 9 evaluation axes: 3 prompt (Clarity/Structure, Linguistic Quality, Fairness) + 6 response (Accuracy, Coherence, Relevance, Objectivity, Clarity, Conciseness)
  - 1-5 Likert scale with natural language rationales
  - Spearman ρ≈0.97 correlation with conventional accuracy
  - Cross-evaluator rank correlation ρ=0.68-0.85
  - Zero-shot prompt rewriting improved accuracy up to 11.7 points
- **Applied to**: D1 (Clarity/Structure), D4 (Coherence), D5 (Linguistic Quality)

### PEARL (Rubric-Driven Multi-Metric Framework)
- **Source**: Anghel et al., MDPI Information 16(11):926, 2025. Cited 7 times.
- **Key contribution**: First framework combining multi-rubric scoring + explanation-aware metrics + robustness analysis + multi-LLM-evaluator analysis
- **Applied to**: Multi-expert review methodology, scoring consistency

---

## Industry Standards

### Anthropic Agent Skills (Official Design Principles)
- **Source**: Anthropic Engineering Blog, "Equipping agents for the real world with Agent Skills", December 2025
- **Key principles**:
  - Progressive Disclosure = core design principle (3-level loading: metadata → SKILL.md body → referenced files)
  - "Start with evaluation" — identify gaps first, build skills to address
  - "Structure for scale" — split when unwieldy, separate mutually exclusive paths
  - "Think from Claude's perspective" — monitor real usage, iterate
  - "Iterate with Claude" — capture successful approaches into reusable context
- **Applied to**: D2 (Progressive Disclosure), overall methodology

### Anthropic Complete Guide to Building Skills (33 pages)
- **Source**: "The Complete Guide to Building Skills for Claude", Anthropic, January 2026 (resources.anthropic.com)
- **Key contributions**:
  - Three skill categories: Content Generation, Multi-Step Workflows, MCP Enhancement
  - Description field best practices: specific verb + artifact + trigger phrases (200-400 chars)
  - Body writing: specific > abstract, error handling mandatory, conditional routing, iterative refinement
  - Testing methodology: Trigger Testing + Functional Testing + Comparative Testing
  - Advanced patterns: Sequential Workflows (validation gates), Cross-Service Orchestration, Iterative Refinement, Conditional Routing
- **Applied to**: D3 (description quality), D4 (workflow patterns), D6 (validation gates)

### SKILL.md Cross-Agent Compatibility Test
- **Source**: Agensi.io, "SKILL.md Cross-Agent Compatibility: Tested Across 6 Agents", May 2026
- **Test scope**: 10 skills × 6 agents (Claude Code, Codex CLI, Gemini CLI, Cursor, GitHub Copilot, OpenClaw)
- **Key data**:
  - 8/10 skills worked identically across all 6 agents
  - Universal fields: `name`, `description`
  - Widely supported: `when_to_use`, `argument-hint`
  - Agent-specific: `allowed-tools`, `context`, `agent`, `hooks`
  - Description quality = #1 factor for trigger reliability
  - Claude Code most reliable trigger; Copilot most conservative
  - Emoji headers reduce Gemini CLI section accuracy ~12%
- **Applied to**: D3 (Trigger Reliability), D5 (emoji decision)

### Termdock Agent Skills Guide 2026
- **Source**: Termdock.com, "Agent Skills Guide 2026: Build, Share & Secure", March 2026
- **Key guidelines**:
  - Keep SKILL.md under 500 lines (context window cost)
  - One skill, one verb (split when two trigger patterns)
  - Scripts for deterministic tasks
  - Progressive disclosure minimizes token usage
  - Description optimization is highest-leverage improvement
- **Ecosystem data**: 490K+ skills across 3 marketplaces (SkillsMP 400K+, Skills.sh 83K+, ClawHub ~10K+)
- **Applied to**: D2 (line count), D3 (description optimization)

### Superpowers Framework
- **Source**: Jesse Vincent, github.com/obra/superpowers, 89K+ GitHub stars (March 2026)
- **Key principle**: Enforcement > Suggestion
  - "Skills do not just suggest TDD. They refuse to write implementation code without tests."
  - "They do not just recommend planning. They halt and produce a plan before touching any files."
- **Structure**: 10+ core skills covering full development lifecycle
- **Accepted**: Anthropic Claude Code plugin marketplace, January 2026
- **Key patterns extracted** (see expert-skill-patterns.md §2):
  - Iron Law: "NO [ACTION] WITHOUT [PREREQUISITE] FIRST. [Consequence]. No exceptions."
  - Rigid/Flexible/Advisory enforcement classification
  - Process Chain: skill output = next skill input (interface contract)
  - Anti-Pattern Catalogue: reference file for common mistakes
- **Applied to**: D4 (process chain), D6 (Enforcement Strength)

### SkillzWave Grading Model
- **Source**: SkillzWave marketplace (skillzwave.com), grading system used for all Superpowers skills. Example: github.com/obra/superpowers/issues/202 (Dec 2025)
- **Model**: 5 pillars + modifiers = 100 points
  - Progressive Disclosure Architecture (30): Token Economy, Layered Structure, Reference Depth, Navigation Signals
  - Ease of Use (25): Metadata Quality, Discoverability, Terminology Consistency, Workflow Clarity
  - Spec Compliance (15): Frontmatter Validity, Name Conventions, Description Quality, Optional Fields
  - Writing Style (10): Voice & Tense, Objectivity, Conciseness
  - Utility (20): Problem Solving Power, Degrees of Freedom, Feedback Loops, Examples & Templates
  - Modifiers (±15): Penalties (xml_tags_in_metadata -5, first_second_person_description -2) / Bonuses (grep_friendly_structure +1, gerund_style_name +1)
- **Grade scale**: A (90-100) / B (80-89) / C (70-79) / D (60-69) / F (<60)
- **Key finding**: Even Superpowers' own meta-skill scored 68/100 (D) — emotional language, redundant content, missing examples
- **Applied to**: Cross-validation scoring, D1/D2/D3/D5/D6 sub-criteria

### Snyk ToxicSkills Study
- **Source**: Snyk, "ToxicSkills" research, February 5, 2026
- **Scope**: 3,984 skills scanned
- **Key data**:
  - 36.8% (1,467) had at least one security flaw
  - 13.4% (534) contained critical-level issues
  - 76 confirmed malicious payloads
  - 91% of malicious skills combined prompt injection + traditional malware
- **Attack vectors**: Shell execution, filesystem access, prompt injection
- **Mitigation**: allowed-tools restrictions, file ownership declaration, source verification
- **Applied to**: D7 (Safety & Boundaries)

---

## Documentation Frameworks

### Diátaxis (Documentation System)
- **Source**: Daniele Procida, diataxis.fr
- **Four types**: Tutorials, How-to Guides, Reference, Explanation
- **Application**: SKILL.md = How-to Guide (task-oriented); reference.md = Reference (information-oriented)
- **Applied to**: Expert Review Round 2 (documentation architecture)

### ETH Zurich Context Engineering Research
- **Source**: Referenced in Termdock Guide 2026
- **Finding**: Overly detailed context files degrade agent performance
- **Implication**: CLAUDE.md/AGENTS.md should be 200-500 words; task-specific content belongs in skills
- **Applied to**: D2 (progressive disclosure rationale)

---

## How to Cite in Audit Reports

When reporting a finding, cite the source:

```
- **Best Practice**: PEEM D1 Clarity/Structure — "well-organized presentation ensuring logical coherence" (Hong et al., 2026)
- **Best Practice**: Anthropic Progressive Disclosure — "load information only as needed" (Anthropic, 2025)
- **Best Practice**: Agensi Cross-Agent Test — "plain markdown instructions work everywhere" (Agensi, 2026)
- **Best Practice**: Superpowers Enforcement — "refuse, don't suggest" (Vincent, 2026)
- **Best Practice**: Snyk ToxicSkills — "explicit tool restrictions mitigate 13.4% critical flaws" (Snyk, 2026)
```
