# Чек-лист ретроспективы прогона (supervised orchestrator)

Ретро по одному прогону `examples/supervised_orchestrator.workflow.js`. Цель — за 5 минут понять: сбор отработал честно, ресурсы потрачены не зря, качество фактов адекватное.

## Как пользоваться

1. Открой `research_output/<runId>/run_journal.md` (человекочитаемо) и `run_journal.json` (точные числа). В JSON есть `summary` (агрегаты прогона) и `journal[]` (пошаговый лог; у каждого шага `stage` ∈ resume|research|verify|format|journal и флаг `loop_invoked_collection`).
2. Пройди разделы 1→6 по порядку. У каждого пункта в скобках указано, **какое поле журнала смотреть**.
3. Отмечай `- [x]` если пункт ОК. Любой неотмеченный пункт → кандидат в Action items (раздел 6).
4. В конце сверься с таблицей «красные флаги».

Опорные значения: resume-прогон → `resumed=true`, research пропущен, `loop_collection_calls_total=0`. Fresh-прогон → `resumed=false`, `loop_collection_calls_total=1` (один цикл сбора; при ретраях больше).

---

## 1. No-refetch integrity (сбор вызван ожидаемо?)

Проверяем, что цикл собирал ровно там, где должен, и нигде больше.

- [ ] Если `resumed=true` → `loop_collection_calls_total == 0`; если `resumed=false` → `>= 1` (`summary.resumed`, `summary.loop_collection_calls_total`).
- [ ] Пере-фетча в verify/format нет: `collection_calls_in_verify_or_format == 0` (`summary.collection_calls_in_verify_or_format`).
- [ ] Стадии verify и format не вызывали коллектор: на их шагах `loop_invoked_collection == false` (`journal[].stage` = verify/format → `loop_invoked_collection`).
- [ ] При resume стадия research помечена пропущенной, а не выполнена (`journal[]` stage=research → `skipped:true`; на стадии resume `decision` = «fingerprint MATCH → Research SKIPPED»).
- [ ] Счётчик сходится: число шагов с `loop_invoked_collection==true` в `journal[]` == `loop_collection_calls_total` в `summary` (внешняя метрика бьётся с пошаговой).
- [ ] Resume сработал по той же теме, а не вслепую: при `resumed=false` причина осмысленна (`journal[]` stage=resume → `reason`: «snapshot отсутствует» либо «fingerprint MISMATCH»).

## 2. Efficiency / стоило ли (multi-agent vs нативный single-context)

Multi-agent прогон ~150k токенов. Решаем, окупился ли он.

- [ ] Понятно, fresh это или resume: на resume сбор уже оплачен ранее → текущий прогон почти бесплатен по сбору (`summary.resumed`, `loop_collection_calls_total`).
- [ ] Оценена дороговизна сбора: смотри `budget.spent_usd` / `loads_used` в snapshot (`journal[]` stage=research данные / `snapshot.json` → `budget`). Дорогой сбор → resume реально экономит; дешёвый → выигрыш от кэша мал.
- [ ] Объём собранного оправдывает overhead: `sources` не единичный и реально переиспользован дальше (`summary.sources`, `journal[]` verify → `sources_reused`).
- [ ] Вывод зафиксирован: multi-agent оправдан, когда сбор дорогой/повторяемый ИЛИ нужен изолированный фактчек; для разового дешёвого запроса нативный single-context был бы дешевле (свой вывод записать в Action items).

## 3. Quality (качество фактчека)

- [ ] Баланс подтверждённых/отклонённых осмыслен, не «всё подряд confirmed» (`summary.claims_confirmed`, `summary.claims_rejected`).
- [ ] Для каждого отклонённого ясна ПРИЧИНА: single-source / противоречие источников / устарело (`journal[]` verify, поля rejected в `verdict` внутри `run_journal.json`).
- [ ] Фактчекер не штамповал: при единственном источнике на claim он не помечен confirmed без оговорок; нехватка данных ушла в rejected, а не «дофантазирована» (`rejected[].confidence`, причина).
- [ ] confirmed опираются на extract'ы из snapshot, а не на общие знания агента (сверь `sources[].extract` со списком confirmed).
- [ ] Итоговый отчёт покрывает только confirmed (Format кормили `verdict.confirmed`; rejected в Fact Sheet не протёк).

