# Phase 1 — Data model + state: контракт (перед кодом)

> Цель Phase 1: превратить «checkpoint — placeholder / resume по инструкции» в **реальный сериализуемый
> объект** с инвариантами §8.0, проверяемыми В КОДЕ. ФОРМА (dataclasses/enums), сериализация, валидация и
> resume-инварианты — **реализованы и покрыты юнит-тестами** (`tests/test_phase1.py`, 16 тестов).
> Файлы: `engine/model.py`, `engine/state.py`. Disposition-политика (`engine/policy.py`) — сигнатура, Phase 6.

Модель **claim-центричная** и **расширяет** JSON `state`-блок из `AGENT.MD §8.0` (обратносовместимо —
только добавления). Сериализованный snapshot = тот же `state`-блок, что пишется в `cp_NN_<stage>.md`.

---

## 1. JSON-контракт snapshot (расширяет AGENT.MD §8.0)

```json
{
  "checkpoint_version": "1.0",
  "run_id": "whoop-cdek-20260609-b7e2",
  "created_utc": "2026-06-09T10:02:40Z",
  "task_fingerprint": "<sha1(normalize(question|route|depth|sorted(scope)))>",
  "stage": "cp_01_raw",
  "phase_completed": 2,
  "next_phase": 3,
  "last_gate": { "id": "G1", "verdict": "PASS" },
  "budget": { "limit_usd": 0.20, "spent_usd": 0.0, "loads_used": 4, "loads_cap": 6 },
  "task_frame": {
    "question": "...", "route": "B", "depth": "Standard",
    "scope": ["cdek.shopping"], "acceptance_criteria": ["..."],
    "language": "ru"
  },
  "subtasks": [
    { "id": "ST-1", "type": "SEARCH", "status": "done", "depends_on": [], "description": "..." }
  ],
  "sources": [
    {
      "id": "S1", "url": "https://...", "title": "...",
      "tier": "S", "fetched_via": "native_web_search", "status": "rendered",
      "created_utc": "2026-06-09T10:01:00Z", "raw_path": "raw/S1.txt", "extract": { "price": "..." },
      "published_at": "2026-06-01", "date_confidence": "high", "time_sensitive": true,
      "scores": { "authority": 0.9, "recency": 0.8, "independence": 0.7,
                  "traceability": 0.9, "corroboration": 0.6, "composite": 0.81 },
      "metadata": {}
    }
  ],
  "claims": [
    {
      "id": "C1", "text": "...", "role": "own_finding", "category": "verified", "confidence": 4,
      "sources": ["S1", "S2"], "contradicting_sources": [],
      "status": "confirmed", "cluster_id": "K1", "verdict_explanation": "..."
    }
  ],
  "clusters": [
    { "id": "K1", "title": "...", "claim_ids": ["C1","C3"], "representative_ids": ["C1"], "uncertainty": null }
  ],
  "open_items": ["cross-check Peak/One на 2-м листинге того же сайта"],
  "resume_instruction": "S1-S2 уже rendered — НЕ пере-собирать; продолжить с Phase 3 (фактчек)."
}
```

### Расширения относительно §8.0 (всё аддитивно)
| Где | Добавлено | Зачем |
|---|---|---|
| `task_frame` | `language` | язык вывода (скилл адаптируется к языку пользователя) |
| `sources[]` | `title`, `published_at`, `date_confidence`, `time_sensitive`, `scores{}` | staleness-re-verify + реальный скоринг Phase 3 |
| `claims[]` | `role`, `contradicting_sources`, `cluster_id`, `verdict_explanation` | роль claim'а (own/external) + детект противоречий + кластеры Phase 4 |
| top-level | `clusters[]` | cluster-first вывод Phase 4/6 |
| `subtasks[]` | `depends_on`, `description` | DAG зависимостей Phase 1 |

---

## 2. Перечисления (enums)

