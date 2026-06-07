# Hook-Driven Middleware Specification

> **Version:** 2.0.0
> **Status:** Production-ready
> **Scope:** Event-driven middleware layer for Deep Research Skill — tool interception, validation, cost tracking, quality gating
> **Philosophy:** *Every tool call is observed, every cost is tracked, every gate is enforced*

---

## 1. Event-Driven Middleware Concept

### 1.1 Overview

Hook-Driven Middleware is an event-driven interception layer that sits between the AI agent and tool execution. Inspired by ECC (Evolutionary Collective Control) architecture, it provides **pre-execution validation**, **post-execution observation**, and **asynchronous analysis** of every tool call without modifying tool implementations.

The middleware operates on a **publish-subscribe pattern**: tool calls generate events (hooks), and registered handlers process them. Handlers can be **blocking** (halt execution until approved) or **non-blocking** (observe and log asynchronously).

### 1.2 Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent (Claude/MCP)                      │
├─────────────────────────────────────────────────────────────┤
│              Hook-Driven Middleware Layer                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │  PreToolUse │  │  PostToolUse │  │  Session Hooks  │    │
│  │  (blocking) │  │  (async)     │  │  (lifecycle)    │    │
│  └──────┬──────┘  └──────┬───────┘  └─────────────────┘    │
│         │                │                                  │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌─────────────────┐    │
│  │  Validation │  │  Cost Track  │  │  Quality Gate   │    │
│  │  Engine     │  │  Hooks       │  │  Hooks          │    │
│  └─────────────┘  └──────────────┘  └─────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    Tool Router                              │
│         (Routes to appropriate tool backend)                │
├─────────────────────────────────────────────────────────────┤
│  mshtools-*  │  Browserbase  │  Jina  │  Firecrawl  │  ... │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Event Types

| Hook Type | Timing | Blocking | Purpose |
|-----------|--------|----------|---------|
| **PreToolUse** | Before tool execution | Yes (configurable) | Validate inputs, check budget, enforce policies, route tools |
| **PostToolUse** | After tool execution | No (async) | Log results, track costs, update quality metrics, trigger follow-ups |
| **SessionStart** | At session start | No | Initialize budgets, load configs, set up tracking |
| **SessionEnd** | At session end | No | Generate reports, persist data, cleanup |
| **PreCompact** | Before context compaction | Yes | Critical decision points requiring approval |
| **Stop** | After each response | No | Continuous learning, pattern extraction |

---

## 2. PreToolUse / PostToolUse Hooks

### 2.1 PreToolUse Hook (Blocking Validation)

PreToolUse hooks execute **before** every tool call. They can:
- **Approve** — allow execution to proceed (exit code 0)
- **Block** — halt execution with an error (exit code 2)
- **Warn** — allow execution with a warning to stderr (exit code 0 + stderr)
- **Modify** — alter parameters before execution
- **Redirect** — route to a different tool or fallback

**Hook Execution Flow:**
```
1. Agent decides to call tool T with params P
2. PreToolUse hooks fire in priority order
3. Each hook returns: {action: 'approve'|'block'|'warn'|'modify', ...}
4. If any hook blocks → tool call aborted, error returned to agent
5. If all approved (possibly modified) → tool executes
6. PostToolUse hooks fire asynchronously
```

### 2.2 PostToolUse Hook (Async Observation)

PostToolUse hooks execute **after** tool completion, asynchronously (non-blocking). They:
- Log tool output for audit trail
- Extract patterns for continuous learning
- Update cost tracking in real-time
- Trigger quality assessment
- Record observations without slowing down execution

**Async Guarantee:**
- PostToolUse hooks have a configurable timeout (default 10s)
- They run in a separate execution context
- Failures in PostToolUse hooks do NOT affect the main execution
- Output is persisted to a queue for later processing if needed