## 4. Failures & corrections (сбои и самокоррекция)

- [ ] Были ли ретраи: `research_tries` (`summary.research_tries`). Если `>1` — понять, почему первая попытка не дала `done`.
- [ ] Финальный статус приемлем: `final_status` = done; partial/blocked требует объяснения (`summary.final_status`).
- [ ] Если статус не done — зафиксирован `blockedBy`: budget/timeout/paywall/low_quality/none (`journal[]` research → `blockedBy`, `snapshot.json` → `blockedBy`).
- [ ] Сработала ли коррекция: на ретрае директива содержала фикс из `correct()` под конкретный `blockedBy` (budget→только Tier-1; timeout→failover; paywall→открытые альтернативы; low_quality→переразбивка). Проверить, что фикс соответствовал причине.
- [ ] Эскалаций к человеку по paywall не было (по политике `correct()` paywall НЕ эскалируется); любая фактическая эскалация — разобрать.
- [ ] Цикл не исчерпал `MAX_RESEARCH_TRIES` вхолостую (`research_tries` < лимита, либо ранний выход по partial на 2-й попытке оправдан).

## 5. Staleness (актуальность при resume)

Заполнять ТОЛЬКО если `resumed=true`.

- [ ] Оценён возраст снапшота: когда был создан исходный `snapshot.json` / прогон, давший кэш (mtime файла или `run_id` исходного прогона).
- [ ] Тема время-чувствительная? (цены, курсы, релизы, «актуальная …» в `summary.topic`). Если да — устаревший кэш = риск.
- [ ] Для время-чувствительных данных решено: переверить свежим прогоном (другой `runId` или удалить snapshot) ИЛИ осознанно принять на веру с пометкой возраста. Не принимать молча.
- [ ] Если данные стабильные (определения, методология) — resume на старом кэше оправдан, переверка не нужна.

## 6. Action items (шаблон, максимум 3)

Перенеси сюда неотмеченные пункты выше. Коротко: проблема → действие.

- [ ] **A1.** _<симптом из журнала>_ → _<что сделать в следующем прогоне>_
- [ ] **A2.** _<…>_ → _<…>_
- [ ] **A3.** _<…>_ → _<…>_

---

## Красные флаги (симптом в журнале → что значит)

| Симптом в журнале | Что значит |
|---|---|
| `resumed=true`, но `loop_collection_calls_total > 0` | resume не сработал — цикл всё равно собирал; проверь логику fingerprint/skip |
| `collection_calls_in_verify_or_format > 0` | пере-фетч в verify/format — нарушена изоляция кэша |
| шаг verify/format с `loop_invoked_collection=true` | стадия, которая должна только читать кэш, полезла собирать |
| число шагов с `loop_invoked_collection=true` ≠ `loop_collection_calls_total` | внешняя метрика и пошаговый лог разошлись — журналу нельзя доверять |
| `claims_rejected=0` при `sources<=1` | фактчекер штампует confirmed без перекрёстной проверки |
| `claims_confirmed=0` | сбор/верификация провалились — отчёт пустой по сути |
| `research_tries` упёрся в `MAX_RESEARCH_TRIES`, `final_status≠done` | сбор не сошёлся; коррекция не помогла |
| `final_status` = blocked + `blockedBy=budget/timeout` | прогон оборвался по лимиту, данные неполные |
| `blockedBy=paywall` + признаки эскалации к человеку | нарушена политика correct() (paywall → открытые альтернативы, не человек) |
| `resumed=true` + время-чувствительная `topic` + нет переверки | риск отдать устаревшие данные как актуальные |
| `sources_reused=0` при `resumed=true` | загрузили снапшот, но verify его не использовал — кэш бесполезен |
