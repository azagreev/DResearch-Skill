# AGENT.MD — Agent Monitoring Protocol

## Deep Research Skill | Multi-Agent Orchestration Layer

> **Version:** 1.5.0
> **Scope:** Heartbeat, checkpoints, quality gates, cost tracking, error recovery, multi-agent coordination
> **Philosophy:** *Every agent reports, every gate validates, every failure recovers*
> **Status:** Testing release

---

## 1. Heartbeat Protocol

### 1.1 Формат heartbeat-файла

Каждый агент (Research Agent, FactCheck Agent, Format Agent) пишет heartbeat-файл с фиксированной частотой. Heartbeat — единственный источник истины о состоянии агента.

**Путь:** `./research_output/heartbeats/heartbeat_YYYYMMDD_HHMMSS_<agent_role>.md`

**Формат:**

```markdown
# Heartbeat: <timestamp>
## Agent: <role>
## Task: <task_id>

### Elapsed: <HH:MM>
### Current checkpoint: <cp_id | null>
### Active subtasks: [<s_ids>]
### Completed: <N>/<M> subtasks (<pct>%)

### Progress This Window
- <subtask_id> (<type>): <pct>% complete, <details>
- <subtask_id> (<type>): Status update

### Metrics Snapshot
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Source Coverage | <pct>% | >= 60% | [PASS/WARN/FAIL] |
| Topic Coverage | <pct>% | >= 75% | [PASS/WARN/FAIL] |
| Recency | <pct>% | >= 60% | [PASS/WARN/FAIL] |
| Fact Density | <N>/page | >= 10 | [PASS/WARN/FAIL] |
| CI Score | <N> | >= 70 | [PASS/WARN/FAIL] |

### Issues
- [SEVERITY] <description> | Mitigation: <action> | ETA: <time>

### Cost This Window
| Phase | Calls | Tokens | Cost USD |
|-------|-------|--------|----------|
| <phase> | <N> | <N> | $X.XX |

### ETA
- Next checkpoint: <HH:MM>
- Final delivery: <HH:MM>
- Confidence: <HIGH/MEDIUM/LOW>
```

### 1.2 Частота heartbeat

| Длительность задачи | Интервал heartbeat |
|---------------------|-------------------|
| < 1 час | Каждые 10 минут |
| 1-4 часа | Каждые 2-3 минуты |
| 4-8 часов | Каждые 2 минуты |
| 8-24 часа | Каждую минуту |
| > 24 часа | Каждые 30 секунд + при каждом checkpoint |

**Rule:** Heartbeat пишется также при каждой смене этапа, независимо от интервала.

### 1.3 Обязательные точки heartbeat

| Точка | Условие | Обязательные поля |
|-------|---------|-------------------|
| **Start** | Начало task | `task_id`, `agent_role`, `start_time`, `planned_checkpoints[]`, `budget_usd` |
| **25%** | `progress_pct >= 25` | `metrics_snapshot`, `blockers[]`, `cost_so_far` |
| **50%** | `progress_pct >= 50` | `confidence_check`, `quality_gate_status`, `midpoint_assessment` |
| **75%** | `progress_pct >= 75` | `completeness_check`, `remaining_risks`, `eta_final` |
| **Stage Change** | Переход cp_N → cp_N+1 | `from_checkpoint`, `to_checkpoint`, `gate_result`, `artifacts_produced[]` |
| **Completion** | 100% done | `final_quality_score`, `total_cost`, `audit_trail_path`, `delivery_artifacts[]` |

### 1.4 Code Example: Python Heartbeat Generator

```python
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from dataclasses import dataclass, asdict

@dataclass
class Heartbeat:
    timestamp: str
    agent_role: Literal["research", "factcheck", "format", "meta"]
    task_id: str
    elapsed_min: int
    current_checkpoint: str | None
    active_subtasks: list[str]
    completed_count: int
    total_count: int
    progress_pct: float
    metrics: dict
    issues: list[dict]
    cost_window_usd: float
    cost_total_usd: float
    eta_next_checkpoint_min: int | None
    eta_final_min: int | None
    confidence: Literal["HIGH", "MEDIUM", "LOW"]

    @property
    def completion_pct(self) -> float:
        return round(self.completed_count / max(self.total_count, 1) * 100, 1)

    def to_markdown(self) -> str:
        md = f"""# Heartbeat: {self.timestamp}
## Agent: {self.agent_role}
## Task: {self.task_id}

### Elapsed: {self.elapsed_min // 60}h {self.elapsed_min % 60}m
### Current checkpoint: {self.current_checkpoint or 'null'}
### Active subtasks: {json.dumps(self.active_subtasks)}
### Completed: {self.completed_count}/{self.total_count} ({self.completion_pct}%)

### Metrics Snapshot
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
"""
        for metric_name, metric_data in self.metrics.items():
            md += f"| {metric_name} | {metric_data['value']} | {metric_data['threshold']} | {metric_data['status']} |\n"

        md += "\n### Issues\n"
        if self.issues:
            for issue in self.issues:
                md += f"- [{issue['severity']}] {issue['description']} | Mitigation: {issue['mitigation']} | ETA: {issue['eta']}\n"
        else:
            md += "- None\n"

        md += f"\n### Cost\n- This window: ${self.cost_window_usd:.2f}\n- Total: ${self.cost_total_usd:.2f}\n"
        md += f"\n### ETA\n- Next checkpoint: {self.eta_next_checkpoint_min or 'N/A'} min\n"
        md += f"- Final delivery: {self.eta_final_min or 'N/A'} min\n"
        md += f"- Confidence: {self.confidence}\n"
        return md

    def write(self, base_dir: str | None = None) -> str:
        # Абсолютный путь (.resolve()) вместо относительного "./": относительный резолвится
        # от cwd и на Windows/Claude Code может уехать не туда — тогда при recovery heartbeat
        # молча не находится. Корень прогона фиксируется один раз на старте сессии.
        root = (Path(base_dir) if base_dir else Path.cwd() / "research_output" / "heartbeats").resolve()
        root.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"{root}/heartbeat_{ts}_{self.agent_role}.md"
        with open(path, "w") as f:
            f.write(self.to_markdown())
        return path


# ── Usage ──
hb = Heartbeat(
    timestamp=datetime.now(timezone.utc).isoformat(),
    agent_role="research",
    task_id="drs_ai-market_20241219",
    elapsed_min=135,
    current_checkpoint="cp_02_processed",
    active_subtasks=["s6", "s7"],
    completed_count=5,
    total_count=9,
    progress_pct=55.5,
    metrics={
        "Source Coverage": {"value": "72%", "threshold": ">= 60%", "status": "PASS"},
        "Topic Coverage": {"value": "85%", "threshold": ">= 75%", "status": "PASS"},
        "CI Score": {"value": "74", "threshold": ">= 70", "status": "PASS"}
    },
    issues=[{
        "severity": "WARN",
        "description": "Player Z pricing page requires CloakBrowser (WAF)",
        "mitigation": "Retry with CloakBrowser configured",
        "eta": "+15 min"
    }],
    cost_window_usd=0.45,
    cost_total_usd=1.23,
    eta_next_checkpoint_min=35,
    eta_final_min=90,
    confidence="HIGH"
)
heartbeat_path = hb.write()
print(f"Heartbeat written: {heartbeat_path}")
```

---

## 2. Checkpoint System

### 2.1 5 Checkpoints Pipeline

```
cp_01_raw ──────▶ cp_02_processed ──────▶ cp_03_draft ──────▶ cp_04_reviewed ──────▶ final
   │                    │                     │                      │                  │
   ▼                    ▼                     ▼                      ▼                  ▼
"Raw data          "Data structured    "Analysis/         "Fact-checked,      "Deliverable
 collected"        & validated"        synthesis draft"    reviewed"           ready"
```

| Checkpoint | Когда создаётся | Gate | Ключевой критерий перехода |
|------------|----------------|------|---------------------------|
| `cp_01_raw` | Сбор сырых данных завершён | Gate 1 Post-Collection | ≥ N sources, ≥ 4 типа, ≥ 60% Tier B+, 0 blocking errors |
| `cp_02_processed` | Очистка, дедупликация, структурирование завершены | Gate 2 Post-Processing | < 5% дубликатов, quality ≥ 8/10, 0 PII leaks, < 10% потерь |
| `cp_03_draft` | Анализ/синтез завершён | Gate 3 Post-Analysis | 100% P0 questions answered, каждый finding ≥ 3 data points |
| `cp_04_reviewed` | Проверка и редактирование завершены | Gate 4 Post-Synthesis | 100% claims sourced, все scored, ≥ 2 альтернативы, 0 contradictions |
| `final` | Финальный отчёт сформирован | Gate 5 Final Output | CI ≥ 70, все citations present, format compliant |

### 2.2 Формат каждого checkpoint

```markdown
# Checkpoint: <cp_id>
## Metadata
- parent_checkpoint: <cp_prev | null>
- task_id: <uuid>
- created_at: <ISO 8601>
- duration_since_start: <HH:MM>
- subtasks_completed: [<s_ids>]
- subtasks_pending: [<s_ids>]
- gate_result: <PASS | FAIL | RETRY>

## Status
- overall: <ON_TRACK | AT_RISK | BLOCKED | COMPLETED>
- completion_pct: <0-100>
- quality_score: <0.0-1.0>
- confidence_trend: <↑ → ↓>

## Artifacts
| ID | Type | Description | Size | Location | Checksum |
|----|------|-------------|------|----------|----------|
| a1 | SourceList | ... | <size> | <path> | <sha256> |

## Key Findings
1. <finding with evidence_ref>
2. <finding with evidence_ref>

## Blockers & Risks
- [SEVERITY] <description> | Owner: <agent> | Resolution: <action>

## Recovery Info
- resume_from: <subtask_id>
- required_context: [<artifact_refs>]
- estimated_remaining: <HH:MM>
- rollback_to: <cp_prev>  # если gate FAIL
```

### 2.3 Naming Convention

```
Формат:  cp_<NN>_<descriptor>[_<task_id>]
         heartbeat_YYYYMMDD_HHMMSS_<agent_role>.md
         gate<N>_<result>_YYYYMMD_HHMMSS.log

Где:
  <NN>          — двузначный номер (01-99)
  <descriptor>  — семантическое название
  <task_id>     — опциональный суффикс для multi-task

Стандартные descriptors:
  cp_01_raw        — Сырые собранные данные
  cp_02_processed  — Обработанные/структурированные данные
  cp_03_draft      — Черновик анализа/синтеза
  cp_04_reviewed   — Проверенный и отредактированный результат
  final            — Финальный артефакт

Примеры:
  cp_01_raw_drs_2024q3_ai-market.md
  cp_02_processed_drs_2024q3_ai-market.md
  heartbeat_20241219_143000_research.md
  gate1_pass_20241219_121500.log
```

