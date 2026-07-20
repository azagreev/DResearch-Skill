# Матрица трассировки — OpenResearcher reuse (R1–R3)

Сквозная связь `REQ → критерии приёмки → тесты`. Источник рекомендаций: [OPENRESEARCHER_REUSE.md](OPENRESEARCHER_REUSE.md).
Ветка: `feature/openresearcher-reuse`. Baseline (до изменений): **353 engine + 79 bench** тестов зелёные, golden-corpus PASSED, determinism byte-identical.

Легенда статуса: ⬜ не начато · 🟨 в работе · 🟩 принято (тесты зелёные) · 🟥 красное.

**Политика ошибок:** при любой ошибке (регрессия, зависание `HANG`, недостижение зелёного, major/critical findings) — параллельный root-cause агент: собрать ошибки → корневая причина (маппинг на корни A–F из [BUGLOG.md](BUGLOG.md)) → системный guard (не костыль) → лог. Не срабатывает на плановый RED в TDD.

---

## R1 — Lenient-then-strict парсинг входа на границе CLI

**Источник:** OpenResearcher `deploy_agent.py` (dual-format tool-call parsing, json5→regex fallback).
**Куда:** `engine/cli.py::_read_input` (граница, где модель подаёт JSON в движок). Downstream-обработчики уже валидируют через `_source_from`/`_claim_from`/`snapshot_from_dict` — контракт данных НЕ ослабляется.
**Тип:** pattern · **Усилия:** low · **Статус:** 🟩 принято (независимо: 8/8 новых, engine 361 OK, bench 79 OK, golden PASSED, determinism byte-identical; ревью PASS, 0 critical/major, 1 minor приемлемый)

**Реализация:** `engine/cli.py` — `_lenient_loads()` (strict-first fast path → на `JSONDecodeError` фиксированный one-shot pipeline: strip code-fence → normalize smart-quotes → strip trailing commas → re-parse), `InputParseError(ValueError)`; `main()` ловит только `InputParseError`. `model.py` не тронут — типизированная валидация downstream сохранена.

| AC | Критерий приёмки | Тест | Статус |
|----|------------------|------|--------|
| AC1.1 | Валидный JSON парсится идентично прежнему (нет изменения поведения) | `test_r1_lenient_input.py::test_ac1_1_valid_json_parses_identically` | 🟩 |
| AC1.2 | Near-valid чинится: code-fence, trailing commas, smart-quotes | `...::test_ac1_2a_markdown_code_fence_repaired`, `...::test_ac1_2b_trailing_commas_repaired`, `...::test_ac1_2c_smart_typographic_quotes_repaired` | 🟩 |
| AC1.3 | Починенный парс проходит типизированную валидацию; неверный по схеме отклоняется downstream (негативный) | `...::test_ac1_3_repaired_syntax_still_rejected_by_downstream_typed_validation` | 🟩 |
| AC1.4 | Непочинимый вход → явная ошибка (не None), ненулевой exit-code | `...::test_ac1_4_unrepairable_input_raises_explicit_error_nonzero_exit` | 🟩 |
| AC1.5 | stdlib-only, детерминизм сохранён | `...::test_ac1_5_stdlib_only_and_deterministic` + CI determinism gate | 🟩 |
| AC1.E2E | Сквозной: fenced+trailing-comma JSON через `cli run` → отчёт рендерится | `...::test_ac1_e2e_code_fence_and_trailing_comma_through_run` | 🟩 |

**Инвариант:** успешный `parse` никогда не обходит `model.validate_*` (риск §3.1) — подтверждён ревью.

---

## R2 — Verifiable-citation формат 【S†L{start}-L{end}】 + лимит дословности

**Источник:** OpenResearcher `data_utils.py` (`DEVELOPER_CONTENT`/`TOOL_CONTENT`, формат 【id†L..】, «≤10 слов дословно»).
**Куда:** `engine/ingest.py` (стабильная нумерация строк), `engine/model.py` (line-span у Claim↔Source), `engine/report.py::_cites` (рендер), `SKILL.md` (промпт-правило).
**Тип:** prompt+pattern · **Усилия:** low–med · **Статус:** 🟩 принято (независимо: 9/9 новых, engine 370 OK, bench 79 OK, golden PASSED, determinism byte-identical; ревью PASS, 0 critical/major)

