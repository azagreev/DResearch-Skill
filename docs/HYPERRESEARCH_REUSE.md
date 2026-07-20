# Hyperresearch — анализ переиспользования (H1–H7)

Изучение проекта [jordan-gibbs/hyperresearch](https://github.com/jordan-gibbs/hyperresearch)
с целью перенести лучшее в Deep Research Skill (DRS). Метод: три параллельных
агента — (1) Python-ядро hyperresearch, (2) методология skills/критиков/линтов,
(3) инвентаризация текущих возможностей и пробелов DRS. Сквозная трассировка
REQ→критерий→тест: [TRACE_HYPERRESEARCH.md](TRACE_HYPERRESEARCH.md).

## Главный вывод

DRS **архитектурно впереди** hyperresearch по большей части инфраструктуры:
checkpoint/resume (`engine/state.py`), cross-run vault на SQLite+FTS5
(`engine/memory.py`), determinism-gate + golden corpus + byte-identical replay,
5-компонентный auditable composite score (`engine/score.py`), trust-fence против
инъекций (`engine/ingest.py`). Поэтому переиспользуем не «фичи вообще», а узкий
набор механик, закрывающих **реальные** пробелы DRS и укладывающихся в наш
инвариант: **stdlib-only, детерминизм, offline**.

> **Статус:** H1–H7 отгружены в **v1.7.0** (см. CHANGELOG и [TRACE_HYPERRESEARCH.md](TRACE_HYPERRESEARCH.md)).
> Ниже — исходный анализ; в конце документа — **Backlog** невзятых кандидатов на v1.8.0+.

## Матрица переиспользования

### Портируем — движок (реальный пробел + stdlib + детерминизм)

| ID | Механика hyperresearch | Пробел DRS | Ценность |
|----|------------------------|-----------|----------|
| **H1** | Механический quote-integrity (`citecheck.py`, mech. tier) | Цитата 【S†L{a}-L{b}】 не проверяется на фактическое наличие текста в строках источника | HIGH |
| **H2** | Вычисляемая independence: union-find по canonical-URL / wire-signature / Jaccard≥0.7 (`independence.py`+`similarity.py`), score 1/cluster_size | `ScoreComponents.independence` (вес 0.20) — незаполняемый вход; синдикация/циркулярное репортинг не детектится | HIGH |
| **H3** | Retraction floor (offline-половина `scholar.py`/`quality.py`) | Отзыв публикаций не обрабатывается вообще (только проза в references) | MED |
| **H6** | Numeric-consistency (`citecheck.py`) | FCA «Quantitative Validation» — только проза в SKILL.md | MED |
| **H7** | Scale-as-config-profile (`config.py`+`profiles.py`, dataclass-loader, `extends`) | Пороги/лимиты/word-targets живут в прозе SKILL.md, не в машиночитаемом профиле | LOW-MED |

### Портируем — методология (skill/subagent-слой)

| ID | Паттерн hyperresearch | Пробел DRS | Ценность |
|----|-----------------------|-----------|----------|
| **H4** | Patch-never-regenerate: tool-lock `[Read,Edit]`, per-hunk caps, escalate-what-won't-fit, `patch-surgery` gate | `verify.py` только читает; нет patch-цикла и tool-lock-дисциплины | MED-HIGH |
| **H5** | Instruction- + dialectic-критики (2 из 4 адверсариальных, findings-only) | FactCheck проверяет факты, но не «ответили ли на вопрос / разобрали контраргумент» | MED |

### НЕ портируем

- **Network / heavy-deps:** scholar/enrich (OpenAlex/S2 + httpx), embeddings, crawl4ai/browser-lane, escalation-queue — конфликт с offline/stdlib. (Идея offline-retraction-JSON и percentile/floor-логика — учтена в H3.)
- **sqlite-migrations, pydantic, jinja2** — код не портируется. Идеи «CHECK-vocab → enum-валидатор на записи» и «markdown-is-truth / rebuildable index» у нас уже реализованы.
- **Дублирующее, где DRS уже лучше:** checkpoint/resume, cross-run vault, determinism-gate, composite scoring, PageRank (у нас RRF+tier fusion в `rank.py`).

## REQ-спецификации

### H1 — Механический quote-integrity gate
**Куда:** новый модуль верификации цитат + вызов на границе рендера/факт-чека;
переиспользует `ingest.content_lines` и `Claim.citation_spans`.
**Суть:** для каждой цитаты со span'ом дословный текст обязан присутствовать в
`content_lines[a..b]` источника (нормализация пробелов). Иначе `QUOTE_MISMATCH`.
**AC:** (1.1) верно-процитированный span проходит; (1.2) фейковая цитата →
QUOTE_MISMATCH; (1.3) в FINDINGS это hard-block (claim исключён/отчёт помечен),
детерминированно, без LLM; (1.4) legacy без цитат/span — байт-в-байт неизменно;
(1.5) stdlib+детерминизм; (1.E2E) сквозной: отчёт с фейковой цитатой падает гейт.

### H2 — Вычисляемая source independence
**Куда:** новый чистый модуль independence + интеграция в `score.py` (заполнение
компонента) и `factcheck.resolve_conflict`.
**Суть:** union-find кластеризует источники по детерминированным сигналам
(canonical-URL, wire/dateline-signature, shingle Jaccard≥порог); каждый источник
получает вес `1/cluster_size`. Значение заполняет `ScoreComponents.independence`.
**AC:** (2.1) чистая функция кластеризации детерминирована и order-independent;
(2.2) N перефразированных перепечаток одной новости → ~1 голос; (2.3)
corroboration-ladder считает сумму independence, а не число инстансов; (2.4)
порог конфигурируем, safe default не занижает independence без явного сигнала;
(2.5) устранено расхождение проза/код (SKILL.md:104 ↔ `resolve_conflict`);
(2.6) байт-идентичность там, где сигнала синдикации нет.

### H3 — Retraction flag-and-veto (offline)
**Куда:** `model.Source` (флаг), `factcheck.py` (veto), детектор языка отзыва.
**Суть:** `Source.retracted` → hard-veto цитирующего claim (→ FALSE/exclude),
если отзыв не подтверждён явно; детерминированный детектор retraction-языка в
extract'ах помечает источник. Offline; live-lookup НЕ делаем.
**AC:** (3.1) retracted-источник → veto; (3.2) детектор языка отзыва помечает;
(3.3) явный acknowledgment снимает hard-block; (3.4) offline+детерминизм;
(3.5) байт-в-байт при отсутствии отзыва.

### H6 — Numeric-consistency
**Куда:** модуль верификации (рядом с H1).
**Суть:** числовые утверждения claim трассируемы к числам в цитируемом источнике;
нетрассируемые числа флагаются (warning-класс).
**AC:** (6.1) число из claim, присутствующее в источнике, проходит; (6.2)
число без опоры → флаг; (6.3) детерминизм; (6.4) байт-в-байт без числовых claim.

### H7 — Scale-as-config-profile
**Куда:** новый stdlib-модуль профилей (dataclass + JSON/загрузчик), потребляется
движком; выносит пороги гейтов и лимиты из прозы SKILL.md.
**Суть:** именованные профили (по глубине) со scale-кнобами и порогами гейтов;
`extends`-оверлей; golden-pinned. Пороги, введённые H1/H2, живут здесь.
**AC:** (7.1) профиль грузится и валидируется, unknown-ключи игнорируются;
(7.2) `extends` наследование; (7.3) движок читает пороги из профиля, а не из
литералов; (7.4) golden-pinned дефолты; (7.5) детерминизм.

### H4 — Patch-never-regenerate (skill-слой)
**Куда:** SKILL.md + subagent-контракты + структурный lint.
**Суть:** patch/polish-субагенты tool-locked к `[Read,Edit]` (физически не могут
Write/перегенерировать); per-hunk caps; findings, не влезающие в hunk,
эскалируются оркестратору; `patch-surgery`-гейт запрещает ship, если veto-level
finding не применён.
**AC:** (4.1) контракт субагента ограничен `[Read,Edit]`; (4.2) hunk-cap
задокументирован и проверяем; (4.3) неприменённый critical finding блокирует
ship (структурная проверка); (4.4) docs↔reachability guard зелёный.

### H5 — Instruction + dialectic критики (skill-слой)
**Куда:** два новых findings-only субагента + их промпты + вызов в workflow.
**Суть:** instruction-критик диффит H2/сущности черновика против декомпозиции
(+ проверка «vague-recommendation» — требует конкретных чисел/порогов, где
evidence позволяет); dialectic-критик ищет неразобранные контраргументы,
которые уже есть в корпусе. Оба без Edit (findings-only).
**AC:** (5.1) критики не имеют Edit; (5.2) instruction-критик ловит пропуск
атомарного пункта декомпозиции; (5.3) dialectic-критик ловит неразобранный
контраргумент из корпуса; (5.4) findings капятся, чтобы не хоронить critical.

## Риски

- **H2 (independence офлайн приблизительна):** настоящая независимость требует
  link-graph. Митигация — консервативная детерминированная эвристика +
  конфигурируемый порог + safe default (не занижать independence без явного
  сигнала синдикации). Ложное занижение хуже пропуска → порог консервативный.
- **H7 (churn):** вынос порогов из прозы затрагивает много точек. Митигация —
  golden-pinned дефолты, байт-идентичность вывода при дефолтном профиле.
- **H4/H5 (skill-слой):** проверяется структурно (lint/reachability), не
  юнит-тестами движка; LLM-часть строго вне детерминированного ядра.

## Что НЕ трогаем (DRS уже сильнее)

checkpoint/resume, cross-run SQLite memory, determinism-gate + golden corpus +
byte-identical replay, typed collection seam + trust-fence, 5-компонентный
auditable composite score, RRF+tier fusion, prose-only fallback mode.


---

## Backlog / deferred (кандидаты на v1.8.0+)

Невзятое в v1.7.0 из тех же трёх агентских разборов, отранжированное по
ценности × fit к инварианту (stdlib-only / детерминизм / offline).

### Сильные (рекомендованы на v1.8.0)

| ID | Что | Откуда | Пробел DRS | Ценность / риск |
|----|-----|--------|-----------|-----------------|
| **H8** | Ship-gate агрегатор (`shipcheck`): один GO/NO-GO из quote-integrity (H1) + numeric (H6) + instruction-coverage (H5) + retraction (H3) + citation-density + heading/length; пороги из профиля (H7) | `runs.verify_run` | 6 аудит-verb'ов разрознены; нет единого «можно ли отгружать» | HIGH / низкий (композиция готового, read-only, детерминизм) |
| **H9** | Stance-target группировка claim'ов: мета-вид «эти утверждения о ОДНОМ объекте», split по позиции + количественные значения (консенсус vs противоречие) | `claims.group_by_target` / `literature_matrix` | `cluster.py` группирует по тексту, нет реконсиляции противоречий для синтеза | MED-HIGH / средний |

### Второй эшелон

| ID | Что | Заметка |
|----|-----|---------|
| **H10** | Renormalize-on-missing в composite (не штрафовать за отсутствующий компонент, ренормировать веса) | `quality.py`; **меняет scoring-семантику** → сдвиг golden-tier'ов, нужен opt-in / re-pin |
| **H11** | Width/cluster-coverage критик: флагать evidence-кластеры с findings, отсутствующие в отчёте | третий адверсариальный критик, механический; есть `EvidenceCluster` |
| **H12** | Verbatim-prompt anchoring + scaffold-lint (точный промпт как «евангелие», перечитывается каждой фазой) | анти-context-rot; skill-слой + guard |
| **H13** | Offline citation-authority: percentile авторитетности из статического citations-JSON от скилла (+ retraction из того же фида) | расширяет H3; stdlib+offline через данные caller'а |

### Крупные рефакторы / diminishing returns

- **H14 — Phase-loads-on-demand:** разбить 7 фаз SKILL.md на отдельные skill-файлы,
  грузящиеся при исполнении фазы (урок V7→V8 hyperresearch). Крупный рефактор.
- **Triple-draft→synthesize**, **depth/corpus-critic** — оркестрационная методология,
  преимущественно семантическая (LLM); слабо ложится на детерминированный движок.

### Спецификации рекомендованных

**H8 — Ship-gate агрегатор.** Куда: новый `engine/shipgate.py` + verb `shipcheck`
(read-only; отчёт не трогается → байт-идентичность тривиальна). Суть: чистая
функция собирает вердикт `PASS/WARN/FAIL` + breakdown из детерминированных
проверок. Блокирующие (FAIL): заблокированная H1-цитата у own-finding;
citation-density findings ниже порога профиля; отгружаемый claim цитирует
retracted-источник без acknowledgment. Warning: нетрассируемые числа (H6),
непокрытые критерии (H5). Пороги — из `profiles` (H7), что даёт профилю реального
потребителя. AC: (8.1) агрегирует ≥5 проверок в один вердикт; (8.2) H1-блок или
retracted-cite → FAIL; (8.3) numeric/instruction → WARN, не FAIL; (8.4)
citation-density < порога профиля → FAIL; (8.5) read-only + детерминизм, отчёт
неизменен; (8.E2E) `engine shipcheck`: чистый snapshot → PASS, «грязный» → FAIL с
причинами.

**H9 — Stance-target группировка.** Куда: `Claim.stance_target: Optional[str]`
(drop-when-None → байт-идентичность, как citation_spans/retracted), новый
`engine/reconcile.py` + verb `claimsmatrix` (read-only). Суть: LLM проставляет
`stance_target` (ключ группировки), движок детерминированно группирует и
реконсилирует: `contradicted`, если в группе противоположные вердикты
(VERIFIED↔FALSE) или взаимные `contradicting_sources`; иначе `consensus`; плюс
surфейс количественных значений (переиспользуя `numeric._number_tokens`). AC:
(9.1) поле Optional, drop-when-None; (9.2) группировка по stance_target; (9.3)
реконсиляция consensus/contradiction; (9.4) количественные значения по target;
(9.5) детерминизм, read-only, отчёт неизменен.
