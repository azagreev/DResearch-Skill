# Матрица трассировки — Hyperresearch reuse (H1–H7)

Сквозная связь `REQ → критерии приёмки → тесты`. Источник рекомендаций:
[HYPERRESEARCH_REUSE.md](HYPERRESEARCH_REUSE.md).
Целевой релиз: **v1.7.0**. Baseline (до изменений): **engine 371 + bench 96**,
golden PASSED, determinism byte-identical.
Итог: **engine 428 (+57), bench 96**, golden PASSED, determinism byte-identical, 0 регрессий.

Легенда: ⬜ не начато · 🟨 в работе · 🟩 принято (тесты зелёные) · 🟥 красное.

**Политика ошибок:** при любой ошибке — параллельный root-cause агент: собрать →
корневая причина → системный guard (не костыль) → лог. Не срабатывает на плановый RED.
**Процесс на REQ:** Spec(Opus) → Tests-red(Sonnet) → Implement(Sonnet) →
Review(Opus, чистый контекст) + условный parallel root-cause. Smoke-first +
`Start-Job`/`Wait-Job` таймауты. Между итерациями — независимая верификация в main-loop.

---

## H1 — Механический quote-integrity gate (движок)
**Куда:** `engine/quoteintegrity.py` (новый), `engine/report.py` (гейт), `engine/cli.py` (`quotecheck`). **Статус:** 🟩 принято (10 тестов; ревью NO-GO→GO после remediation)

**Реализация:** дословная цитата из текста claim обязана присутствовать в
`content_lines[span]` цитируемого источника; scope — только claim'ы со `citation_spans`
(R2-opt-in), поэтому legacy/golden байт-идентичны. Mismatched **own-finding** исключается
из отчёта + surfaced note (текст непроверенной цитаты НЕ печатается).

**Remediation (ревью, закрыто системно):** MAJOR — гейт был disposition-слепым и
глушил debunk'и (INCLUDE_AS_CORRECTION). Фикс: корректировки не подавляются никогда
(гейт защищает только own-findings); note только для реально заблокированных findings;
дедуп вложенных цитат. Root cause отдельно: UTF-8/cp1252 в subprocess-тестах →
`encoding="utf-8"` (системный guard).

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC1.1 | Верная цитата в span проходит | `test_h1_quote_integrity.py::Ac11SupportedQuotePassesTest` | 🟩 |
| AC1.2 | Фейковая/вне-span цитата → mismatch | `...::Ac12FabricatedQuoteFlaggedTest` | 🟩 |
| AC1.3 | FINDINGS hard-block + note; debunk НЕ подавляется; note только для blocked findings | `...::Ac13FindingsHardBlockTest`, `Ac13DebunkNotSuppressedTest`, `Ac13NoteOnlyForBlockedFindingsTest` | 🟩 |
| AC1.4 | Legacy без span — байт-в-байт | `...::Ac14LegacyByteIdenticalTest` | 🟩 |
| AC1.5 | stdlib + детерминизм | `...::Ac15DeterminismAndStdlibTest` + determinism gate | 🟩 |
| AC1.E2E | `engine quotecheck` флагает фейк | `...::Ac1E2ESubprocessTest` | 🟩 |

## H2 — Вычисляемая source independence (движок)
**Куда:** `engine/independence.py` (новый), `engine/factcheck.py` (тайбрейкер), `engine/cli.py` (`independence`). **Статус:** 🟩 принято (10 тестов; ревью GO + hardening)

**Реализация:** union-find по near-dup телу (Jaccard≥0.70) + canonical-URL → каждый
источник `1/cluster_size` в компонент independence (вес 0.20) → ниже composite/tier/
confidence без переписывания ladder. `consensus_strength` (5 перепечаток ≈ 1 голос).
Тайбрейкер в `resolve_conflict` (Tier>freshness>independence>quantity), закрыл
расхождение SKILL.md:104↔код. Verb opt-in → run_pipeline/golden не тронуты.

