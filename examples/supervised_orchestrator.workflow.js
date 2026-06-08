/**
 * supervised_orchestrator.workflow.js — REAL supervised control-loop с RESUME (v0.3, вариант A)
 * ============================================================================================
 *
 * Идея: оркестратор — этот JS-цикл, он живёт ВНЕ контекста агентов.
 *   - Сбор (collection) — одна стадия (Research). Результат кэшируется в JS (`snap`) и пишется на диск.
 *   - Verify/Format ПОЛУЧАЮТ кэш как данные; цикл их не просит собирать и не вызывает коллектор повторно.
 *   - RESUME: на старте loader-subagent читает прошлый snapshot.json. Если он есть и тема совпала —
 *     стадия Research ПРОПУСКАЕТСЯ целиком, `loop_collection_calls_total` остаётся 0. Это и есть
 *     resume, который РЕАЛЬНО не пере-собирает — доказательство в журнале считает сам цикл (внешне),
 *     а не самоотчёт агента (в нативном resume агент писал «0», реально фетчил — здесь так нельзя).
 *
 * Run-journal на диск каждый прогон: ./research_output/<runId>/run_journal.{json,md} (+ snapshot.json).
 *   Скрипт Workflow не имеет ФС — файлы пишет subagent; журнал ещё и возвращается как return value.
 *
 * Запуск:
 *   1-й раз (сбор):   Workflow({ scriptPath, args: { topic, runId: 'my_run', depth: 'Quick' } })
 *   resume (без сбора): тот же runId и та же topic → Research пропускается, collection=0.
 *
 * Hard-enforcement (опц.): чтобы Verify/Format ФИЗИЧЕСКИ не могли фетчить — дай им opts.agentType
 *   без web-инструментов. Сейчас enforced loop-level (цикл не вызывает коллектор) + инструкция.
 */

export const meta = {
  name: 'deep-research-supervised',
  description: 'Supervised control-loop с resume: собрать один раз и закэшировать; при resume сбор пропускается (collection=0); пишет run-journal для ретро.',
  phases: [
    { title: 'Resume' },
    { title: 'Research' },
    { title: 'Verify' },
    { title: 'Format' },
    { title: 'Journal' },
  ],
}

// ----------------------------- входные параметры (args может прийти строкой — разбираем оба) -----------------------------
const A = (typeof args === 'string') ? (() => { try { return JSON.parse(args) } catch (e) { return {} } })() : (args || {})
const TOPIC = A.topic || 'Актуальная цена API Claude Opus 4.x за 1M токенов (input/output), офиц. Anthropic'
const RUN_ID = A.runId || 'supervised_demo'
const DEPTH = A.depth || 'Quick'
const MAX_RESEARCH_TRIES = A.maxResearchTries || 3
const OUT_DIR = `./research_output/${RUN_ID}`

// ----------------------------- схемы -----------------------------
const RESUME_LOAD = { type: 'object', required: ['found'], properties: {
  found: { type: 'boolean' },
  topic: { type: 'string' },
  snapshot: { type: 'object' },
} }
const SNAPSHOT = { type: 'object', required: ['status', 'blockedBy', 'sources', 'budget'], properties: {
  status: { enum: ['done', 'partial', 'blocked'] },
  blockedBy: { enum: ['budget', 'timeout', 'paywall', 'low_quality', 'none'] },
  sources: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, url: { type: 'string' }, tier: { type: 'string' }, extract: { type: 'object' } } } },
  claims: { type: 'array', items: { type: 'object' } },
  budget: { type: 'object', properties: { spent_usd: { type: 'number' }, loads_used: { type: 'number' } } },
} }
const VERDICT = { type: 'object', required: ['confirmed', 'rejected'], properties: {
  confirmed: { type: 'array', items: { type: 'object' } }, rejected: { type: 'array', items: { type: 'object' } } } }
const REPORT = { type: 'object', required: ['fact_sheet'], properties: {
  fact_sheet: { type: 'string' }, aggregate_confidence: { type: 'string' } } }

// ------------- run-journal: строит ЦИКЛ => метрики внешне наблюдаемые -------------
const journal = []
let loopCollectionCalls = 0 // сколько раз ЦИКЛ вызвал коллектор. Resume/Verify/Format его не увеличивают.
function note(stage, data) { journal.push({ step: journal.length + 1, stage, ...data }); log(`[${stage}] ${JSON.stringify(data)}`) }

function correct(prev) {
  if (!prev) return ''
  switch (prev.blockedBy) {
    case 'budget':      return 'Бюджет на исходе: только Tier-1, финализируй по собранному.'
    case 'timeout':     return 'Источник завис: пропусти, failover на следующий tier.'
    case 'paywall':     return 'Paywall: НЕ эскалируй человеку, возьми открытые альтернативы.'
    case 'low_quality': return 'Качество < порога: переразбей слабую subtask на узкие запросы.'
    default:            return ''
  }
}