**Реализация:** `ingest.py` — `_normalize_newlines` + `content_lines(source)` (стабильная 1-индексная нумерация в единственной точке); `model.py` — `Claim.citation_spans: Optional` (drop из `_jsonable` при None → байт-идентичная сериализация), валидация формы span в одной точке `_citation_spans_from`; `report.py` — `resolve_citation_spans` (кламп со следом) + `_cites` рендерит 【S†L..】/legacy; `SKILL.md` — формат + правило «≤10 слов». Без bump `CHECKPOINT_VERSION` (поле деградирует как `metadata`).

**Remediation (findings ревью, закрыто системно):** #3 malformed span → валидация формы в `_citation_spans_from` + guard `_is_citation_span` в report (класс ошибок предотвращён на границе, не костыль); #1 clamp-notes всплывают в `render_markdown` только при фактическом клампе (AC2.3 «не молчаливо» сквозняком; байт-идентичность без клампа сохранена). #2 (version bump) — принято как решение спеки.

| AC | Критерий приёмки | Тест | Статус |
|----|------------------|------|--------|
| AC2.1 | `source_from_raw` даёт стабильную нумерацию строк; ре-ingest идентичного raw → идентичная нумерация (round-trip) | `test_r2_citations.py::test_ac2_1_line_numbering_stable_across_reingest` | 🟩 |
| AC2.2 | Claim с line-span рендерит 【S1†L{a}-L{b}】; без span — legacy `[S1]` (обратная совместимость) | `...::test_ac2_2_span_renders_verifiable_citation_else_legacy` | 🟩 |
| AC2.3 | Span вне границ контента отклоняется/клампится со следом (не молчаливо) | `...::test_ac2_3_out_of_bounds_span_clamped_with_trace`, `...::test_ac2_3_malformed_span_no_crash`, `...::test_ac2_3_clamp_note_surfaced_in_render`, `...::test_ac2_3_malformed_spans_dropped_at_model_boundary` | 🟩 |
| AC2.4 | `SKILL.md` документирует формат + правило «≤10 слов дословно»; docs↔CLI reachability guard зелёный | `...::test_ac2_4_skill_md_documents_citation_format_and_quote_limit` + `test_phase15_reachability.py` | 🟩 |
| AC2.5 | Golden-output отчёта БАЙТ-в-байт неизменён, когда span нет | `...::test_ac2_5_report_byte_identical_without_span` + determinism gate | 🟩 |
| AC2.E2E | Сквозной collect→ingest→report: цитата резолвится в реальный диапазон строк источника | `...::test_ac2_e2e_collect_ingest_report_resolves_real_line_span` | 🟩 |

**Инвариант / предусловие:** стабильная нумерация строк в ingest (риск §3.2) — выполнено (единственная точка `content_lines`).

---

## R3 — Честный judge: robust parse + dual-denominator + pinned config

**Источник:** OpenResearcher `eval.py` (`GRADER_TEMPLATE`, `parse_judge_response`, `LLMJudge`, dual accuracy, PrettyTable breakdown).
**Куда:** `bench/judge/` (новый `parse.py`; расширение `collate.py`), `bench/score.py` (dual accuracy). LLM-вызов остаётся в agent/workflow-слое — движок остаётся детерминированным (см. `bench/README.md` honesty ledger).
**Тип:** code+pattern · **Усилия:** medium · **Статус:** 🟩 принято (независимо: 17/17 новых, bench 96 OK, engine 370 OK, golden PASSED, determinism byte-identical; ревью PASS, 0 critical/major)

**Реализация:** `bench/judge/parse.py` (новый) — `parse_judge_response()` (JSON fast-path → extract-before-verdict со смещением → markdown-толерантный regex вердикта; `ok=False`→unjudged через существующий `collate.build_verdicts`, переиспользует `met_from_status`); `bench/judge/config.py` (новый) — frozen `JudgeConfig(model,temperature,prompt_hash)` + `from_mapping` (presence-and-not-None, temp=0 валиден) + `prompt_hash_of` (sha256); `bench/score.py` — pure `dual_accuracy()` (аддитивно, деление-на-ноль безопасно). Весь недетерминизм/LLM остаётся в agent-слое — bench чист.