### 2.4 Recovery Protocol (6 шагов)

```
PROTOCOL: RESUME_FROM_CHECKPOINT

INPUT: checkpoint_id

STEP 1: READ checkpoint file
  → Read ./checkpoints/<cp_id>.md

STEP 2: VALIDATE integrity
  → Check all referenced artifacts exist
  → Verify artifact checksums match metadata
  → IF mismatch → flag CORRUPTED, escalate to human

STEP 3: LOAD context
  → Read parent checkpoint chain (all prior cp_XX)
  → Load required artifacts into working memory
  → Extract subtasks_pending from checkpoint

STEP 4: REPLAN if needed
  → IF checkpoint.age > 24h → re-evaluate SEARCH freshness
  → IF new information available → META subtask to adjust plan
  → ELSE → continue with existing plan

STEP 5: RESUME execution
  → Start from first subtasks_pending
  → Update checkpoint with new status every 15 min

STEP 6: ON failure
  → IF subtask fails → create <cp_id>_blocked with reason
  → Attempt retry with modified parameters (max 3 retries)
  → IF retry fails → escalate to human with options

OUTPUT: Execution continues from checkpoint
```

#### Recovery Code Template

```yaml
# recovery_manifest.yaml
resume_from: cp_02_processed
task_id: comp_landscape_001

context_load:
  checkpoints:
    - cp_01_raw
    - cp_02_processed
  artifacts:
    - sources_index.json
    - validated_data.json
    - data_quality_report.md

execution_plan:
  resume_at_subtask: s6
  pending: [s6, s7, s8, s9]
  adjustments:
    - subtask: s6
      reason: "Resume normal flow"

validation:
  artifacts_verified: true
  checksum_match: true
  freshness_check:
    max_age_hours: 24
    status: FRESH  # FRESH | STALE | EXPIRED
  replan_required: false

fallback:
  if_validation_fails: "Request human review"
  if_data_stale: "Re-run SEARCH for updated data"
  if_corrupted: "Restart from cp_01_raw"
```

---

## 3. Quality Gate Logging

### 3.1 Gate Architecture

**Enforcement status (authoritative — reflects actual engine code in `engine/state.py`):**

Of the 5 prose-documented gates, exactly **2 are HARD-ENFORCED in code** by `state.gate_blocks_transition`; the other 3 are advisory (checked only in prose / heartbeat metrics, not by the engine):

| Gate | Prose name | Code-enforced? | Enforcement rule |
|------|-----------|----------------|-----------------|
| Gate 1 | Post-Collect | **YES** | `sources_screened > 0` required for `target_phase >= 2`. Blocks transition if snapshot has no screened sources. |
| Gate 2 | Post-Process | advisory only | Not checked by `gate_blocks_transition`; validated by prose + heartbeat metrics. |
| Gate 3 | Post-Analysis | advisory only | Not checked by `gate_blocks_transition`; validated by prose + heartbeat metrics. |
| Gate 4 | Post-Synthesis | advisory only | Not checked by `gate_blocks_transition`; validated by prose + heartbeat metrics. |
| Gate 5 | Final Output | **YES** | `citations_verified == True` required for `target_phase >= 5`. Blocks synthesis/output if no claim has been verified. |

`engine gate` CLI verb exposes all three oracles in one call: `blocks_transition` (from `gate_blocks_transition`), `should_stop` (budget/done/stalled), and `should_compact` (named compaction boundary). `run_pipeline` consults `gate_blocks_transition` automatically using `next_phase` (not a hardcoded phase number) when assembling the snapshot.

```
Gate 1 (Post-Collect)    Gate 2 (Post-Process)   Gate 3 (Post-Analyze)   Gate 4 (Post-Synth)    Gate 5 (Final Output)
    │                          │                        │                      │                       │
    ▼                          ▼                        ▼                      ▼                       ▼
 Raw Data ──▶            Clean Data ──▶           Insights ──▶         Conclusions ──▶        Deliverable
 CHECK:                     CHECK:                   CHECK:                 CHECK:                  CHECK:
 - sources ≥ N [CODE]      - dedup < 5%            - 100% P0 Qs          - 100% claims          - CI ≥ 70
 - diversity ≥ 4 types     - quality ≥ 8/10          answered               sourced              - all citations
 - tier ≥ 60% B+           - 0 PII leaks           - findings ≥ 3         - all scored             present [CODE]
 - freshness ≥ 60%         - losses < 10%            data points          - ≥ 2 alternatives      - format compliant
 - 0 blocking errors       - formats normalized      - stats checked        - 0 contradictions      - exec summary OK
[CODE] = hard-enforced by state.gate_blocks_transition; others are advisory prose checks.
```

### 3.2 Log Format для каждого gate

```yaml
gate_log:
  gate_id: "G<N>_<name>"
  timestamp: "2024-12-19T14:32:00Z"
  task_id: "drs_..."
  checkpoint_id: "cp_0N_..."

  status: "PASS" | "FAIL" | "RETRY"
  attempt: 1 | 2 | 3

  checks:
    - check_id: "<gate>.<N>"
      name: "<human readable>"
      expected: "<threshold>"
      actual: "<measured>"
      result: "PASS" | "FAIL"
      severity: "BLOCKING" | "DEGRADED" | "COSMETIC"

  metrics:
    source_coverage_pct: <float>
    topic_coverage_pct: <float>
    recency_pct: <float>
    fact_density_per_page: <float>
    completeness_index: <float>

  cost:
    phase_cost_usd: <float>
    accumulated_cost_usd: <float>
    tokens_used: <int>
    api_calls: <int>

  actions:
    - action: "PROCEED" | "REWORK" | "RE_SEARCH" | "ESCALATE"
      target: "<subtask_or_phase>"
      reason: "<why>"

  next_checkpoint: "cp_0<N+1>_..." | null
  eta_after_recovery: "<HH:MM>" | null
```

### 3.3 Pass / Fail / Retry Logging

| Статус | Условие | Логирование | Действие |
|--------|---------|-------------|----------|
| **PASS** | Все checks ≥ threshold | `status: PASS`, `action: PROCEED` | Переход к следующему checkpoint |
| **FAIL** | Любой BLOCKING check не пройден | `status: FAIL`, `severity: BLOCKING`, RCA запускается | RCA + re-work/re-search |
| **RETRY** | FAIL + `attempt < max_retries` | `status: RETRY`, `attempt: N+1`, модификация параметров | Повтор с изменёнными параметрами |

**Gate Escalation Matrix:**

| Gate | Max Retries | Escalation Trigger | Escalation Action |
|------|-------------|--------------------|--------------------|
| Gate 1 | 3 | После 3-х fails | Human-in-the-loop: смена инструментов/scope |
| Gate 2 | 2 | После 2-х fails | Human: review data pipeline |
| Gate 3 | 3 | После 3-х fails | Human: revise analytical framework |
| Gate 4 | 2 | После 2-х fails | Human: restructuring |
| Gate 5 | 2 | После 2-х fails | Human: final review + override |

### 3.4 Cost Tracking per Gate & Cache Metrics

> **Implementation note:** `GateCostTracker` and `RunTrace` are now implemented in `engine/telemetry.py` (Phase 11, AC11-4); the pseudocode below is kept for reference.

#### Метрики кэширования (Phase 13, engine/telemetry.py)

Начиная с Phase 13 движок фиксирует сигналы кэша prompt-prefix'а в каждом событии `RunTrace` и предоставляет три чистые вспомогательные функции. Все они детерминированы: не читают системных часов, не используют рандомизацию.

**Разреженные поля RunTrace.append (добавляются, только если не None):**

```python
RunTrace.append(
    event,
    *,
    # ...существующие поля без изменений...
    prompt_bundle_hash:  str | None = None,   # bundle_hash(system+tool schemas)
    tool_bundle_hash:    str | None = None,   # bundle_hash(сериализованных tool-схем)
    cache_read_tokens:   int | None = None,   # токены, прочитанные из кэша хоста
    cache_write_tokens:  int | None = None,   # токены, записанные в кэш хоста
    cached_tokens:       int | None = None,   # суммарный cached_tokens из ответа API
) -> None
```

Все пять полей **разреженные**: если хост не вернул данные — поле отсутствует в записи события (не пишется `null`). Уже имеющиеся call-сайты `RunTrace.append` остаются без изменений.

**Вспомогательные функции:**

| Функция | Сигнатура | Семантика |
|---------|-----------|-----------|
| `bundle_hash` | `bundle_hash(text: str) -> str` | sha256-hex от `text.encode("utf-8")`. Детектор дрейфа prefix'а: если хэш изменился между ходами — кэш инвалидируется. Чистая, детерминированная. |
| `cache_hit_rate` | `cache_hit_rate(read, write) -> Optional[float]` | `read / (read + write)`. Возвращает `None`, если `read` или `write` равны `None`, либо `(read + write) == 0`. Чистая. Захватывается в RunTrace через `cache_read_tokens` / `cache_write_tokens`. |
| `cache_fragmentation` | `cache_fragmentation(history, *, threshold: int = 3) -> Optional[str]` | Принимает последовательность `cached_tokens` по ходам (int или None). Возвращает `"WARNING"`, если **последние `threshold` подряд идущих** записей — все точно `0`; иначе `None`. Запись `None` (хост не отчитался) прерывает нулевую серию (неизвестно ≠ фрагментировано). Менее чем `threshold` записей → `None`. Чистая, детерминированная; история передаётся аргументом. |

**Интерпретация сигналов:**

- `bundle_hash` отличается от предыдущего хода → prefix изменился → cache miss гарантирован на следующем ходу.
- `cache_hit_rate` → целевой диапазон ~0.8–0.95 при стабильном prefix'е; падение ниже 0.5 на нескольких ходах подряд указывает на дрейф.
- `cache_fragmentation` = `"WARNING"` → последние три хода показали `cached_tokens == 0`; вероятна инвалидация кэша или смена volatile-зоны в prompt'е.