// ==================== RESUME — loader читает прошлый snapshot.json (это не сбор) ====================
phase('Resume')
let resumed = false
let snap = null
const loaded = await agent(
  `Ты Resume-loader. Прочитай файл ${OUT_DIR}/snapshot.json, ЕСЛИ он существует. НЕ фетчи из web, НЕ выдумывай.
Верни {found:true, topic, snapshot} с его содержимым; если файла нет или он нечитаем — {found:false}.`,
  { schema: RESUME_LOAD, label: 'resume-check', phase: 'Resume' },
)
if (loaded && loaded.found && loaded.topic === TOPIC && loaded.snapshot) {
  resumed = true
  snap = loaded.snapshot
  note('resume', { resumed: true, sources_loaded: (snap.sources || []).length, loop_invoked_collection: false, decision: 'fingerprint MATCH → Research SKIPPED' })
} else {
  const reason = (loaded && loaded.found) ? 'fingerprint MISMATCH (другая тема)' : 'snapshot отсутствует'
  note('resume', { resumed: false, reason, decision: 'fresh run → Research' })
}

// ==================== RESEARCH — выполняется ТОЛЬКО если НЕ resumed ====================
phase('Research')
if (!resumed) {
  for (let i = 1; i <= MAX_RESEARCH_TRIES; i++) {
    const fix = correct(snap)
    const directive = `Ты Research-агент. Декомпозируй и собери данные, ТОЛЬКО Tier-1 (native web). Depth ${DEPTH}. ${fix}
Верни SNAPSHOT: sources[] (id,url,tier,extract с реальными значениями), budget{spent_usd,loads_used}, status, blockedBy.
Тема: ${TOPIC}`
    loopCollectionCalls++ // ЦИКЛ вызывает коллектор — считаем внешне, ДО вызова
    let res
    try { res = await agent(directive, { schema: SNAPSHOT, label: `research:try-${i}`, phase: 'Research' }) }
    catch (e) { res = { status: 'blocked', blockedBy: 'budget', sources: (snap && snap.sources) || [], claims: [], budget: { spent_usd: 0, loads_used: 0 } } }
    snap = res
    note('research', { attempt: i, status: snap.status, blockedBy: snap.blockedBy, sources: (snap.sources || []).length, loop_invoked_collection: true })
    if (snap.status === 'done') break
    if (snap.status === 'partial' && i >= 2) break
  }
} else {
  note('research', { skipped: true, reason: 'resumed — снапшот загружен, сбор не нужен', loop_invoked_collection: false })
}

// ==================== VERIFY — получает кэш snap; цикл НЕ вызывает коллектор ====================
phase('Verify')
const verdict = await agent(
  `Ты FactCheck-агент. Тебе ПЕРЕДАНЫ уже собранные источники (ниже). НЕ делай новых web-вызовов —
работай только по этим extract'ам; если данных не хватает — в rejected, НЕ фетчи. Верни confirmed[] и rejected[] с confidence.
SNAPSHOT.sources: ${JSON.stringify((snap && snap.sources) || [])}`,
  { schema: VERDICT, label: 'verify', phase: 'Verify' },
)
note('verify', { confirmed: (verdict.confirmed || []).length, rejected: (verdict.rejected || []).length, loop_invoked_collection: false, sources_reused: ((snap && snap.sources) || []).length })

// ==================== FORMAT ====================
phase('Format')
const report = await agent(
  `Ты Format-агент. Собери Fact Sheet ≤200 слов по подтверждённым фактам. НЕ фетчи.
confirmed: ${JSON.stringify(verdict.confirmed || [])}`,
  { schema: REPORT, label: 'format', phase: 'Format' },
)
note('format', { loop_invoked_collection: false })

// ==================== JOURNAL — пишет run_journal.{json,md} + snapshot.json (для будущего resume) ====================
phase('Journal')
const summary = {
  run_id: RUN_ID, topic: TOPIC, depth: DEPTH,
  resumed,
  research_tries: journal.filter((e) => e.stage === 'research' && e.attempt).length,
  loop_collection_calls_total: loopCollectionCalls, // 0 при resume — внешнее доказательство no-refetch
  collection_calls_in_verify_or_format: 0,
  sources: ((snap && snap.sources) || []).length,
  claims_confirmed: (verdict.confirmed || []).length,
  claims_rejected: (verdict.rejected || []).length,
  final_status: (snap && snap.status) || 'unknown',
  no_refetch_guarantee: 'enforced by control flow — при resume Research пропущен; Verify/Format получают кэш; цикл не вызывает коллектор',
}
const snapshotForResume = { topic: TOPIC, snapshot: snap }
await agent(
  `Ты Journal-writer. Запиши РОВНО три файла, ничего не добавляя сверх данных:
1) ${OUT_DIR}/run_journal.json — ровно: ${JSON.stringify({ summary, journal })}
2) ${OUT_DIR}/snapshot.json — ровно: ${JSON.stringify(snapshotForResume)}  (это чекпоинт для будущего resume — не меняй)
3) ${OUT_DIR}/run_journal.md — человекочитаемый ретро-лог: таблица summary (выдели resumed и loop_collection_calls_total),
   пошаговая таблица journal (step|stage|данные), и блок «Для ретро» (сбор был? пере-фетч? ретраи? что отклонено? это resume?).
Создай папку ${OUT_DIR} при необходимости. Верни пути.`,
  { label: 'journal-writer', phase: 'Journal' },
)
note('journal', { written: `${OUT_DIR}/run_journal.{json,md} + snapshot.json` })

return { summary, report, journal }