**Hardening (ревью MINOR-1/2):** тайбрейкер срабатывает только если ОБЕ стороны имеют
≥1 заскоренный independence (`is not None`), иначе no-op — не «побеждать» из-за
незаскоренной стороны. + boundary-тест против ложной синдикации.

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC2.1 | Детерминизм + order-independent | `test_h2_independence.py::Ac21DeterministicOrderIndependentTest` | 🟩 |
| AC2.2 | N перепечаток → 1/N; distinct → 1.0; нет ложной синдикации | `...::Ac22ReprintsClusterTest`, `Ac22NoFalseSyndicationTest` | 🟩 |
| AC2.3 | consensus_strength: перепечатки ≈ 1 голос | `...::Ac23ConsensusStrengthTest` | 🟩 |
| AC2.4 | Порог конфигурируем; safe default не занижает | `...::Ac24ThresholdAndSafeDefaultTest` | 🟩 |
| AC2.5 | Тайбрейкер использует independence; no-op без сигнала | `...::Ac25ResolveConflictTiebreakerTest` | 🟩 |
| AC2.6 | Байт-идентичность (fill-when-None, verb opt-in) | `...::Ac24...::test_apply_does_not_overwrite...` + determinism gate | 🟩 |

## H3 — Retraction flag-and-veto (движок, offline)
**Куда:** `model.Source.retracted`, `engine/retraction.py` (новый), `engine/factcheck.py` (veto), `engine/cli.py` (`retraction`). **Статус:** 🟩 принято (11 тестов; ревью GO + MAJOR remediation)