**ClaimCategory** — 6 категорий фактчека (`references/factcheck_system.md §4.1`). Имена членов UPPERCASE, **значения lowercase** (совпадают со §8.0: `"category": "verified"` → старые checkpoint'ы грузятся без алиасинга):

| Член | Значение | Label | Emoji |
|---|---|---|---|
| `VERIFIED` | `verified` | ВЕРНО | ✅ |
| `FALSE` | `false` | НЕВЕРНО | ❌ |
| `OUTDATED` | `outdated` | УСТАРЕЛО | ⏰ |
| `INCOMPLETE` | `incomplete` | НЕПОЛНО | ⚠️ |
| `OPINION` | `opinion` | ОДНА ИЗ ТОЧЕК ЗРЕНИЯ | 🔮 |
| `UNVERIFIED` | `unverified` | НЕ УДАЛОСЬ ПРОВЕРИТЬ | ❓ |

**ClaimRole** — `own_finding` (рисёрч сам утверждает) | `external_claim` (внешнее утверждение на проверке). Определяет судьбу FALSE (см. ниже).

> ⚠️ Попадание в отчёт — **НЕ** статическое свойство категории. Бывший `REPORTABLE_CATEGORIES` удалён: он ошибочно выкидывал любой FALSE, тогда как FALSE *внешнего* утверждения — это и есть смысл дебанка, а FALSE *своего вывода* должен идти на пересмотр, а не молча исчезать. Политика — роль-зависимая, в Phase 6.

### Reportability — политика Phase 6 (`engine/policy.py`)
`disposition(claim, report_mode) -> Disposition`:

| category | role | → disposition |
|---|---|---|
| `VERIFIED` | любая | `INCLUDE` |
| `OUTDATED` / `INCOMPLETE` / `OPINION` | любая | `INCLUDE_WITH_FLAG` |
| `UNVERIFIED` | любая | `INCLUDE_WITH_FLAG` (в `findings` может `EXCLUDE_BUT_RECORD`) |
| `FALSE` | `external_claim` | `INCLUDE_AS_CORRECTION` (дебанк = ценность) |
| `FALSE` | `own_finding` | `TRIGGER_REVISION` → при исчерпании `EXCLUDE_BUT_RECORD` |

`report_mode ∈ {findings, debunk, mixed}` сдвигает пограничные случаи, но **не отменяет** ветку FALSE×role. `EXCLUDE_BUT_RECORD` всегда пишет в память (Phase 5), чтобы тот же claim не всплыл снова.

Прочие enums: `Route{A,B,C,D}`, `Depth{Quick,Standard,Deep,Exhaustive}`, `Tier{S,A,B,C,D}`,
`SubTaskType{SEARCH,EXTRACT,ANALYZE,COMPARE,SYNTHESIZE,VALIDATE,FORMAT,META}`,
`SubTaskStatus{pending,in_progress,done,failed}`, `SourceStatus{pending,rendered,failed}`,
`DateConfidence{high,med,low}`, `ClaimStatus{pending,confirmed,rejected}`, `ClaimRole{own_finding,external_claim}`, `GateVerdict{PASS,WARN,FAIL}`.

**confidence** — целое 1..5 (1=Speculative … 5=Certain), визуализация ⚪🔴🟡🟢🔵.

**scores** — компоненты authority-композита (`source_authority_framework.md`), все в [0,1]:
`composite = Authority·0.30 + Recency·0.25 + Independence·0.20 + Traceability·0.15 + Corroboration·0.10`.
`None` = ещё не оценено (заполняет `score.py` в Phase 3).

---

## 3. Fingerprint

```
normalize_for_fingerprint(tf) = lower/trim/collapse-ws( tf.question | tf.route | tf.depth | sorted(tf.scope) )
compute_fingerprint(tf)       = sha1(normalize_for_fingerprint(tf)).hexdigest()
```
Детерминирован, без системных часов. Совпадение fingerprint = «та же задача» → resume; иначе → свежий прогон.

---

## 4. Инварианты resume (enforce В КОДЕ, не инструкцией)

| Инвариант (§8.0) | Функция-энфорсер (`state.py`) |
|---|---|
| fingerprint-guard: match → resume с `next_phase`; mismatch → новая run-папка, чужой checkpoint не трогаем | `resume_or_fresh()` |
| highest-NN checkpoint с fallback на NN-1 при повреждении | `find_latest_checkpoint()` |
| budget carry-forward: `spent_usd`/`loads_used` переносятся, НЕ обнуляются | `carry_budget()` |
| собранные источники READ-ONLY на resume (пере-фетч = нарушение, не оптимизация) | `assert_sources_readonly()` |
| staleness-окна по depth (Quick 24h / Standard 7d / Deep&Exhaustive 14d); `now_utc` приходит аргументом | `stale_source_ids()`, режим `RESUME_RESTALE` |

`resume_or_fresh()` возвращает `ResumeDecision{ mode: FRESH|RESUME|RESUME_RESTALE, snapshot, run_dir, stale_source_ids, reason }`.

---

## 5. Round-trip и валидация

- **Round-trip:** `snapshot_from_dict(snapshot_to_dict(s)) == s` (с точностью до dropped-None полей).
- **Версия:** неизвестный `checkpoint_version` → ошибка (не молчаливое чтение).
- **`validate_snapshot()` → список нарушений (пусто = валидно), pure, без I/O:**
  уникальность id (`S*`/`C*`/`ST*`/`K*`); `claim.sources`/`contradicting_sources` ссылаются на существующие `Source.id`;
  `confidence ∈ 1..5`; `representative_ids ⊆ claim_ids`; `next_phase ∈ 0..6`; `budget.*` неотрицательны;
  `cluster_id` claim'а ссылается на существующий кластер.

---

## 6. Atomic-запись

`save_checkpoint()` пишет `cp_NN_<stage>.md` через tmp-файл + `os.replace` (атомарно), ведущим блоком —
` ```json ` со snapshot. Чтение — `load_checkpoint()` вырезает первый json-блок и зовёт `snapshot_from_dict`.

---

## 7. Что НЕ входит в Phase 1
Скоринг (`score.py`, Phase 3), фактчек-присвоение категорий/ролей (`factcheck.py`, Phase 4), кластеризация
(`cluster.py`, Phase 4), кросс-прогонная память (`memory.py`, Phase 5), **disposition-политика**
(`engine/policy.py` — сигнатура `disposition()` уже зафиксирована, реализация в Phase 6). Phase 1 даёт
только модель данных + state-машину (сигнатуры).