**Remediation (finding #1 ревью, закрыто системно):** import-guard сделан рекурсивным (`os.walk` вместо `os.listdir`) — будущий подпакет engine/bench, нарушающий границу, тоже будет пойман (усиление самого guard'а, не костыль). #2 (verdict-before-answer→ok=False) — принято как контракт GRADER_TEMPLATE.

| AC | Критерий приёмки | Тест | Статус |
|----|------------------|------|--------|
| AC3.1 | `parse_judge_response`: сначала `extracted_final_answer`, потом вердикт; толерантен к `**status:**`/`status:`; `ok=False` при непарсибельном (→ unjudged) | `test_r3_judge.py::ParseJudgeResponseTest::*` (extract-before-verdict, markdown, offset, unparsable, case/spacing) | 🟩 |
| AC3.2 | Dual-denominator: `judged_accuracy = met/judged` и `overall_accuracy = met/total`, breakdown {met,unmet,unjudged,total}; при всех judged обе равны | `...::DualAccuracyTest::*` (equal, partial, zero-denominators) | 🟩 |
| AC3.3 | Pinned `JudgeConfig` требует model+temperature+prompt_hash; отсутствие поля отклоняется; конфиг записан в verdicts | `...::PinnedJudgeConfigTest::*` (round-trip, missing rejected, temp0, recorded via build_verdicts) | 🟩 |
| AC3.4 | Judge вне `engine/`: `bench.judge` не импортирует движок-judge; `engine` не импортирует `bench` (рекурсивный AST import-guard, обе стороны) | `...::ImportGuardTest::test_bench_judge_does_not_import_engine`, `...::test_engine_does_not_import_bench` | 🟩 |
| AC3.5 | Детерминизм bench pure-функций сохранён | `...::DeterminismTest::*` + CI determinism gate (byte-identical) | 🟩 |

**Инвариант:** LLM-судья строго вне детерминированного движка — подтверждён рекурсивным import-guard (обе стороны).

---

## Глобальные критерии приёмки

- ✅ Все существующие тесты (353 engine + 79 bench) зелёные, 0 регрессий.
- ✅ Каждый REQ: ≥1 юнит-тест + участие в ≥1 сквозном e2e (R1.E2E, R2.E2E; R3 — через bench score-пайплайн).
- ✅ Матрица полна: нет REQ без теста, нет нового теста без REQ.
- ✅ Pre-release ревью в чистом контексте: 0 незакрытых critical/major.
- ✅ Инварианты не нарушены (см. per-REQ).
- ✅ golden-corpus regression PASSED; determinism byte-identical.

## Журнал итераций

| Итерация | REQ | Spec | Tests-red | Impl | Suite | Mini-review | Статус |
|----------|-----|------|-----------|------|-------|-------------|--------|
| 1 | R1 | 🟩 | 🟩 (8 fail, смоук 0.23с, без HANG) | 🟩 | 🟩 engine 361 / bench 79 | 🟩 PASS (1 minor) | 🟩 принято |
| 2 | R2 | 🟩 | 🟩 (6 fail, смоук 0.08с, без HANG) | 🟩 | 🟩 engine 370 / bench 79 | 🟩 PASS → 3 minor; #1/#3 закрыты remediation, #2 принята | 🟩 принято |
| 3 | R3 | 🟩 | 🟩 (смоук без HANG) | 🟩 | 🟩 bench 96 / engine 370 | 🟩 PASS → 2 minor; #1 закрыт remediation (guard рекурсивный), #2 принят | 🟩 принято |

**Итог Этапа 1:** все 3 REQ приняты. Суммарно: **engine 370 (+17 к baseline 353), bench 96 (+17 к baseline 79)**, golden PASSED, determinism byte-identical, 0 регрессий.

## Этап 2 — Pre-release ревью (чистый контекст)

Свежий агент (Opus, чистое окно; вход: diff кода R1–R3 + этот TRACE + критерии, без истории беседы). **Вердикт: GO**, 0 critical/major, 4 minor.

- **#1 (закрыто):** непреднамеренная замена em-dash→дефис в security-строке `_FENCE` и docstring `ingest.py` (scope-creep) — откачено к оригиналу.
- **#2 (закрыто системно):** `resolve_citation_spans` клампил span'ы для source не из `claim.sources` → вводящая в заблуждение заметка. Цикл ограничен `claim.sources` + добавлен guard-тест `Ac23SpanForUncitedSourceNoNoteTest`.
- **#3, #4 (приняты):** single-line answer в `parse_judge_response` и best-effort regex-repair в `_lenient_loads` — уже задокументированы в docstring, соответствуют контракту.

**Финал после remediation: engine 371, bench 96, golden PASSED, determinism byte-identical.** Готово к Этапу 3 (коммит — после одобрения пользователя).