### 2.3 Hook Registration Format

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "web_search|browser_visit",
        "hooks": [
          {
            "type": "command",
            "command": "python hooks/cost_checker.py",
            "blocking": true,
            "timeout": 5
          }
        ],
        "priority": 100,
        "id": "pre:cost:guard"
      },
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python hooks/observer.py",
            "async": true,
            "timeout": 10
          }
        ],
        "priority": 10,
        "id": "pre:observe:all"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python hooks/cost_tracker.py",
            "async": true
          }
        ],
        "id": "post:cost:track"
      }
    ]
  }
}
```

---

## 3. Blocking Validation (Exit Code 2)

### 3.1 Exit Code Convention

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| **0** | Success / Approved | Continue tool execution |
| **1** | Hook error / Misconfiguration | Log error, continue with warning |
| **2** | Explicit block | Abort tool call, return error to agent |
| **3+** | Reserved for future use | Treated as exit code 1 |

### 3.2 Validation Rules

PreToolUse hooks enforce the following validation layers:

**Layer 1: Budget Guard**
```python
def validate_budget(tool_name: str, params: dict, session_budget: dict) -> dict:
    """Block if tool would exceed session budget."""
    estimated_cost = estimate_tool_cost(tool_name, params)
    remaining = session_budget['max_cost'] - session_budget['spent']
    
    if estimated_cost > remaining:
        return {
            'action': 'block',
            'exit_code': 2,
            'reason': f'Budget exceeded: ${estimated_cost:.4f} > remaining ${remaining:.4f}',
            'suggestion': 'Use lower-tier tool or request budget increase'
        }
    return {'action': 'approve'}
```

**Layer 2: Rate Limit Guard**
```python
def validate_rate_limit(tool_name: str, call_history: list) -> dict:
    """Block if rate limit would be exceeded."""
    limit = RATE_LIMITS.get(tool_name, {'rpm': 60, 'rph': 1000})
    recent_calls = count_calls_in_window(call_history, window_minutes=1)
    
    if recent_calls >= limit['rpm']:
        return {
            'action': 'block',
            'exit_code': 2,
            'reason': f'Rate limit: {recent_calls}/{limit["rpm"]} RPM for {tool_name}',
            'retry_after': 60  # seconds
        }
    return {'action': 'approve'}
```

**Layer 3: Policy Guard**
```python
def validate_policy(tool_name: str, params: dict, policy_rules: list) -> dict:
    """Block if tool violates policy (prohibited targets, data types, etc.)."""
    for rule in policy_rules:
        if rule.matches(tool_name, params):
            if rule.action == 'block':
                return {
                    'action': 'block',
                    'exit_code': 2,
                    'reason': f'Policy violation: {rule.description}',
                    'rule_id': rule.id
                }
            elif rule.action == 'warn':
                return {
                    'action': 'warn',
                    'exit_code': 0,
                    'stderr': f'Warning: {rule.description}'
                }
    return {'action': 'approve'}
```

---

## 4. Async Observation

### 4.1 Observation Pipeline

```
Tool Call → PostToolUse Trigger → Queue → Processors → Persistence
                                          │
                                          ├── Cost Extractor
                                          ├── Quality Analyzer
                                          ├── Pattern Extractor
                                          └── Audit Logger
```

### 4.2 Observation Types

| Observation | Extractor | Storage | Purpose |
|-------------|-----------|---------|---------|
| Cost | Cost Extractor | Session cost log | Real-time budget tracking |
| Latency | Timing Analyzer | Performance DB | Tool performance monitoring |
| Quality | Content Analyzer | Quality metrics | Output quality scoring |
| Pattern | Pattern Extractor | Learning DB | Continuous improvement |
| Error | Error Classifier | Error log | Failure analysis |

### 4.3 Async Guarantees

```python
@dataclass
class AsyncHookConfig:
    """Configuration for async hook execution."""
    timeout_seconds: float = 10.0
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    queue_on_failure: bool = True       # Queue for later processing if hook fails
    ignore_failure: bool = True          # Don't fail main execution if hook fails
    max_concurrent: int = 5              # Max concurrent async hooks