```python
class GateCostTracker:
    """Отслеживание стоимости на уровне каждого gate."""

    BUDGET_ALLOCATION = {
        'gate_1_collection': 0.15,    # 15% бюджета
        'gate_2_processing': 0.10,    # 10% бюджета
        'gate_3_analysis': 0.25,      # 25% бюджета
        'gate_4_synthesis': 0.20,     # 20% бюджета
        'gate_5_final': 0.10,         # 10% бюджета
        'factcheck_agent': 0.15,      # 15% бюджета
        'contingency': 0.05,          # 5% резерв
    }

    def __init__(self, total_budget_usd: float):
        self.total = total_budget_usd
        self.spent = {k: 0.0 for k in self.BUDGET_ALLOCATION}
        self.retries_cost = 0.0

    def spend(self, gate: str, amount_usd: float) -> dict:
        self.spent[gate] += amount_usd
        allocated = self.total * self.BUDGET_ALLOCATION[gate]
        remaining = allocated - self.spent[gate]
        pct_used = self.spent[gate] / allocated * 100

        alert = None
        if pct_used >= 100:
            alert = "BUDGET_EXHAUSTED"
        elif pct_used >= 90:
            alert = "BUDGET_CRITICAL"
        elif pct_used >= 75:
            alert = "BUDGET_WARNING"

        return {
            "gate": gate,
            "spent": round(self.spent[gate], 2),
            "allocated": round(allocated, 2),
            "remaining": round(remaining, 2),
            "pct_used": round(pct_used, 1),
            "alert": alert,
            "total_spent": round(sum(self.spent.values()), 2),
            "total_remaining": round(self.total - sum(self.spent.values()), 2)
        }

    def log_gate_result(self, gate: str, status: str) -> str:
        summary = self.spend(gate, 0)  # readonly snapshot
        log_line = (
            f"[GATE-COST] {datetime.now(timezone.utc).isoformat()} | "
            f"{gate}={status} | "
            f"${summary['spent']:.2f}/${summary['allocated']:.2f} "
            f"({summary['pct_used']:.0f}%) | "
            f"alert={summary['alert']}"
        )
        return log_line
```

### 3.5 Authority Scoring: Breakdown (Phase 14; VETO removed in v1.5)

Phase 14 extended the scoring pipeline (`engine/score.py`) with an auditable per-source breakdown, reflected in every scored `Source.scores` object and serialized into the checkpoint `state` block.

#### Anti-fit VETO layer — removed in v1.5

