# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-06-07

### Added
- Initial public release of Deep Research Skill v2.0.0
- 6-phase research workflow: Task Analysis, Decomposition, Collection, Fact-Checking, Synthesis, Output
- Cost-first execution model with 4-tier tool hierarchy (native tools to premium APIs)
- Multi-agent orchestration with heartbeat protocol and checkpoint recovery
- Evidence-based reporting with mandatory citations and confidence scoring (1-5 scale)
- Anti-hallucination mandate with zero-tolerance fact-checking protocol
- Source Authority Framework with Tier S/A/B/C/D classification
- Progressive disclosure: summary → findings → details based on depth level
- Independent verification: cross-model and cross-source fact validation
- 4 research depth levels: Quick, Standard, Deep, Exhaustive
- 4 search routes: Wide Search, Focused Search, File-Only, File-Augmented
- 8 subtask types: SEARCH, EXTRACT, ANALYZE, COMPARE, SYNTHESIZE, VALIDATE, FORMAT, META
- Comprehensive tool matrix covering 50+ research tools with cost/quality ratings
- Fact-checking system with 3-agent pipeline (Verification, Comparison, Scoring)
- Output format templates for executive summary, deep report, competitive analysis, market research
- Legal bypass methods documentation (ETHICAL_ONLY scope)
- CAPTCHA handling module with 5-technique escalation ladder
- Agent monitoring protocol (AGENT.MD) with heartbeat, checkpoints, quality gates
- 18 reference documents with research on tools, APIs, and techniques
- Marketplace integration via `.claude-plugin/marketplace.json`
- Full documentation in Russian

### Architecture
- Lazy-loaded phase modules for optimal token efficiency
- Checkpoint recovery system — no progress loss on interruption
- Heartbeat protocol every 30 seconds
- Cost tracking and budget enforcement per phase
- Quality gates with PASS/WARN/FAIL metrics
- Error recovery with 3-attempt escalation

### Documentation
- SKILL.md — main skill entry point with activation triggers
- SKILL.master.md — complete master documentation
- AGENT.MD — multi-agent orchestration protocol
- LEGAL_METHODS.md — ethical legal bypass techniques
- CAPTCHA_MODULE.md — CAPTCHA handling strategies
- 18 reference documents in `references/` directory

### Research Coverage
- Jina AI Reader integration
- Bypass paywall techniques (ethical)
- ECC (European Commission) data sources
- Models.dev evaluation platform
- CAPTCHA solving landscape
- Academic skill research
- Skill marketplace analysis
- Browserbase cloud browser
- Prompt engineering master techniques

[2.0.0]: https://github.com/deep-research-skill/deep-research-skill/releases/tag/v2.0.0