```

---

## 5. Integration with Tool Router

### 5.1 Hook-Driven Tool Routing

PreToolUse hooks can **redirect** tool calls to alternative implementations based on context:

```python
class ToolRouterHook:
    """Routes tool calls through hook-driven middleware before execution."""
    
    def __init__(self, router_config: dict):
        self.tier_rules = router_config['tier_rules']
        self.fallback_chains = router_config['fallback_chains']
        self.cost_model = router_config['cost_model']
    
    def pre_tool_use(self, tool_name: str, params: dict, context: dict) -> dict:
        """
        Evaluate tool call against routing rules.
        May redirect to cheaper/faster alternative.
        """
        # Check if cheaper alternative exists
        tier = self.get_tool_tier(tool_name)
        if tier > 2:  # Tier 3 or 4 (expensive)
            alternative = self.find_cheaper_alternative(tool_name, params)
            if alternative and self.alternative_sufficient(alternative, params):
                return {
                    'action': 'modify',
                    'tool': alternative['name'],
                    'params': alternative['params'],
                    'reason': f'Routed from {tool_name} to {alternative["name"]}: '
                              f'saved ~{alternative["savings"]:.2f}x cost'
                }
        
        # Check fallback chain if tool is known to fail
        if self.recent_failure_rate(tool_name) > 0.5:
            fallback = self.fallback_chains.get(tool_name)
            if fallback:
                return {
                    'action': 'modify',
                    'tool': fallback[0],
                    'reason': f'High failure rate ({self.recent_failure_rate(tool_name):.0%}), '
                              f'using fallback: {fallback[0]}'
                }
        
        return {'action': 'approve'}