**Реализация:** `Source.retracted: Optional[bool]=None` (drop-when-None → байт-идентичность
checkpoint'ов). Отозванный источник исключается из support **и** contradicting в
`classify_claim` (если claim явно не acknowledges отзыв). Детектор языка отзыва (en+ru) +
`mark_retractions` (opt-in). Hot-path вето — по флагу (нулевой false-positive).

**Remediation (ревью MAJOR):** отозванный источник сохранял вето-силу на contradicting-
стороне (мог толкнуть валидный claim в FALSE/OUTDATED) → симметричный strip на обе стороны.

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC3.1 | retracted-only support → UNVERIFIED; валидный ко-цитат выживает; retracted-contradictor не фальсифицирует | `test_h3_retraction.py::Ac31RetractedSourceVetoedTest`, `Ac31RetractedContradictorTest` | 🟩 |
| AC3.2 | Детектор + mark_retractions | `...::Ac32DetectorMarksSourcesTest` | 🟩 |
| AC3.3 | Acknowledgment снимает вето | `...::Ac33AcknowledgmentLiftsVetoTest` | 🟩 |
| AC3.4 | Offline + детерминизм | `...::Ac34DeterminismTest` | 🟩 |
| AC3.5 | Байт-в-байт при отсутствии отзыва | `...::Ac35ByteIdentityTest` + determinism gate | 🟩 |

## H6 — Numeric-consistency (движок)
**Куда:** `engine/numeric.py` (новый), `engine/cli.py` (`numcheck`). **Статус:** 🟩 принято (8 тестов; ревью — в pre-release)

**Реализация:** число из claim подтверждено, если его цифровая последовательность
встречается в цитируемом источнике (с учётом span). Read-only verb, не вплетён в render →
отчёт всегда байт-идентичен.

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC6.1 | Трассируемое число проходит | `test_h6_numeric.py::Ac61TraceableNumberPassesTest` | 🟩 |
| AC6.2 | Нетрассируемое/вне-span → флаг | `...::Ac62UntraceableNumberFlaggedTest` | 🟩 |
| AC6.3 | Детерминизм | `...::Ac63DeterminismTest` | 🟩 |
| AC6.4 | Report не импортирует numeric (байт-идентичность) | `...::Ac64ReportUntouchedTest` | 🟩 |

## H7 — Scale-as-config-profile (движок)
**Куда:** `engine/profiles.py` (новый), `engine/plan.py` (MAX_CONCURRENT из профиля), `engine/cli.py` (`profile`). **Статус:** 🟩 принято (6 тестов; ревью — в pre-release)

**Реализация:** frozen `Profile` со scale-кнобами + порогами гейтов; built-in по глубине
(quick/standard/deep/exhaustive), `extends`-оверлей, unknown-ключи игнорируются;
golden-pinned дефолты = историческим литералам. `plan.MAX_CONCURRENT` берётся из
`profiles.DEFAULT` (значение 5 неизменно).

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC7.1 | Load + ignore-unknown | `test_h7_profiles.py::Ac71LoadIgnoreUnknownTest` | 🟩 |
| AC7.2 | `extends` наследование | `...::Ac72ExtendsTest` | 🟩 |
| AC7.3 | Движок читает порог из профиля | `...::Ac73EngineReadsFromProfileTest` | 🟩 |
| AC7.4 | Golden-pinned дефолты | `...::Ac74GoldenPinnedDefaultsTest` | 🟩 |
| AC7.5 | Детерминизм | `...::Ac75DeterminismTest` | 🟩 |

## H5 — Instruction + dialectic критики (skill-слой + движок)
**Куда:** `engine/instrcov.py` (новый, механическое ядро), `engine/cli.py` (`instrcheck`), `SKILL.md` (методология). **Статус:** 🟩 принято (7 тестов; ревью — в pre-release)

**Реализация:** instruction-critic имеет **детерминированное ядро в движке** —
`uncovered_criteria` помечает пункты acceptance_criteria/scope без покрытия (нулевое
пересечение значимых терминов с claim'ами/кластерами). Read-only. Dialectic-critic —
семантический review-проход в agent-слое (LLM вне детерминированного движка).

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC5.1 | Read-only (report не импортирует instrcov) | `test_h5_instruction.py::Ac51ReadOnlyTest` | 🟩 |
| AC5.2 | Ловит пропуск пункта декомпозиции (criteria/scope) | `...::Ac52UncoveredCriterionFlaggedTest`, `Ac52CoveredCriterionNotFlaggedTest` | 🟩 |
| AC5.3 | Dialectic — семантический проход (agent-слой, задокументирован) | SKILL.md «Adversarial review (H5)» | 🟩 |
| AC5.4 | Edge/детерминизм | `...::Ac54EdgeAndDeterminismTest` | 🟩 |

## H4 — Patch-never-regenerate (skill-слой)
**Куда:** `SKILL.md` (дисциплина) + структурный guard. **Статус:** 🟩 принято (4 теста; ревью — в pre-release)

**Реализация:** SKILL.md документирует: пост-факт-чек правки только через `[Read, Edit]`
точечными hunk'ами, отчёт не перегенерируется; finding не влезает → эскалация
`policy.TRIGGER_REVISION`; неприменённый critical блокирует ship. Guard-тест не даёт
молча удалить дисциплину из прозы.

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC4.1 | Секция + tool-lock `[Read, Edit]` | `test_h4_patch_discipline.py::...::test_ac41_section_and_tool_lock_present` | 🟩 |
| AC4.2 | Hunk-cap задокументирован | `...::test_ac42_per_hunk_cap_documented` | 🟩 |
| AC4.3 | Эскалация не молчаливая; critical блокирует ship | `...::test_ac43_escalation_not_silent_rewrite` | 🟩 |
| AC4.4 | Guard non-vacuous | `...::test_guard_is_non_vacuous` | 🟩 |

---

## Глобальные критерии приёмки
- ✅ Все существующие тесты зелёные, 0 регрессий (engine 371→428, bench 96).
- ✅ Каждый REQ: ≥1 юнит-тест; e2e где применимо (H1.E2E; verbs через reachability smoke).
- ✅ Матрица полна: нет REQ без теста, нет теста без REQ.
- ✅ golden-corpus PASSED; determinism byte-identical (trust+quality).
- ✅ Новые verb'ы reachable (CAPABILITY_VERBS ↔ CURATED_CAPABILITIES ↔ docs↔CLI guard).

## Журнал итераций
| REQ | Tests-red | Impl | Suite | Review | Статус |
|-----|-----------|------|-------|--------|--------|
| H1 | 🟩 (RED, смоук без HANG) | 🟩 | 🟩 engine 379 | 🟩 NO-GO→GO (MAJOR debunk закрыт системно) | 🟩 |
| H6 | 🟩 | 🟩 | 🟩 engine 387 | ⏳ pre-release | 🟩 |
| H2 | 🟩 | 🟩 | 🟩 engine 398 | 🟩 GO + hardening (MINOR-1/2) | 🟩 |
| H3 | 🟩 | 🟩 | 🟩 engine 408→416 | 🟩 GO + MAJOR remediation (contradicting strip) | 🟩 |
| H7 | 🟩 | 🟩 | 🟩 engine 416 | ⏳ pre-release | 🟩 |
| H5 | 🟩 | 🟩 | 🟩 engine 423 | ⏳ pre-release | 🟩 |
| H4 | 🟩 | 🟩 | 🟩 engine 427 | ⏳ pre-release | 🟩 |

## Pre-release ревью (чистый контекст)

Свежий агент (чистое окно; вход: список изменений + этот TRACE + AC; фокус на H4/H5/H6/H7 без отдельного ревью + сквозные инварианты). **Вердикт: GO**, 0 critical, 0 major, 5 minor.

- **MINOR-1 (закрыто):** `profile` verb падал `KeyError` на неизвестном `extends`. Фикс: резолв через `get_profile(ext)` (unknown → DEFAULT, консистентно) + тест `test_unknown_extends_falls_back_to_default`.
- **MINOR-2/-3 (numeric leniency / merge пробелом), MINOR-4 (H4 guard = doc-presence), MINOR-5 (instrcov single-term):** приняты как documented warning-level / structural — не влияют на детерминированный движок, golden, checkpoint-совместимость. MINOR-3 не трогаем: плоский пробел нужен для «30 000»→«30000».

**Инварианты подтверждены:** byte-identity (H1 no-op без span; numeric/instrcov не в render; `retracted` drop-when-None, CHECKPOINT_VERSION 1.3; `MAX_CONCURRENT==5`), stdlib/offline без циклов, детерминизм, reachability (6 verb'ов), CLI-surface.

**Финал: engine 428, bench 96, golden PASSED, determinism byte-identical, 0 регрессий. Готово к релизу v1.7.0.**


---

# v1.8.0 — H8 / H9 (второй заход)

Baseline v1.8.0: engine 428 + bench 96. Итог: **engine 453 (+25), bench 96**,
golden PASSED, determinism byte-identical, 0 регрессий. Оба REQ: per-REQ ревью в
чистом контексте.

## H8 — Ship-gate агрегатор (`shipcheck`, движок)
**Куда:** `engine/shipgate.py` (новый), `engine/profiles.py` (`citation_density_min`), `engine/cli.py` (`shipcheck`). **Статус:** 🟩 принято (ревью NO-GO→GO после remediation)

**Реализация:** read-only `check()` собирает `PASS/WARN/FAIL` + breakdown из
батареи v1.7.0. Блокирующие: quote-integrity (own-finding, который бы отгрузился),
retracted-cite, citation-density < порога профиля, пустой отчёт. Warning: numeric,
instruction-coverage, retracted-в-библиографии. Пороги из `profiles` (H7).

**Remediation (ревью, закрыто системно):** MAJOR-1 completeness считал только
findings → debunk из корректировок = ложный NO-GO → ключ на `shipped` (findings OR
corrections). MAJOR-2 citation-density смотрел truthiness `c.sources` → ложный PASS
на висячем id → считать процитированным только резолвящийся источник (зеркало
`report._cites`). MINOR: quote-block scoped на would-ship own-findings; numeric/
instruction-coverage scoped на shipped; retracted-в-библиографии → WARN.

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC8.1 | Агрегирует ≥5 проверок в один вердикт+breakdown | `test_h8_shipgate.py::Ac81AggregatesTest`, `Ac81MirrorReportShipSetTest` | 🟩 |
| AC8.2 | Блокирующие (quote-block, retracted-cite) → FAIL | `...::Ac82BlockingFailTest` | 🟩 |
| AC8.3 | numeric/instruction → WARN, не FAIL | `...::Ac83WarnNotFailTest` | 🟩 |
| AC8.4 | citation-density < порога профиля (резолвящиеся источники) → FAIL | `...::Ac84CitationDensityTest`, `Ac81...::test_dangling_source_id_fails_citation_density` | 🟩 |
| AC8.5 | read-only + детерминизм; report не импортирует shipgate | `...::Ac85ReadOnlyDeterministicTest` | 🟩 |
| AC8.E2E | `engine shipcheck`: чистый → PASS | `...::Ac8E2ESubprocessTest` | 🟩 |

## H9 — Stance-target группировка (`claimsmatrix`, движок)
**Куда:** `Claim.stance_target: Optional[str]` (drop-when-None), `engine/reconcile.py` (новый), `engine/cli.py` (`claimsmatrix`). **Статус:** 🟩 принято (ревью GO + honesty-remediation)

**Реализация:** LLM ставит `stance_target`; движок детерминированно группирует и
сводит: `consensus` (все VERIFIED) / `refuted` (все FALSE) / `contradicted` (V+F) /
`inconclusive` (только мнения) / `disputed` (решающее + мнения); канонические
значения (digit-keys) + флаг `numeric_divergence`.

**Remediation (ревью, 2 honesty-MAJOR):** all-FALSE больше не «disputed», а `refuted`;
одни мнения → `inconclusive`; «consensus» вердиктов не прячет расхождение чисел
(`numeric_divergence`); `numbers` дедуплицируются по digit-key (чинит false-split);
публичный seam `numeric.number_tokens`/`digit_key` (снят coupling на приватный helper).

| AC | Критерий | Тест | Статус |
|----|----------|------|--------|
| AC9.1 | `stance_target` Optional, drop-when-None | `test_h9_reconcile.py::Ac91ByteIdentityTest` | 🟩 |
| AC9.2 | Группировка по stance_target (без ключа — вне матрицы) | `...::Ac92GroupingTest` | 🟩 |
| AC9.3 | Вердикты consensus/refuted/contradicted/inconclusive/disputed | `...::Ac93ReconciliationTest` | 🟩 |
| AC9.4 | Канонические значения + numeric_divergence | `...::Ac94QuantifiedValuesTest`, `Ac93NumericDivergenceTest` | 🟩 |
| AC9.5 | Детерминизм; read-only; report не импортирует reconcile | `...::Ac95ReadOnlyDeterministicTest` | 🟩 |

## Итог v1.8.0
Verb'ы теперь: 8 новых read-only (v1.7.0: quotecheck/numcheck/independence/retraction/
profile/instrcheck; v1.8.0: shipcheck/claimsmatrix). Reachability-guard зелёный.
Pre-release ревью (чистый контекст): **GO** — 0 critical/major/minor, 2 non-blocking observation (quote-block сигнал scoped на own-findings — intended по AC; косметическая асимметрия scope numeric/instrcov — warning-level). Mirror-fidelity, байт-идентичность (CHECKPOINT_VERSION 1.3), детерминизм, reachability, ацикличность импортов — подтверждены. 453/453. Готово к релизу v1.8.0.