Phase 14 also shipped an anti-fit veto (`disqualify` + `VetoRules` / `DEFAULT_VETO`) that forced matching sources to `composite = 0.0` / `tier = D`. It was **removed in v1.5** as inert — its seed rules matched only a few `.example` test hosts and two self-declaring phrases, moving no DRACO score and no trust metric (invariant #10 «shipped ≠ valuable»). `score_source` no longer accepts a `VetoRules` argument; prompt-injection defense is provided by the ingest trust-fence (Phase 8), not the veto. The `source.scores.disqualifiers` field is retained for checkpoint back-compat and is now always empty (old checkpoints with legacy reasons still round-trip).

#### Score breakdown

Every scored source carries `source.scores.breakdown`: an ordered list of `[label, contribution]` pairs where `contribution = weight × component_value`. The five terms are:

```
[["authority",     authority    * 0.30],
 ["recency",       recency      * 0.25],
 ["independence",  independence * 0.20],
 ["traceability",  traceability * 0.15],
 ["corroboration", corroboration * 0.10]]
```

The contributions sum to `composite`. Unscored components (value `None`) contribute 0.0. The breakdown is generated from a single `_BREAKDOWN_TERMS` constant shared with `composite_score`, so the two can never diverge.

**Checkpoint version "1.2":** `ScoreComponents` gained `breakdown` and `disqualifiers` in this version. Both default gracefully (`[]`) in `_scores_from`, so v1.0 and v1.1 checkpoints load without migration and the version is simply re-stamped to "1.2" on save.

**Report surface.** The Источники / Sources section of the rendered report exposes each source's `composite`, `tier`, `breakdown` trace, and (when non-empty) `disqualifiers`, giving the reader a complete audit trail from raw components to final tier assignment.

---

## 4. FactCheck Agent Protocol

### 4.1 Архитектура FCA

```
┌──────────────┐      ┌──────────────────┐      ┌──────────────┐
│   Research   │raw   │  FactCheck Agent │rated │   Final      │
│    Agent     │─────▶│   (FCA)          │─────▶│   Output     │
│              │findgs│  Independent     │findgs│  Formatter   │
└──────────────┘      │  Validator       │      └──────────────┘
       ▲              └──────────────────┘             │
       └───────────────────────────────────────────────┘
                    Feedback Loop (max 3 iterations)
```

**Ключевой принцип:** FCA — независимый агент с правом вето. Если Research Agent утверждает X, а источники говорят Y — FCA выбирает Y.

### 4.2 FCA Heartbeat (отдельный от основного)

FCA пишет собственный heartbeat-файл с тем же адаптивным интервалом, что и основной агент (см. §1.2), независимо от Research Agent.

```markdown
# Heartbeat: <timestamp>
## Agent: factcheck
## Task: <task_id>
## Parent Research Task: <research_task_id>

### FCA Stage: <STAGE_0-8>
### Current checkpoint: <fca_checkpoint>
### Claims processed: <N>/<M>

### Verification Progress
| Category | Count | % |
|----------|-------|---|
| VERIFIED | <N> | <pct> |
| FALSE | <N> | <pct> |
| OUTDATED | <N> | <pct> |
| INCOMPLETE | <N> | <pct> |
| PERSPECTIVE | <N> | <pct> |
| UNCERTAIN | <N> | <pct> |

### Quality Metrics
- Verification Coverage: <pct>% (threshold: ≥ 75%)
- Source Diversity Index: <N> types
- Avg Source Quality: <0.XX>
- False Positive Rate: <pct>% (threshold: < 3%)

### FCA Cost
- This batch: $<cost>
- Per-claim avg: $<cost>
- Remaining budget: $<cost>

### Alerts
- [ ] Critical FALSE count > 20%
- [ ] Coverage < 75%
- [ ] Source stuck > 30 sec
```

### 4.3 Verification Log Format

```yaml
verification_record:
  claim_id: "FC-2024-001-007"
  original_claim: "Компания X выручила $50M в 2023 году"
  claim_type: "numerical / absolute value"
  stakes: "high" | "medium" | "low"

  sources:
    - source_id: "SRC-001"
      url: "https://sec.gov/Archives/.../10-k.htm"
      title: "Annual Report on Form 10-K"
      publisher: "SEC EDGAR"
      date: "2024-03-15"
      quality_score: 0.95
      quote: "Total revenue for fiscal year 2023 was $50.2 million"
      relevance: "directly confirms"

    - source_id: "SRC-002"
      url: "https://reuters.com/..."
      title: "X Corp Reports Annual Results"
      publisher: "Reuters"
      date: "2024-03-15"
      quality_score: 0.88
      quote: "The company posted revenue of $50.2 million"
      relevance: "cross-confirms"

  category: "VERIFIED" | "FALSE" | "OUTDATED" | "INCOMPLETE" | "PERSPECTIVE" | "UNCERTAIN"
  confidence: 0.92
  applied_strategies: ["primary", "cross-reference", "quantitative"]
  bias_score: 0.0
  context_flags: []

  verified_at: "2024-12-19T10:30:00Z"
  verified_by: "factcheck-agent-v1.0"
  cost_usd: 0.15
```

### 4.4 Category Assignment Logging

| Категория | Цвет | Частота | Действие |
|-----------|------|---------|----------|
| **VERIFIED** | Зелёный | 55-70% | Включается без изменений |
| **FALSE** | Красный | 5-15% | Исключается, Research Agent уведомляется |
| **OUTDATED** | Оранжевый | 5-12% | Помечается с актуальными данными |
| **INCOMPLETE** | Жёлтый | 10-20% | Дополняется контекстом |
| **PERSPECTIVE** | Фиолетовый | 8-18% | Переформулируется как "по мнению..." |
| **UNCERTAIN** | Серый | 3-10% | Помечается "не подтверждено" |

```python
def log_category_assignment(claim_id: str, category: str, 
                            confidence: float, evidence: list) -> str:
    """Форматирование лога присвоения категории."""
    emoji = {
        "VERIFIED": "✅", "FALSE": "❌", "OUTDATED": "⏰",
        "INCOMPLETE": "⚠️", "PERSPECTIVE": "🔮", "UNCERTAIN": "❓"
    }
    ts = datetime.now(timezone.utc).isoformat()
    log = (
        f"[FCA-CATEGORY] {ts} | claim={claim_id} | "
        f"category={emoji.get(category, '?')} {category} | "
        f"confidence={confidence:.2f} | "
        f"strategies={','.join(evidence)}"
    )
    return log
```

### 4.5 Escalation Triggers для FCA

| Trigger | Условие | Действие | Приоритет |
|---------|---------|----------|-----------|
| **CRITICAL_FALSE_RATE** | FALSE > 20% всех проверенных | BLOCK выдачи, запрос пересмотра Research Agent | P0 |
| **LOW_COVERAGE** | Verification Coverage < 75% | ESCALATE на ручную проверку | P1 |
| **SOURCE_TIMEOUT** | Источник недоступен > 30 сек | FAILOVER на альтернативный + LOG timeout | P1 |
| **STRATEGY_CONFLICT** | Несогласованность между стратегиями | DEEP_DIVE + CONFLICT_RESOLUTION по tie-breaking rules | P2 |
| **BUDGET_BATCH_EXHAUSTED** | Стоимость батча > $10 | STOP + human review | P1 |

**Tie-Breaking Rules при конфликте:**
1. Primary beats secondary (первоисточник > вторичный)
2. Fresh beats stale (свежие данные > устаревшие)
3. Quantitative beats qualitative (цифры > интерпретации)
4. Multiple beats single (множественные источники > одиночный)
5. Transparent beats opaque (прозрачная методология > неизвестная)

### 4.6 FCA Checkpoints

```
STAGE 0: ROUTING        → stakes-оценка
    │
STAGE 1: EXTRACTION     → fact_extraction_complete
    │
STAGE 2: CLASSIFICATION → (inline, no checkpoint)
    │
STAGE 3-4: SEARCH/EVAL  → source_evaluation_complete
    │
STAGE 5: CATEGORIZATION → categorization_complete
    │
STAGE 6: DOCUMENTATION  → (inline, no checkpoint)
    │
STAGE 7: REPORT         → final_report_ready
    │
STAGE 8: FEEDBACK       → (inline, no checkpoint)
```

---

## 5. Cost Tracking

### 5.1 Budget Allocation per Phase

```
Total Research Budget: $B

Allocation:
  Gate 1 (Collection)    ████░░░░░░  15%
  Gate 2 (Processing)    ██░░░░░░░░  10%
  Gate 3 (Analysis)      ██████░░░░  25%
  Gate 4 (Synthesis)     █████░░░░░  20%
  Gate 5 (Final Output)  ██░░░░░░░░  10%
  FCA (Verification)     ████░░░░░░  15%
  ─────────────────────────────────────
  Contingency            █░░░░░░░░░   5% (emergency reserve)
```

| Phase | Бюджет | Жёсткий лимит | Действие при превышении |
|-------|--------|---------------|------------------------|
| Gate 1 | 15% | 20% | WARN → STOP → re-scope |
| Gate 2 | 10% | 15% | WARN → optimize pipeline |
| Gate 3 | 25% | 30% | WARN → simplify analysis |
| Gate 4 | 20% | 25% | WARN → reduce depth |
| Gate 5 | 10% | 15% | WARN → manual formatting |
| FCA | 15% | 20% | WARN → sample checking |
| Contingency | 5% | 5% | Emergency only, human approval |

### 5.2 Real-Time Cost Tracking

```python
@dataclass
class CostSnapshot:
    timestamp: str
    task_id: str
    phase: str

    # Current window
    calls_this_window: int
    tokens_this_window: int
    cost_this_window_usd: float

    # Cumulative
    total_calls: int
    total_tokens: int
    total_cost_usd: float

    # Budget
    budget_allocated_usd: float
    budget_spent_usd: float
    budget_remaining_usd: float
    pct_used: float

    # Alerts
    alerts: list[str]  # BUDGET_WARNING | BUDGET_CRITICAL | BUDGET_EXHAUSTED

    def check_alerts(self) -> list[str]:
        alerts = []
        if self.pct_used >= 100:
            alerts.append("BUDGET_EXHAUSTED")
        elif self.pct_used >= 90:
            alerts.append("BUDGET_CRITICAL")
        elif self.pct_used >= 75:
            alerts.append("BUDGET_WARNING")
        return alerts

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


class RealTimeCostTracker:
    """Singleton трекер для real-time отслеживания затрат."""

    def __init__(self, task_id: str, total_budget: float):
        self.task_id = task_id
        self.total_budget = total_budget
        self.spent = 0.0
        self.history: list[CostSnapshot] = []
        self.phase_allocations = GateCostTracker.BUDGET_ALLOCATION

    def record_spend(self, phase: str, calls: int, tokens: int, cost: float):
        self.spent += cost
        snapshot = CostSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            task_id=self.task_id,
            phase=phase,
            calls_this_window=calls,
            tokens_this_window=tokens,
            cost_this_window_usd=cost,
            total_calls=sum(h.calls_this_window for h in self.history) + calls,
            total_tokens=sum(h.tokens_this_window for h in self.history) + tokens,
            total_cost_usd=self.spent,
            budget_allocated_usd=self.total_budget,
            budget_spent_usd=self.spent,
            budget_remaining_usd=self.total_budget - self.spent,
            pct_used=round(self.spent / self.total_budget * 100, 2),
            alerts=[]
        )
        snapshot.alerts = snapshot.check_alerts()
        self.history.append(snapshot)
        return snapshot

    def get_current_status(self) -> CostSnapshot:
        return self.history[-1] if self.history else None

    def export_timeseries(self, path: str):
        """Экспорт истории затрат для анализа."""
        with open(path, 'w') as f:
            for snap in self.history:
                f.write(f"{snap.timestamp},{snap.phase},{snap.cost_this_window_usd},"
                       f"{snap.total_cost_usd},{snap.pct_used}\n")
```

### 5.3 Budget Exhaustion Protocol

```
ON budget alert:

  IF BUDGET_WARNING (75%):
    → LOG: "Phase X at 75% budget"
    → NOTIFY: meta-agent
    → CONTINUE with heightened monitoring

  IF BUDGET_CRITICAL (90%):
    → LOG: "Phase X at 90% budget — entering conservation mode"
    → NOTIFY: meta-agent + human (async)
    → ACTIVATE: conservation mode
      - Reduce search queries by 50%
      - Skip non-critical validations
      - Use cached results where possible

  IF BUDGET_EXHAUSTED (100%):
    → LOG: "Phase X budget exhausted — stopping"
    → NOTIFY: human (blocking)
    → OPTIONS:
      a) Allocate from contingency (requires human approval)
      b) Reduce scope (renegotiate AC)
      c) Degrade output quality (document in disclaimer)
      d) Abort task

  IF CONTINGENCY_EXHAUSTED:
    → HARD STOP
    → Produce partial output with full audit trail
    → Escalate to human immediately
```

### 5.4 Early Stopping Criteria

| Критерий | Условие | Действие |
|----------|---------|----------|
| **Diminishing Returns** | 3+ итерации re-search без улучшения CI > 2% | STOP, задокументировать gap |
| **Confidence Plateau** | Средний confidence не растёт 2+ gate | STOP, зафиксировать текущий уровень |
| **Time Overrun** | elapsed > 1.5 × estimated_duration | WARN → re-scope или extend |
| **Cost Overrun** | spent > allocated × 1.25 | STOP → budget exhaustion protocol |
| **Quality Ceiling** | CI ≥ 90 и не растёт | Early deliver с отметкой "near-optimal" |
| **User Interrupt** | Получен сигнал прерывания | SAVE checkpoint → graceful exit |

---

## 6. Error Recovery

### 6.1 Circuit Breaker Pattern

```
Circuit Breaker для инструментов:

  [CLOSED] ──(failure)──▶ [OPEN] ──(timeout)──▶ [HALF-OPEN]
     ▲                        │                      │
     │                        │                      │ (test call success)
     └────────────────────────┘◄─────────────────────┘

States:
  CLOSED     → Нормальная работа, запросы проходят
  OPEN       → Инструмент отключён, все запросы → fallback
  HALF-OPEN  → Пробный запрос, при успехе → CLOSED

Rules:
  - 3 consecutive failures → OPEN
  - OPEN timeout: 60 seconds (exponential backoff: 60s, 120s, 240s)
  - HALF-OPEN: 1 пробный запрос, при success → CLOSED, при fail → OPEN
```

```python
class CircuitBreaker:
    """Circuit breaker для инструментов агента."""

    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF-OPEN"

    def __init__(self, tool_name: str, failure_threshold: int = 3, 
                 timeout_seconds: int = 60):
        self.tool_name = tool_name
        self.failure_threshold = failure_threshold
        self.timeout = timeout_seconds
        self.state = self.STATE_CLOSED
        self.failures = 0
        self.last_failure_time = None
        self.total_trips = 0

    def call(self, fn, *args, **kwargs):
        if self.state == self.STATE_OPEN:
            if self._timeout_expired():
                self.state = self.STATE_HALF_OPEN
                self._log_transition("OPEN → HALF-OPEN (timeout expired)")
            else:
                raise CircuitBreakerOpen(
                    f"{self.tool_name} is OPEN — using fallback"
                )

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        if self.state == self.STATE_HALF_OPEN:
            self.state = self.STATE_CLOSED
            self._log_transition("HALF-OPEN → CLOSED (success)")
        self.failures = 0

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.now(timezone.utc)
        if self.failures >= self.failure_threshold:
            self.state = self.STATE_OPEN
            self.total_trips += 1
            self._log_transition(
                f"CLOSED → OPEN ({self.failures} failures, trip #{self.total_trips})"
            )

    def _timeout_expired(self) -> bool:
        if not self.last_failure_time:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        # Exponential backoff: 60s, 120s, 240s
        backoff = self.timeout * (2 ** min(self.total_trips, 3))
        return elapsed >= backoff

    def _log_transition(self, transition: str):
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[CIRCUIT-BREAKER] {ts} | {self.tool_name}: {transition}")


class CircuitBreakerOpen(Exception):
    pass
```

### 6.2 Fallback Activation Logging

| Fallback Level | Trigger | Лог | Действие |
|----------------|---------|-----|----------|
| **L1: Tool Switch** | Circuit breaker OPEN для primary tool | `FALLBACK: tool=<primary> → <fallback>` | Переключение на резервный инструмент |
| **L2: Method Switch** | L1 не помог | `FALLBACK: method=<current> → <alt>` | Смена методологии (напр., аналитика → эвристика) |
| **L3: Scope Reduce** | L1+L2 не помогли | `FALLBACK: scope=full → reduced` | Сужение scope, сохранение критичных AC |
| **L4: Human Handoff** | L1-L3 не помогли или критичный путь | `FALLBACK: agent → human` | Полная эскалация человеку |

```yaml
fallback_log:
  timestamp: "2024-12-19T14:32:00Z"
  task_id: "drs_..."
  trigger: "circuit_breaker_OPEN" | "repeated_failure" | "budget_exhausted" | "quality_stall"

  level: 1 | 2 | 3 | 4
  from_tool: "<primary>"
  to_tool: "<fallback>"

  reason: "<why fallback activated>"
  impact: "DEGRADED" | "PARTIAL" | "BLOCKING"

  result: "SUCCESS" | "PARTIAL" | "FAILED"
  recovery_time_sec: <int>

  next_action: "CONTINUE" | "ESCALATE" | "ABORT"
```

### 6.3 Re-search Loop Protocol

```
RE-SEARCH TRIGGER CONDITIONS:

  Mandatory (всегда триггерят):
    - Gate FAIL + retry_count < max_retries
    - Coverage metric < 50% (critical gap)
    - Confidence score < 2.0 for P0 claims
    - 0 sources found for subtask

  Conditional (триггерят при наличии capacity):
    - Coverage metric 50-70% (warn zone)
    - Source diversity < 4 types
    - Freshness < threshold but > 50% threshold

  Never (не триггерят):
    - Cosmetic formatting issues
    - Confidence ≥ 3.0 for non-critical claims
    - Source availability beyond reasonable effort
```

**Re-search Modification Protocol:**

| Итерация | Действие | Параметры |
|----------|----------|-----------|
| 1 | Query Refinement | Expand keywords, add domain terms, remove restrictive filters |
| 2 | Tool Switching | Switch primary search tool, add specialized databases |
| 3 | Scope Adjustment | Broaden geographic scope, extend temporal window |
| 4+ | Human Escalation | Human-in-the-loop guidance, manual source suggestions |

```python
class ReSearchLoop:
    """Протокол повторного поиска."""

    MAX_ATTEMPTS_PER_SUBTASK = 3
    MAX_TOTAL_RESEARCHES = 10
    BACKOFF_STRATEGY = [60, 120, 240]  # seconds

    def should_trigger(self, gate_result: str, metrics: dict, 
                       claim_priority: str) -> bool:
        """Определить, нужен ли re-search."""
        if gate_result == "FAIL" and self.retries < self.MAX_ATTEMPTS:
            return True
        if metrics.get("coverage", 100) < 50:
            return True
        if claim_priority == "P0" and metrics.get("confidence", 5) < 2.0:
            return True
        if metrics.get("sources_found", 1) == 0:
            return True
        return False

    def plan_iteration(self, attempt: int) -> list[str]:
        """Определить стратегию для N-й итерации."""
        plans = {
            1: ["query_refinement"],
            2: ["tool_switching", "query_refinement"],
            3: ["scope_adjustment", "tool_switching", "query_refinement"]
        }
        return plans.get(attempt, ["human_escalation"])

    def execute_with_backoff(self, attempt: int, search_fn) -> dict:
        """Выполнить re-search с exponential backoff."""
        if attempt > 1:
            delay = self.BACKOFF_STRATEGY[min(attempt - 2, len(self.BACKOFF_STRATEGY) - 1)]
            time.sleep(delay)
        return search_fn()
```

### 6.4 Human Escalation Triggers

| Уровень | Trigger | Действие человека | Тип |
|---------|---------|-------------------|-----|
| **L1: Advisory** | 2nd retry failed | Guidance on scope/tools | Async (task continues) |
| **L2: Blocking** | 3rd retry + critical path | Direct intervention required | Sync (task pauses) |
| **L3: Override** | Gate 5 failed | Approve/reject with comments | Sync (final authority) |

**Escalation Decision Tree:**

```
Re-search failed?
│
├─ Yes → Retries exhausted?
│        │
│        ├─ No → Next iteration with modified params
│        │
│        └─ Yes → Is it critical path?
│                 │
│                 ├─ Yes → Human escalation (blocking)
│                 │         ├─ Human provides guidance → Resume
│                 │         └─ Human reduces scope → Adjust AC
│                 │
│                 └─ No → Degrade gracefully
│                          ├─ Document gap
│                          ├─ Lower confidence score
│                          └─ Continue with disclaimer
│
└─ No → Proceed to next gate
```

---

## 7. Multi-Agent Coordination

### 7.1 Agent Registry

```yaml
agent_registry:
  agents:
    - role: "research"
      name: "Research Agent"
      version: "1.0"
      status: "active" | "idle" | "busy" | "stalled" | "error"
      current_task: "<task_id> | null"
      current_checkpoint: "<cp_id> | null"
      capabilities: [SEARCH, EXTRACT, ANALYZE, COMPARE, SYNTHESIZE]
      dependencies: []
      last_heartbeat: "<ISO 8601>"
      health_score: 0.0-1.0

    - role: "factcheck"
      name: "FactCheck Agent (FCA)"
      version: "1.0"
      status: "active" | "idle" | "busy" | "stalled" | "error"
      current_task: "<task_id> | null"
      current_checkpoint: "<fca_checkpoint> | null"
      capabilities: [VALIDATE, CROSS_REFERENCE, BIAS_DETECT, QUANT_CHECK]
      dependencies: ["research"]  # FCA получает input от Research Agent
      last_heartbeat: "<ISO 8601>"
      health_score: 0.0-1.0

    - role: "format"
      name: "Format Agent"
      version: "1.0"
      status: "active" | "idle" | "busy" | "stalled" | "error"
      current_task: "<task_id> | null"
      current_checkpoint: "<cp_id> | null"
      capabilities: [FORMAT, RENDER, CHART_GENERATE]
      dependencies: ["research", "factcheck"]
      last_heartbeat: "<ISO 8601>"
      health_score: 0.0-1.0

    - role: "meta"
      name: "Meta-Agent (Orchestrator)"
      version: "1.0"
      status: "always_active"
      current_task: "<task_id> | null"
      capabilities: [PLAN, COORDINATE, ESCALATE, MONITOR]
      dependencies: ["research", "factcheck", "format"]
      last_heartbeat: "<ISO 8601>"
      health_score: 1.0
```

### 7.2 Inter-Agent Communication

**Протокол сообщений:**

```yaml
inter_agent_message:
  msg_id: "<uuid>"
  timestamp: "<ISO 8601>"
  from_agent: "research" | "factcheck" | "format" | "meta"
  to_agent: "research" | "factcheck" | "format" | "meta" | "broadcast"
  msg_type: "TASK_ASSIGN" | "RESULT_DELIVER" | "FEEDBACK" | 
            "ESCALATE" | "CHECKPOINT_SYNC" | "HEARTBEAT_PING" | "ERROR_NOTIFY"

  payload:
    # TASK_ASSIGN
    task_id: "<id>"
    description: "<what to do>"
    input_artifacts: [<refs>]
    deadline: "<ISO 8601>"
    budget_usd: <float>

    # RESULT_DELIVER
    output_artifacts: [<refs>]
    quality_score: <float>
    confidence: <float>

    # FEEDBACK (FCA → Research)
    flagged_findings: [<claim_ids>]
    corrections: [<correction_objects>]
    required_action: "replace" | "append_context" | "remove" | "reevaluate"

    # ESCALATE
    level: 1 | 2 | 3
    reason: "<why>"
    options: [<possible_actions>]

  priority: "LOW" | "NORMAL" | "HIGH" | "CRITICAL"
  requires_ack: true | false
```

**Каналы коммуникации:**

| Канал | Назначение | Формат |
|-------|-----------|--------|
| `task_queue` | Meta-agent → Workers | TASK_ASSIGN сообщения |
| `result_bus` | Workers → Meta-agent | RESULT_DELIVER сообщения |
| `feedback_loop` | FCA ↔ Research Agent | FEEDBACK сообщения (max 3 iterations) |
| `escalation_ch` | Any → Human | ESCALATE сообщения |
| `heartbeat_bus` | All → Meta-agent | HEARTBEAT_PING (каждые 2-3 мин) |
| `error_bus` | Any → All | ERROR_NOTIFY (broadcast) |

### 7.3 Deadlock Detection

```
DEADLOCK CONDITIONS:

  Circular Wait:
    A waits for B → B waits for C → C waits for A

  Resource Hold:
    A holds checkpoint X and waits for checkpoint Y held by B

  Mutual Exclusion:
    Только один агент может писать в checkpoint одновременно

DEADLOCK DETECTION ALGORITHM:

  1. Построить wait-for graph из agent_registry
  2. Запустить DFS для поиска циклов
  3. IF cycle detected → DEADLOCK

DEADLOCK RESOLUTION:

  1. IDENTIFY: определить агентов в deadlock
  2. VICTIM: выбрать жертву (наименьший progress, lowest priority)
  3. ROLLBACK: откатить жертву до последнего checkpoint
  4. RELEASE: освободить ресурсы жертвы
  5. RESUME: остальные агенты продолжают
  6. RETRY: жертва перезапускается через 30 сек

PREVENTION:
  - Lock ordering: все агенты запрашивают ресурсы в фиксированном порядке
  - Timeout: агент ждёт ресурс max 60 сек, иначе abort + retry
  - Wait-Die / Wound-Wait: старший агент убивает младшего при конфликте
```

```python
class DeadlockDetector:
    """Детектор deadlock для multi-agent системы."""

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.wait_graph: dict[str, set[str]] = {}  # agent -> {agents it waits for}

    def update_wait_graph(self, agent: str, waiting_for: list[str]):
        """Обновить граф ожидания."""
        self.wait_graph[agent] = set(waiting_for)

    def detect_cycle(self) -> list[str] | None:
        """DFS для поиска цикла в wait-for graph."""
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.wait_graph.get(node, set()):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:]

            path.pop()
            rec_stack.remove(node)
            return None

        for node in self.wait_graph:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle
        return None

    def resolve(self, cycle: list[str]) -> str:
        """Разрешить deadlock — выбрать и откатить жертву."""
        # Выбрать жертву: наименьший progress
        victim = min(cycle, key=lambda a: self.registry.get_progress(a))
        self._log(f"DEADLOCK detected: {' → '.join(cycle)} → victim={victim}")
        
        # Rollback victim
        self.registry.rollback_agent(victim)
        self.wait_graph[victim] = set()
        
        return victim

    def _log(self, message: str):
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[DEADLOCK] {ts} | {message}")
```

### 7.4 Timeout Handling

```
TIMEOUT HIERARCHY:

  Subtask Level:
    - HARD LIMIT: 15 минут wall-clock
    - SOFT TARGET: 5-10 минут
    - WARNING: > 10 минут → ревью на атомарность

  Agent Level:
    - HEARTBEAT timeout: 2 × heartbeat_interval
      (если heartbeat не получен → agent считается stalled)
    - TASK timeout: 1.5 × estimated_duration
      (при превышении → re-scope или escalate)

  Communication Level:
    - Message ACK timeout: 30 секунд
      (если requires_ack=true и ACK не получен → retry × 3)
    - Feedback loop timeout: 5 минут на итерацию
      (при превышении → escalate)

  System Level:
    - Deadlock detection interval: 30 секунд
    - Global task timeout: по бюджету времени
      (при превышении → graceful degradation)
```

**Timeout Actions:**

| Уровень | Timeout | Действие |
|---------|---------|----------|
| Subtask | > 15 min | Abort subtask, mark STALL, create `_blocked` checkpoint |
| Heartbeat | > 2× interval | Mark agent STALLED, attempt ping, if no response → restart agent |
| Task | > 1.5× estimate | WARN → re-scope → or extend with human approval |
| Message ACK | > 30 sec | Retry × 3 → if still no ACK → mark recipient UNAVAILABLE |
| Feedback loop | > 5 min/iteration | Force continue with best-effort corrections |
| Quality gate | > 30 sec | WARN + proceed с пометкой `degraded` + checkpoint (НЕ молчаливый stop) |

```python
class TimeoutManager:
    """Менеджер таймаутов для multi-agent системы."""

    def __init__(self):
        self.timeouts: dict[str, dict] = {}
        self.monitors: dict[str, any] = {}

    def set_timeout(self, entity_id: str, timeout_sec: int, 
                    on_timeout: callable, context: dict = None):
        """Установить таймаут для сущности."""
        import asyncio
        
        async def _watchdog():
            await asyncio.sleep(timeout_sec)
            self._log(f"TIMEOUT: {entity_id} after {timeout_sec}s")
            on_timeout(entity_id, context)

        task = asyncio.create_task(_watchdog())
        self.monitors[entity_id] = task
        self.timeouts[entity_id] = {
            "deadline": datetime.now(timezone.utc).timestamp() + timeout_sec,
            "timeout_sec": timeout_sec,
            "context": context
        }

    def cancel_timeout(self, entity_id: str):
        """Отменить таймаут (при успешном завершении)."""
        if entity_id in self.monitors:
            self.monitors[entity_id].cancel()
            del self.monitors[entity_id]
            del self.timeouts[entity_id]

    def extend_timeout(self, entity_id: str, additional_sec: int):
        """Продлить таймаут."""
        if entity_id in self.timeouts:
            self.timeouts[entity_id]["deadline"] += additional_sec
            # Перезапустить watchdog
            self.cancel_timeout(entity_id)
            remaining = self.timeouts[entity_id]["deadline"] - \
                       datetime.now(timezone.utc).timestamp()
            self.set_timeout(entity_id, max(0, remaining), 
                           self.timeouts[entity_id]["context"])

    def _log(self, message: str):
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[TIMEOUT] {ts} | {message}")
```

---

## 8. Recovery: Full Crash Protocol

### 8.0 Checkpoint State & Resume (the resume anchor)

A checkpoint is "resumable" only if it serializes the actual collected work, not a prose milestone.
Therefore **every** `checkpoints/cp_<NN>_<stage>.md` MUST begin with a fenced ` ```json ` `state` block
(canonical, machine-loadable), followed by the human narrative. This block is the single source of truth
for recovery — the heartbeat is only a hint.

```json
{
  "checkpoint_version": "1.3",
  "run_id": "whoop-cdek-20260607-b7e2",
  "created_utc": "2026-06-07T10:02:40Z",
  "task_fingerprint": "<sha1(normalize(question|route|depth|scope))>",
  "stage": "cp_01_raw", "phase_completed": 2, "next_phase": 3,
  "sources_screened": 12,
  "extraction_table_complete": true,
  "citations_verified": false,
  "last_gate": {"id": "G1", "verdict": "PASS", "reason": null},
  "budget": {"limit_usd": 0.20, "spent_usd": 0.0, "loads_used": 4, "loads_cap": 6},
  "task_frame": {"question": "...", "route": "B", "depth": "Standard",
                 "scope": ["cdek.shopping"], "acceptance_criteria": ["..."]},
  "subtasks": [{"id": "ST-1", "type": "SEARCH", "status": "done"}],
  "sources":  [{"id": "S1", "url": "https://...", "tier": "B", "fetched_via": "jina", "status": "rendered",
                "created_utc": "...", "raw_path": "raw/S1.txt", "extract": {"...": "..."}, "trust": "untrusted",
                "scores": {
                  "authority": 0.65, "recency": 0.80, "independence": 0.60,
                  "traceability": 0.70, "corroboration": 0.50, "composite": 0.672,
                  "breakdown": [
                    ["authority", 0.195], ["recency", 0.200], ["independence", 0.120],
                    ["traceability", 0.105], ["corroboration", 0.050]
                  ],
                  "disqualifiers": []
                }}],
  "claims":   [{"id": "C1", "text": "...", "category": "verified", "confidence": 4,
                "sources": ["S1", "S2"], "status": "confirmed",
                "metadata": {"disagreement": false, "reverified_category": "verified"}}],
  "open_items": ["cross-check Peak/One on a 2nd same-site listing"],
  "resume_instruction": "Sources S1-S2 already rendered — do NOT re-fetch; continue at Phase 3 FCA.",
  "trace": [
    {"event": "ingest", "ts": "2026-06-07T10:02:41Z"},
    {"event": "score", "ts": "2026-06-07T10:02:41Z"},
    {"event": "factcheck", "ts": "2026-06-07T10:02:42Z"},
    {"event": "verify", "ts": "2026-06-07T10:02:42Z"},
    {"event": "cluster", "ts": "2026-06-07T10:02:42Z"},
    {"event": "build", "ts": "2026-06-07T10:02:42Z"}
  ]
}
```

**Version notes for §8.0 state block:**
- `"checkpoint_version": "1.3"` — current version (Phase 15). Older checkpoints (1.0, 1.1, 1.2) migrate automatically: new fields default gracefully on load; the version field is re-stamped to "1.3" on save.
- `"last_gate".reason` — added in v1.3. `null` on PASS; a non-null string on WARN/FAIL carries the blocking reason from `gate_blocks_transition`. Required for the `engine gate` verb output.
- `"claims[].metadata"` — added in v1.3. An open per-claim annotation dict. The in-pipeline auto-verify that stamped `metadata["disagreement"]` / `["reverified_category"]` was removed in v1.5 (never rendered, constant-False on hint-less runs), so `run_pipeline` now leaves it empty `{}`. The standalone `engine verify` verb still emits those fields on demand — it re-derives each claim's category from evidence and reports recorded-vs-evidence drift.
- `"trace"` — added in v1.3. `snapshot.trace` is the serialized form of `RunTrace.as_list()`: a list of `{event, ts}` dicts, one appended per pipeline stage by `run_pipeline`. Stages, in order: `ingest`, `score`, `factcheck`, `cluster`, `build` (the `verify` stage was dropped in v1.5 with the in-pipeline auto-verify). An empty list means the snapshot was loaded from a pre-Phase 15 checkpoint or built without `run_pipeline`.
- `sources[].scores.breakdown` — list of `[label, contribution]` pairs (contributions sum to `composite`). Present after Phase 3 scoring; empty `[]` before.
- `sources[].scores.disqualifiers` — retained for checkpoint backward-compat (the anti-fit veto layer was removed in v1.5). Scoring always leaves it empty `[]`; only old checkpoints may carry legacy veto reasons.

**Write rule.** Emit a checkpoint at every gate boundary (post-collection → `cp_01_raw`, post-processing
→ `cp_02_processed`, post-analysis → `cp_03_draft`, post-synthesis → `cp_04_reviewed`, final), plus on
graceful-degradation finalize and before any human escalation. Write the `state` block FIRST, verify it
parses, then the narrative. Never overwrite a prior `NN`. The `sources[].extract` field carries the actual
gathered data — that is what makes resume free of re-collection.

#### Именованные границы компактизации (Phase 13, engine/compact.py)

Помимо record-чекпоинтов, движок определяет три именованные **границы компактизации** — точки, в которых накопленный контекст прогона передаётся следующему агенту через `build_handoff`. Граница определяется НЕ по числу токенов, а по завершённой фазе.

```python
COMPACTION_BOUNDARIES: tuple[str, ...] = (
    "post_collection",   # сбор завершён, впереди обработка — next_phase == 3 (cp_01_raw)
    "pre_synthesis",     # анализ завершён, впереди синтез   — next_phase == 5
    "pre_report",        # синтез завершён, впереди отчёт     — next_phase == 6
)
```

**Функция `should_compact(snapshot) -> Optional[str]`** возвращает имя ближайшей границы, если снимок находится ровно на ней, и `None` в остальных случаях. Сопоставление выполняется **только по `snapshot.next_phase`** (фаза, в которую прогон вот-вот войдёт):

| Имя границы | Условие на `snapshot` | Опорный чекпоинт |
|-------------|----------------------|------------------|
| `"post_collection"` | `next_phase == 3` | `cp_01_raw` (`phase_completed == 2`) |
| `"pre_synthesis"` | `next_phase == 5` | после анализа |
| `"pre_report"` | `next_phase == 6` | после синтеза (`cp_04_reviewed`) |

Числа фаз закреплены **опорным state-блоком §8.0** (выше): post-collection чекпоинт `cp_01_raw` имеет `next_phase == 3`, а `pipeline.build_snapshot` выставляет `next_phase == 5`, когда прогон готов к синтезу. Эти же пороги согласованы с `engine/state.gate_blocks_transition` (переход к фазе ≥ 5 требует `citations_verified = True`).

При обнаружении границы вызывается `build_handoff(snapshot)` (из `engine/compact.py`) — без изменений. Результат передаётся принимающему агенту вместо полного снимка. Функция `should_compact` чистая и детерминированная: принимает только снимок, не читает часы и не имеет побочных эффектов.

**Resume entry point (runs in Phase 0, before any planning):**
1. Scan `./research_output/checkpoints/` for `cp_*.md`. None → fresh run.
2. Pick the highest `NN` whose `state` block PARSES and passes schema validation. If the latest is
   malformed/partial → fall back to `NN-1`; if none valid → fresh run (note it in the audit trail).
3. **Fingerprint guard:** `task_fingerprint == sha1(normalize(current question|route|depth|scope))`?
   - match → RESUME; announce `↩ Resuming <run_id> from <stage> (phase <next_phase>)`.
   - mismatch → a *different* task: start a fresh run dir; DO NOT load or clobber the other state.
4. Rehydrate `task_frame`, `subtasks`, `sources` (with extracts), `claims`. Jump to `next_phase`;
   do only `open_items` + remaining subtasks.

**Integrity rules (each prevents a specific failure):**
- highest-valid-`NN` + `NN-1` fallback → never resume a half-written checkpoint.
- fingerprint guard → never resume an unrelated task's state into the wrong question.
- **budget carry-forward:** `spent_usd` and `loads_used` are CARRIED, never reset — otherwise an
  interrupted run resumes with a fresh budget and blows past its cap.
- **collected sources are READ-ONLY on resume:** a source with `status` `rendered`/`done` and an
  `extract` MUST be served from `state` — **re-fetching it is a protocol violation, not an
  optimization.** The only sanctioned new fetch on resume is (a) independent cross-verification of a
  *flagged* claim, or (b) a staleness re-check (below). Both MUST increment `new_collection_calls` —
  never a silent fetch reported as `0`.
- **staleness:** time-sensitive sources (prices, "latest", quotes) older than the freshness window
  (Quick 24h · Standard 7d · Deep 14d) are RE-VERIFIED on resume, not trusted blindly; flag any
  resumed-stale value in the final report.

> **Known limitation (observed in testing).** Native execution does NOT *enforce* read-only reuse:
> a model with web access may re-fetch already-collected sources and under-report the count (log `0`
> while actually fetching). So native-mode resume reliably delivers **state continuity + integrity
> guards (fingerprint match/mismatch, no-clobber, no fabricated facts)** but **not guaranteed token
> savings**. Hard enforcement requires the supervised control-loop
> (`examples/supervised_orchestrator.workflow.js`), where the orchestrator passes the `snapshot` and
> never re-invokes collection, and the fetch count is observed externally rather than self-reported.

### 8.1 On Crash / Interruption

```
PROTOCOL: SYSTEM_RECOVERY

INPUT: task_id, latest_heartbeat_path

STEP 1: LOAD latest checkpoint state (§8.0)
  → Scan checkpoints/ ; pick highest cp_NN whose ```json `state` block is VALID
  → Parse state: task_frame, subtasks, sources (with extracts), claims, budget, next_phase
  → Heartbeat is only a hint; the `state` block is the source of truth for resume

STEP 2: IDENTIFY resume point
  → task_fingerprint must match the current request (else: different task → fresh run dir, do not clobber)
  → Resume from state.next_phase; carry budget.spent_usd + loads_used forward (never reset)
  → If no valid checkpoint → start from cp_01_raw / restart

STEP 3: VALIDATE integrity (§8.0 rules)
  → highest-valid-NN; if the latest `state` is malformed/partial → fall back to NN-1
  → Re-verify stale time-sensitive sources (freshness window) instead of trusting blindly
  → Sources with status rendered/done are reused (NOT re-fetched) — the point of resume

STEP 4: RESTORE agent registry
  → Load agent states from checkpoint
  → Check health of each agent
  → Restart stalled agents

STEP 5: RESUME orchestration
  → Meta-agent reads execution plan
  → Re-assign pending subtasks
  → Continue from next gate

STEP 6: LOG recovery action
  → Write recovery_manifest.yaml
  → Append to audit trail
  → Notify human if L2+ escalation

OUTPUT: Execution resumes from recovered state
```

### 8.2 Recovery Manifest Template

```yaml
# recovery_manifest.yaml
recovery_id: "rec_20241219_143000"
task_id: "drs_ai-market_20241219"
trigger: "crash" | "interruption" | "agent_stall" | "deadlock"

detected_at: "2024-12-19T14:30:00Z"
recovered_at: "2024-12-19T14:35:00Z"
recovery_time_sec: 300

last_heartbeat: "./heartbeats/heartbeat_20241219_143000_research.md"
recovery_checkpoint: "cp_02_processed"

agents_status:
  research:
    state: "recovered"
    last_checkpoint: "cp_02_processed"
    subtasks_pending: ["s6", "s7", "s8", "s9"]
    health_score: 0.95
  factcheck:
    state: "idle"
    waiting_for: "cp_04_reviewed"
    health_score: 1.0
  format:
    state: "idle"
    waiting_for: "final"
    health_score: 1.0

actions_taken:
  - "Read heartbeat from 2024-12-19T14:30:00Z"
  - "Validated cp_02_processed integrity: PASS"
  - "Restored research agent from cp_02_processed"
  - "Re-assigned subtasks s6-s9 to research agent"
  - "Continued from Gate 3 (Post-Analysis)"

human_notification: false  # true if L2+ escalation required
```

---

## 9. Phase 14: New CLI Verbs & Escalation Actions

### 9.1 `rescore` — full re-derivation over a frozen snapshot

```
python -m engine rescore --input snapshot.json [--shallow] [--report [--mode findings|debunk|mixed]] [--out PATH]
```

JSON-in (via `--input` or stdin): `{ "snapshot": <Snapshot dict, CHECKPOINT_VERSION "1.2">, "now"?: ISO8601, "model_categories"?: {claim_id: category}, "half_life_days"?: 30 }`. The timestamp is the JSON `now` field — there is **no** `--now` CLI flag on `rescore`.

`rescore` re-runs scoring over the snapshot's `sources` list without touching the source payloads (`url`, `extract`, `raw_path`, `trust`) or source identity: `score_sources` (recomputes `composite`/`tier`/`breakdown`/`disqualifiers` from the **cached** components — `authority`/`recency` are re-seeded only when `None`, which is what makes rescore idempotent) → `score_claims` → (deep mode only) `factcheck_claims` → `cluster_claims`.

**Output (default JSON):** `{ "snapshot": <rescored>, "diff": {"sources": [{id, tier_before, tier_after}], "claims": [{id, confidence_before, confidence_after, category_before, category_after}]}, "readonly_ok": true }` (plus a `"warning"` field under `--shallow`). If any source payload changed, exits **1** with `{ "error", "changed_ids" }`.

**Behavioral guarantees:**
- Deterministic & idempotent: same input + rules → byte-identical output; a second rescore yields an empty diff.
- Read-only over collected sources: no network, no re-fetch; enforced by `assert_sources_readonly`.
- No veto: the anti-fit veto layer was removed in v1.5; rescore derives tiers from the composite arithmetic alone, and `source.scores.disqualifiers` stays empty.

**Flags.** `--shallow` skips **factcheck + clustering** only (NOT recency) — categories/verdicts are then stale relative to the new tiers and a warning is emitted (carried onto the `--report` Markdown too). `--report` emits Markdown instead of JSON (`--mode findings|debunk|mixed`). `--out PATH` also writes the rescored snapshot JSON to `PATH`.

### 9.2 Feedback-ledger verbs (`memory` subcommand)

An **append-only feedback ledger** — human verdicts on engine decisions — lives as a `feedback` table in the cross-run SQLite store (`memory.py`), not a flat file. It is managed through the `memory` subcommand:

```
python -m engine memory --op record-feedback [--db PATH]            # JSON-in: a record (or {"record": {...}})
python -m engine memory --op list-feedback   [--db PATH] [--kind K] [--run-id R]
```

`--db PATH` selects the SQLite file (omit → in-memory, for tests). The timestamp is `--now` (stamped verbatim into `recorded_utc`; no clock read).

**`record-feedback`:** JSON-in a record `{run_id?, item_id?, kind?, engine_value?, human_value?, trace_json?}` (a bare record or `{"record": {...}}`). Always INSERTs — strictly append-only, so two records with the same `item_id` produce two rows. Returns `{ "id": <rowid> }`.

**`list-feedback`:** Returns `{ "feedback": [ {id, run_id, item_id, kind, engine_value, human_value, trace_json, recorded_utc}, … ] }`, ordered oldest-first (by `id`); optional `--kind` / `--run-id` filters.

**NOT auto-consumed by scoring.** The ledger is an audit/calibration trail, never a scoring input: `rescore`, `score`, and the pipeline never read the `feedback` table. Verdicts are acted on explicitly by a human (e.g. dropping a source from the collected set before a rescore) — the engine never silently alters scores from logged feedback.

### 9.3 New `next_valid_actions` escalation tokens

`collect.normalize` and the broader pipeline may now emit the following action tokens in `CollectionResult.next_valid_actions` (and in gate-log `actions[]`):

| Token | When emitted | Meaning |
|-------|-------------|---------|
| `retry_with_proxy` | Provider blocked, not rate-limited | Retry the same URL through a proxy/stealth tier (e.g. Firecrawl stealth, Browserbase) |
| `escalate_to_agent` | Repeated failures across all fallback tiers | Hand control to a human agent or a supervised orchestrator loop |
| `enrich_top_n` | Post-ranking, before synthesis | Fetch full content for the top-N ranked sources that currently have only a snippet |
| `fetch_next_page` | Paginated result set, more pages available | Continue collection with the next page of results (token or offset provided in context) |
| `no_more_pages` | Last page of a paginated set reached | Stop pagination; proceed to ingest |

These tokens follow the same convention as the existing tokens (`ingest_items`, `retry_after_backoff`, `escalate_to_firecrawl`, `enable_provider`): they are **suggestions**, not commands. The calling agent or orchestrator decides whether to act on them.

### 9.4 RSS tier in the collection contract

RSS/Atom is classified `"SAFE"` in `PROVIDER_RISK` alongside `native_web_search`, `jina_reader`, `jina_search`, and `firecrawl`. Items produced by `collect.normalize("rss", ...)` carry:

- `fetched_via = "rss"`
- `metadata["risk_class"] = "SAFE"`
- `published_at` — extracted from `<published>` (Atom), `<updated>` (Atom fallback), or `<pubDate>` (RSS 2.0)

Because `published_at` is reliably present, ingest assigns `date_confidence = "high"` — the highest possible value — and the recency component of the composite score is computed (not defaulted). This makes RSS a high date-confidence discovery tier well-suited for the discover-cheap-then-enrich-survivors pattern described in SKILL.md Phase 2.

---

## 10. Phase 15: Integration & Reachability

### 10.1 Root-Cause Invariant Table

The table below documents the invariants the engine enforces to prevent recurring integration failures. Each invariant has a short name, a description, and the test or mechanism that enforces it.

| # | Invariant | Description | Enforced by |
|---|-----------|-------------|-------------|
| 1 | fingerprint guard | A resumed snapshot must match the current task fingerprint; mismatch → fresh run dir, no clobber. | `state.resume_or_fresh`, `test_phase1_state.py` |
| 2 | budget carry-forward | `spent_usd` and `loads_used` are never reset on resume. | `state.resume_or_fresh`, carry-forward logic |
| 3 | sources read-only on resume | Collected sources with `status rendered/done` are served from `state`, not re-fetched. | `state.assert_sources_readonly`, `test_phase1_state.py` |
| 4 | citations_verified gate | `target_phase >= 5` (synthesis/output) is blocked until `citations_verified == True`. | `state.gate_blocks_transition`, gate enforcement tests |
| 5 | sources_screened gate | `target_phase >= 2` (processing) is blocked when `sources_screened == 0`. | `state.gate_blocks_transition`, gate enforcement tests |
| 6 | trust fence | Retrieved web content is UNTRUSTED data; embedded instructions are ignored. Enforced at `ingest.source_from_raw` via `TrustLevel`. | `engine/ingest.py`, `test_phase8.py` |
| 7 | ~~veto is absolute~~ (removed v1.5) | The anti-fit veto layer was removed in v1.5 as inert (it fired only on `.example` placeholder hosts + 2 self-declaring phrases). Source authority is composite-only; prompt-injection defense stays in the trust fence (inv #6). | n/a — see CHANGELOG [1.5.0] / inv #10 |
| 8 | rescore is idempotent | A second rescore over the same snapshot + rules yields an empty diff; cached components are not zeroed before re-scoring. | `state.rescore_snapshot`, `test_phase14.py` |
| **9** | **built but unreachable = dead integration** | **Every curated capability MUST have a CLI subparser-choice AND be exercised end-to-end. A capability that passes unit tests but has no CLI verb and/or is never called in `run_pipeline` is treated as unintegrated and does not count toward the acceptance bar.** | **`tests/test_phase15_reachability.py`** — asserts that each of `verify`, `plan`, `gate` appears in `cli.build_parser()` choices, and that `run_pipeline` populates `snapshot.trace`. (The in-pipeline auto-verify writing `claim.metadata["disagreement"]` was removed in v1.5 as inert — inv #10; the `verify` capability remains reachable via its CLI verb.) |
| **10** | **shipped ≠ valuable** | **A curated capability that moves no measured metric — neither a benchmark score (DRACO) nor a trust metric — is a cut candidate, not a keep. A simplification cut is accepted only when the trust scorecard is byte-identical before/after (removed dead code, not value).** | **`bench/trust/` scorecard** (determinism / unsupported-claim suppression recall+precision / citation completeness / checkpoint fidelity); `docs/SKILL_VALUE_AND_SIMPLIFICATION.md`, CHANGELOG [1.5.0]. |
| **11** | **fires on real input = shipped** | **A new curated capability counts as shipped only once it demonstrably changes output/score on a NON-synthetic fixture. Mechanism-green unit tests are not enough — a feature whose rules match only placeholder inputs (the v1.2 veto fired only on `.example` hosts) or whose signal is constant on the common path (the in-pipeline auto-verify) is inert. Generalises #10 from cut-time to ship-time.** | Required "fired-on-real-input" test/eval per new capability + value scorecard (`bench/quality/`, `bench/trust/`); `docs/BUGLOG.md` (roots C). |

> **Why invariant #9 matters:** Phase 15 root-causes the pattern where capabilities are fully unit-tested (green) but silently dormant in production because neither the CLI nor `run_pipeline` ever invokes them. The acceptance bar shifts from "unit-test passes" to "reachable end-to-end": a CLI subparser entry-point PLUS a call site in `run_pipeline` (or explicit delegation from `engine run`).

> **Bug-class prevention.** Every defect found in this project, its root cause, and the standing guard that now catches its class are catalogued in [`docs/BUGLOG.md`](../../../../docs/BUGLOG.md) (14 bugs over v1.3–v1.5 → 5 systemic roots A–E). The pre-merge gate that ties the rituals + guards together is [`docs/PRE_MERGE_CHECKLIST.md`](../../../../docs/PRE_MERGE_CHECKLIST.md), and `.github/workflows/ci.yml` enforces the suites + determinism on every push/PR. Rule: a bug fixed without a new guard is a bug that can recur.

### 10.2 Phase 15 CLI Verbs

Three verbs become reachable for the first time in Phase 15:

#### `verify`

```
python -m engine verify --input {snapshot, now?}
```

JSON-in: `{snapshot: <Snapshot dict>, now?: ISO8601}`. Re-verifies every claim in the snapshot; there is no subtask-scoped variant.

JSON-out:
```json
{
  "results": [
    {
      "claim_id": "C1",
      "original_category": "verified",
      "reverified_category": "verified",
      "disagreement": false
    }
  ],
  "summary": {"n_claims": 1, "n_disagreements": 0}
}
```

`verify` calls `verify.reverify_claim` for each claim in the snapshot WITHOUT passing `model_categories` or reading `verdict_explanation`, so the re-derived category reflects the evidence alone. A disagreement (`original_category != reverified_category`) means the recorded verdict diverges from the evidence-supported verdict. Pure, deterministic, no mutation of the snapshot.

#### `plan`

```
python -m engine plan --input {snapshot} | {subtasks}
```

JSON-in: `{snapshot: <Snapshot dict>}` (subtasks are taken from `snapshot.subtasks`) OR `{subtasks: [...]}` directly.

JSON-out:
```json
{
  "status": "valid",
  "errors": [],
  "layers": [["ST-1"], ["ST-2", "ST-3"]],
  "ready": ["ST-2", "ST-3"],
  "max_concurrent": 5
}
```

`plan` calls `plan.validate_plan` (reports unknown deps and non-FEEDBACK cycles), `plan.topo_order` (Kahn-style parallel layering, max 5 per level), and `plan.ready_set` (PENDING subtasks whose every STRICT predecessor is DONE). `status` is `"invalid"` when `errors` is non-empty.

#### `gate`

```
python -m engine gate --input {snapshot, target_phase?}
```

JSON-in: `{snapshot: <Snapshot dict>, target_phase?: int}` (defaults to `snapshot.next_phase`).

JSON-out:
```json
{
  "blocks_transition": null,
  "should_stop": null,
  "should_compact": null
}
```

Each key is `null` when the check passes. Non-null values:
- `blocks_transition`: reason string from `state.gate_blocks_transition` (e.g. `"gate blocked: target_phase 5 requires citations_verified True, but citations_verified is False"`).
- `should_stop`: reason token from `state.should_stop` (`"budget_exhausted"` | `"done_condition_met"` | `"stalled_uncertainty"`).
- `should_compact`: boundary name from `compact.should_compact` (`"post_collection"` | `"pre_synthesis"` | `"pre_report"`).

### 10.3 run_pipeline Phase 15 additions

`pipeline.run_pipeline` (Phase 15, trimmed in v1.5):

**Trace population.** `run_pipeline` creates a `RunTrace` instance and appends one `{event, ts}` dict per stage, in order: `ingest`, `score`, `factcheck`, `cluster`, `build` (`ts` is the passed-in `now_utc`, never a clock read). The Phase-15 in-pipeline auto-verify that also stamped `claim.metadata["disagreement"]` / `["reverified_category"]` was removed in v1.5 as inert (never rendered, constant-False on hint-less runs); on-demand independent re-derivation stays in the `engine verify` verb. At the end, `snapshot.trace = trace.as_list()` serializes the run log into the snapshot for checkpoint persistence and `engine gate`/`engine report` inspection.

**Gate consultation.** `run_pipeline` no longer hardcodes `next_phase=5`. After `build_snapshot` and after the gate-signal fields are set, it computes `snapshot.next_phase` as the highest phase `p∈{1..5}` for which `state.gate_blocks_transition(snapshot, p)` returns `None`, and records `snapshot.last_gate` (with `reason`). This means the pipeline reflects the blocked/unblocked state of the transition rather than always writing phase 5.

## 11. Appendices

### Appendix A: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│              DEEP RESEARCH — AGENT MONITORING QUICK CARD            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  HEARTBEAT:    Every 2-3 min (tasks 1-4h)                          │
│                Every 1 min (tasks 4-24h)                            │
│                Every 30 sec (tasks > 24h)                            │
│                ALSO: start, 25/50/75%, stage change, completion      │
│                                                                     │
│  CHECKPOINTS:  cp_01_raw → cp_02_processed → cp_03_draft           │
│                → cp_04_reviewed → final                              │
│                                                                     │
│  QUALITY GATES: 5 gates, binary PASS/FAIL                          │
│    G1: Post-Collection    G2: Post-Processing                       │
│    G3: Post-Analysis      G4: Post-Synthesis                        │
│    G5: Final Output                                                   │
│                                                                     │
│  FCA:          Independent heartbeat every 30 sec                   │
│                6 categories: VERIFIED/FALSE/OUTDATED/INCOMPLETE/    │
│                PERSPECTIVE/UNCERTAIN                                 │
│                                                                     │
│  COST:         15/10/25/20/10/15/5% allocation (G1-G2-G3-G4-G5-    │
│                FCA-contingency)                                      │
│                Alerts: 75% WARN, 90% CRITICAL, 100% EXHAUSTED       │
│                                                                     │
│  CIRCUIT BREAKER:  3 failures → OPEN → 60s timeout → HALF-OPEN    │
│                                                                     │
│  ESCALATION:   L1 Advisory → L2 Blocking → L3 Override              │
│                                                                     │
│  RECOVERY:     6 steps: Read heartbeat → Identify checkpoint →     │
│                Validate → Restore state → Resume → Log               │
│                                                                     │
│  DEADLOCK:     Detect cycle in wait-for graph → pick victim →      │
│                rollback → release resources → retry                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Appendix B: File & Directory Structure

```
./research_output/
├── task_manifest.yaml              # Общий манифест исследования
├── checkpoints/
│   ├── cp_01_raw.md
│   ├── cp_02_processed.md
│   ├── cp_03_draft.md
│   ├── cp_04_reviewed.md
│   └── final.md
├── artifacts/
│   ├── cp_01/                      # Артефакты cp_01_raw
│   │   ├── sources_index.json
│   │   ├── search_queries.log
│   │   └── raw_extracts/
│   ├── cp_02/                      # Артефакты cp_02_processed
│   │   ├── validated_data.json
│   │   ├── data_quality_report.md
│   │   └── merged_dataset.csv
│   ├── cp_03/                      # Артефакты cp_03_draft
│   │   ├── analysis_report.md
│   │   ├── insights.json
│   │   └── comparison_matrices/
│   ├── cp_04/                      # Артефакты cp_04_reviewed
│   │   ├── reviewed_report.md
│   │   ├── fact_check_log.md
│   │   └── confidence_scores.json
│   └── final/                      # Финальные артефакты
│       ├── report.md
│       ├── executive_summary.md
│       ├── appendices/
│       ├── bibliography.json
│       └── methodology.md
├── heartbeats/                     # Heartbeat-файлы всех агентов
│   ├── heartbeat_20241219_143000_research.md
│   ├── heartbeat_20241219_143000_factcheck.md
│   └── heartbeat_20241219_143030_research.md
├── gates/                          # Логи quality gates
│   ├── gate1_pass_20241219_121500.log
│   ├── gate2_pass_20241219_123000.log
│   └── gate3_retry_20241219_131500.log
├── costs/                          # Cost tracking
│   ├── cost_snapshot_20241219_143000.json
│   └── cost_timeseries.csv
├── recovery/                       # Recovery артефакты
│   ├── recovery_manifest.yaml
│   └── state_snapshots/            # Автоматические бэкапы
└── audit/
    └── full_audit_trail.md           # Полная цепочка аудита
```

### Appendix C: Log Level Reference

| Level | Использование | Примеры |
|-------|--------------|---------|
| `DEBUG` | Детали выполнения subtask | Начало/конец поиска, парсинг |
| `INFO` | Нормальные события | Gate pass, checkpoint created, heartbeat |
| `WARN` | Потенциальные проблемы | Budget 75%, freshness low, single source |
| `ERROR` | Ошибки, требующие действия | Gate fail, tool timeout, checksum mismatch |
| `CRITICAL` | Блокирующие проблемы | Budget exhausted, >20% FALSE, deadlock, data corruption |

### Appendix D: Integration Flow Summary

```
Timeline:
  T+0min     → Start: AC defined, agents registered, budget allocated
  T+2-3min   → Heartbeat: progress %, current gate, issues
  T+gate1    → Checkpoint: cp_01_raw + Gate 1 log
  T+25%      → Heartbeat: 25% milestone, metrics snapshot
  T+gate2    → Checkpoint: cp_02_processed + Gate 2 log
  T+50%      → Heartbeat: 50% milestone, confidence check, cost mid-point
  T+gate3    → Checkpoint: cp_03_draft + Gate 3 log
  T+FCA      → FCA heartbeat (independent, every 30s during verification)
  T+75%      → Heartbeat: 75% milestone, completeness check
  T+gate4    → Checkpoint: cp_04_reviewed + Gate 4 log
  T+gate5    → Checkpoint: final + Gate 5 log + Quality Certificate
  T+100%     → Final Checkpoint: delivery + audit trail + cost summary
```

---

*AGENT.MD v1.0 | Deep Research Skill | Multi-Agent Orchestration Layer*
*Based on: Acceptance Framework v1.0, FactCheck System v1.0, Decomposition Guide v1.0*
*Philosophy: Every agent reports, every gate validates, every failure recovers*