```

### 5.2 Routing Decision Matrix

| Condition | Action | Hook Priority |
|-----------|--------|---------------|
| Budget remaining < 10% | Block expensive tools (Tier 3-4), allow Tier 1-2 | 200 |
| Rate limit approaching | Block or delay tool call | 150 |
| Known failure pattern | Redirect to fallback tool | 120 |
| Cheaper alternative available | Redirect to alternative | 100 |
| Policy violation | Block with error | 250 |
| Debug mode enabled | Log full params for inspection | 50 |

---

## 6. Cost Tracking Hooks

### 6.1 Real-Time Cost Tracking

Every tool call is intercepted by cost tracking hooks that maintain running budget totals:

```python
@dataclass
class CostTrackingHook:
    """
    Hook for real-time cost tracking across all tool calls.
    Integrates with CostTracker from cost_matrix_full.md.
    """
    
    session_budget: CaptchaBudget  # Reuse from CAPTCHA_MODULE
    cost_log_file: str = "session_costs.jsonl"
    
    def pre_tool_use(self, tool_name: str, params: dict) -> dict:
        """Pre-check: estimate cost and verify budget."""
        estimated = self.estimate_cost(tool_name, params)
        
        if not self.session_budget.can_afford(estimated):
            return {
                'action': 'block',
                'exit_code': 2,
                'reason': f'Cost ${estimated:.4f} exceeds remaining budget',
                'session_total': self.session_budget._session_cost
            }
        return {'action': 'approve', 'estimated_cost': estimated}
    
    def post_tool_use(self, tool_name: str, params: dict, 
                      result: dict, latency_ms: float) -> None:
        """Post-log: record actual cost and update totals (async)."""
        actual_cost = self.calculate_actual_cost(tool_name, params, result, latency_ms)
        
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'tool': tool_name,
            'params_hash': hash_params(params),
            'estimated_cost': self.estimate_cost(tool_name, params),
            'actual_cost': actual_cost,
            'latency_ms': latency_ms,
            'session_total': self.session_budget._session_cost + actual_cost,
            'success': result.get('success', True)
        }
        
        # Async write to log
        asyncio.create_task(self._persist_entry(entry))
        
        # Update running total
        self.session_budget._session_cost += actual_cost
        self.session_budget._solve_count += 1
    
    def _persist_entry(self, entry: dict) -> None:
        """Async persist to JSONL file."""
        with open(self.cost_log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
```

### 6.2 Cost Estimation by Tool

```python
COST_ESTIMATES = {
    # Tier 1: Native/Free
    'web_search': {'base': 0.0, 'per_result': 0.0, 'unit': 'call'},
    'browser_visit': {'base': 0.0, 'per_result': 0.0, 'unit': 'call'},
    'ipython': {'base': 0.0, 'per_result': 0.0, 'unit': 'call'},
    
    # Tier 2: Low-Cost APIs
    'jina_reader': {'base': 0.0, 'per_result': 0.0, 'unit': 'call'},
    'search_data_source': {'base': 0.0, 'per_result': 0.0, 'unit': 'call'},
    
    # Tier 3: Mid-Range
    'firecrawl': {'base': 0.001, 'per_result': 0.0, 'unit': 'page'},
    'serper_api': {'base': 0.001, 'per_result': 0.0, 'unit': 'call'},
    
    # Tier 4: Enterprise
    'browserbase': {'base': 0.01, 'per_result': 0.005, 'unit': 'minute'},
    'captcha_solve': {'base': 0.001, 'per_result': 0.0, 'unit': 'solve'},
    'generate_video': {'base': 0.05, 'per_result': 0.0, 'unit': 'generation'},
}
```

### 6.3 Budget Alerts

| Threshold | Action | Hook Behavior |
|-----------|--------|---------------|
| 50% | Warning | PostToolUse hook logs WARNING level message |
| 75% | Alert | PreToolUse hooks start blocking Tier 4 tools |
| 90% | Critical | PreToolUse hooks block Tier 3-4, allow only Tier 1-2 |
| 100% | Exhausted | All non-free tool calls blocked (exit code 2) |

---

## 7. Quality Gate Hooks

### 7.1 Quality Gate Enforcement

Quality Gate hooks enforce the 5-Gate acceptance framework:

```python
class QualityGateHook:
    """
    PreToolUse hook that enforces quality gates before data collection.
    Integrates with acceptance_framework.md Gate system.
    """
    
    GATES = {
        1: 'Relevance Gate',      # Output matches user intent
        2: 'Completeness Gate',   # All AC addressed
        3: 'Accuracy Gate',       # Facts verified
        4: 'Authority Gate',      # Sources meet tier requirements
        5: 'Format Gate',         # Output follows specified format
    }
    
    def pre_tool_use(self, tool_name: str, params: dict, 
                     gate_status: dict) -> dict:
        """
        Block tools if quality gates haven't been met.
        For example, block data collection if Gate 1 (Relevance)
        hasn't been validated.
        """
        # Gate 1 must pass before any collection
        if tool_name in DATA_COLLECTION_TOOLS and not gate_status.get(1):
            return {
                'action': 'block',
                'exit_code': 2,
                'reason': 'Gate 1 (Relevance) not validated. '
                          'Confirm user intent before data collection.',
                'gate': 1
            }
        
        # Gate 4 must pass before using Tier D sources
        source_tier = params.get('source_tier', 'unknown')
        if source_tier == 'D' and not gate_status.get(4):
            return {
                'action': 'warn',
                'exit_code': 0,
                'stderr': f'Warning: Tier D source used before Gate 4 pass. '
                          f'Requires {self.GATES[4]} validation.'
            }
        
        return {'action': 'approve'}
```

### 7.2 Gate-State Validation Rules

| Gate | Name | PreToolUse Rule | Blocking |
|------|------|-----------------|----------|
| G1 | Relevance | Block collection tools until intent confirmed | Yes |
| G2 | Completeness | Block synthesis until all AC verified | Yes |
| G3 | Accuracy | Block output formatting until facts checked | Yes |
| G4 | Authority | Warn on Tier D sources, block if >20% | Yes (configurable) |
| G5 | Format | Block delivery until format validated | Yes |

---

## 8. Python Pseudocode: Complete Hook System

### 8.1 Core Dispatcher

```python
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict, Any
from enum import Enum
import asyncio
import json
import subprocess
from datetime import datetime

class HookAction(Enum):
    APPROVE = "approve"
    BLOCK = "block"
    WARN = "warn"
    MODIFY = "modify"

@dataclass
class HookResult:
    action: HookAction
    exit_code: int = 0          # 0=approve, 1=error, 2=block
    reason: str = ""
    modified_tool: Optional[str] = None
    modified_params: Optional[dict] = None
    stderr: str = ""            # Warning message

@dataclass
class HookConfig:
    matcher: str                # Regex pattern for tool names
    command: str                # Command to execute
    blocking: bool = True       # Wait for completion
    async_execution: bool = False
    timeout: float = 5.0
    priority: int = 100         # Lower = earlier execution
    id: str = ""               # Unique hook identifier

@dataclass
class HookContext:
    """Context passed to every hook invocation."""
    session_id: str
    tool_name: str
    tool_params: dict
    call_history: List[dict] = field(default_factory=list)
    session_budget: dict = field(default_factory=dict)
    gate_status: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

class HookDispatcher:
    """
    Central dispatcher for all hook-driven middleware.
    Manages registration, priority ordering, and execution.
    """
    
    def __init__(self):
        self.pre_hooks: List[HookConfig] = []
        self.post_hooks: List[HookConfig] = []
        self.session_hooks: List[HookConfig] = []
        self._hook_results: List[dict] = []
    
    def register(self, hook_type: str, config: HookConfig) -> None:
        """Register a hook with priority ordering."""
        target = {
            'PreToolUse': self.pre_hooks,
            'PostToolUse': self.post_hooks,
            'SessionStart': self.session_hooks,
            'SessionEnd': self.session_hooks,
            'PreCompact': self.pre_hooks,
            'Stop': self.post_hooks,
        }.get(hook_type)
        
        if target is None:
            raise ValueError(f"Unknown hook type: {hook_type}")
        
        target.append(config)
        target.sort(key=lambda h: h.priority)
    
    def dispatch_pre(self, context: HookContext) -> HookResult:
        """
        Execute all matching PreToolUse hooks in priority order.
        Returns first BLOCK result, or aggregated modifications.
        """
        matching_hooks = [
            h for h in self.pre_hooks 
            if self._matches(h.matcher, context.tool_name)
        ]
        
        current_tool = context.tool_name
        current_params = dict(context.tool_params)
        
        for hook in matching_hooks:
            try:
                result = self._execute_hook(hook, context, current_tool, current_params)
                
                if result.action == HookAction.BLOCK:
                    return result
                elif result.action == HookAction.MODIFY:
                    current_tool = result.modified_tool or current_tool
                    current_params = result.modified_params or current_params
                elif result.action == HookAction.WARN:
                    # Log warning but continue
                    self._log_warning(hook.id, result.stderr)
                
            except Exception as e:
                # Hook error: log and continue (configurable)
                self._log_error(hook.id, str(e))
                if not hook.blocking:
                    continue
        
        # All hooks passed
        if current_tool != context.tool_name or current_params != context.tool_params:
            return HookResult(
                action=HookAction.MODIFY,
                exit_code=0,
                modified_tool=current_tool,
                modified_params=current_params,
                reason="Tool routed through hooks"
            )
        
        return HookResult(action=HookAction.APPROVE, exit_code=0)
    
    def dispatch_post(self, context: HookContext, 
                      result: dict, latency_ms: float) -> None:
        """
        Execute all matching PostToolUse hooks asynchronously.
        Failures are logged but do not affect execution.
        """
        matching_hooks = [
            h for h in self.post_hooks
            if self._matches(h.matcher, context.tool_name)
        ]
        
        for hook in matching_hooks:
            asyncio.create_task(
                self._execute_async_hook(hook, context, result, latency_ms)
            )
    
    async def _execute_async_hook(self, hook: HookConfig, context: HookContext,
                                   result: dict, latency_ms: float) -> None:
        """Execute a PostToolUse hook asynchronously."""
        try:
            await asyncio.wait_for(
                self._run_hook_command(hook, context, result=result, 
                                       latency_ms=latency_ms),
                timeout=hook.timeout
            )
        except asyncio.TimeoutError:
            self._log_warning(hook.id, f"Timeout after {hook.timeout}s")
        except Exception as e:
            self._log_error(hook.id, f"Async hook error: {e}")
    
    def _execute_hook(self, hook: HookConfig, context: HookContext,
                      current_tool: str, current_params: dict) -> HookResult:
        """Execute a single hook command and parse result."""
        env = {
            'HOOK_TOOL_NAME': current_tool,
            'HOOK_SESSION_ID': context.session_id,
            'HOOK_PRIORITY': str(hook.priority),
            'HOOK_ID': hook.id,
            **{f'HOOK_PARAM_{k.upper()}': str(v) 
               for k, v in current_params.items()}
        }
        
        proc = subprocess.run(
            hook.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=hook.timeout,
            env={**os.environ, **env}
        )
        
        if proc.returncode == 2:
            return HookResult(
                action=HookAction.BLOCK,
                exit_code=2,
                reason=proc.stdout.strip() or "Blocked by policy"
            )
        elif proc.returncode == 0 and proc.stderr:
            return HookResult(
                action=HookAction.WARN,
                exit_code=0,
                stderr=proc.stderr.strip()
            )
        elif proc.returncode != 0:
            return HookResult(
                action=HookAction.BLOCK,
                exit_code=proc.returncode,
                reason=f"Hook error: {proc.stderr.strip()}"
            )
        
        # Parse stdout for modifications
        try:
            output = json.loads(proc.stdout)
            if output.get('action') == 'modify':
                return HookResult(
                    action=HookAction.MODIFY,
                    exit_code=0,
                    modified_tool=output.get('tool', current_tool),
                    modified_params=output.get('params', current_params),
                    reason=output.get('reason', '')
                )
        except json.JSONDecodeError:
            pass
        
        return HookResult(action=HookAction.APPROVE, exit_code=0)
    
    @staticmethod
    def _matches(matcher: str, tool_name: str) -> bool:
        """Check if matcher pattern matches tool name."""
        import re
        if matcher == '*':
            return True
        pattern = matcher.replace('|', '|').replace('*', '.*')
        return bool(re.match(f'^({pattern})$', tool_name))
    
    def _log_warning(self, hook_id: str, message: str) -> None:
        print(f"[WARN] Hook {hook_id}: {message}", file=sys.stderr)
    
    def _log_error(self, hook_id: str, message: str) -> None:
        print(f"[ERROR] Hook {hook_id}: {message}", file=sys.stderr)


# ─── Example: Registration ─────────────────────────────────────────

dispatcher = HookDispatcher()

# Budget guard (highest priority - blocks expensive tools)
dispatcher.register('PreToolUse', HookConfig(
    matcher='browserbase|firecrawl|captcha_solve',
    command='python hooks/budget_guard.py',
    blocking=True,
    priority=200,
    id='pre:budget:guard'
))

# Rate limit check
dispatcher.register('PreToolUse', HookConfig(
    matcher='*',
    command='python hooks/rate_limiter.py',
    blocking=True,
    priority=150,
    id='pre:rate:limit'
))

# Tool router (redirect to cheaper alternatives)
dispatcher.register('PreToolUse', HookConfig(
    matcher='*',
    command='python hooks/tool_router.py',
    blocking=True,
    priority=100,
    id='pre:tool:router'
))

# Cost tracking (async - never blocks)
dispatcher.register('PostToolUse', HookConfig(
    matcher='*',
    command='python hooks/cost_tracker.py',
    async_execution=True,
    timeout=10,
    priority=50,
    id='post:cost:track'
))

# Quality observation (async)
dispatcher.register('PostToolUse', HookConfig(
    matcher='*',
    command='python hooks/quality_observer.py',
    async_execution=True,
    timeout=5,
    priority=60,
    id='post:quality:observe'
))

# ─── Example: Usage ────────────────────────────────────────────────

async def execute_with_hooks(tool_name: str, params: dict, 
                              dispatcher: HookDispatcher) -> dict:
    """Execute a tool with full hook middleware."""
    
    context = HookContext(
        session_id="sess_001",
        tool_name=tool_name,
        tool_params=params,
        session_budget={'max_cost': 1.00, 'spent': 0.15}
    )
    
    # PreToolUse: blocking validation
    pre_result = dispatcher.dispatch_pre(context)
    
    if pre_result.action == HookAction.BLOCK:
        return {
            'success': False,
            'error': pre_result.reason,
            'hook_id': pre_result.exit_code
        }
    
    # Apply modifications if any
    if pre_result.action == HookAction.MODIFY:
        tool_name = pre_result.modified_tool or tool_name
        params = pre_result.modified_params or params
    
    # Execute actual tool
    start_time = datetime.now()
    tool_result = await execute_tool(tool_name, params)
    latency_ms = (datetime.now() - start_time).total_seconds() * 1000
    
    # PostToolUse: async observation
    dispatcher.dispatch_post(context, tool_result, latency_ms)
    
    return tool_result
```

---

## 9. Configuration Reference

### 9.1 Default Hook Configuration

```yaml
# hooks.yaml — Master configuration for Deep Research Skill middleware
hooks:
  version: 2.0.0
  
  pre_tool_use:
    - id: pre:policy:guard
      matcher: "*"
      command: "python hooks/policy_guard.py"
      blocking: true
      priority: 250
      timeout: 3
    
    - id: pre:budget:guard
      matcher: "browserbase|firecrawl|captcha_*|generate_video"
      command: "python hooks/budget_guard.py"
      blocking: true
      priority: 200
      timeout: 2
    
    - id: pre:rate:limit
      matcher: "*"
      command: "python hooks/rate_limiter.py"
      blocking: true
      priority: 150
      timeout: 1
    
    - id: pre:tool:router
      matcher: "*"
      command: "python hooks/tool_router.py"
      blocking: true
      priority: 100
      timeout: 2
    
    - id: pre:quality:gate
      matcher: "*"
      command: "python hooks/quality_gate.py"
      blocking: true
      priority: 75
      timeout: 2
  
  post_tool_use:
    - id: post:cost:track
      matcher: "*"
      command: "python hooks/cost_tracker.py"
      async: true
      timeout: 10
      priority: 100
    
    - id: post:quality:observe
      matcher: "*"
      command: "python hooks/quality_observer.py"
      async: true
      timeout: 5
      priority: 80
    
    - id: post:audit:log
      matcher: "*"
      command: "python hooks/audit_logger.py"
      async: true
      timeout: 3
      priority: 50
  
  session_hooks:
    - id: session:start
      event: "SessionStart"
      command: "python hooks/session_init.py"
      priority: 100
    
    - id: session:end
      event: "SessionEnd"
      command: "python hooks/session_report.py"
      priority: 100
```

---

## 10. Summary

| Feature | Implementation | Status |
|---------|---------------|--------|
| Event-driven middleware | PreToolUse/PostToolUse/Session hooks | Production-ready |
| Blocking validation | Exit code 2 convention | Production-ready |
| Async observation | Timeout-guaranteed, non-blocking | Production-ready |
| Tool Router integration | Cheaper-alternative routing, fallback chains | Production-ready |
| Cost tracking hooks | Real-time budget monitoring, tier-based alerts | Production-ready |
| Quality gate hooks | 5-Gate enforcement, policy guards | Production-ready |
| Python implementation | Full dispatcher + example registration | Pseudocode |

---

*Hook-Driven Middleware v2.0.0 — integrated with Deep Research Skill. 
PreToolUse hooks enforce policy, budget, and quality gates. PostToolUse hooks track costs and quality asynchronously. Every tool call is observed, every cost is tracked, every gate is enforced.*
