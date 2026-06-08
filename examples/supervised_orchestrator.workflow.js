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
 * Hard no-fetch (v0.4): hook для tool-restricted agentType 'no-fetch-analyst' (tools: Read/Grep/Glob,
 *   без web). ВАЖНО — проверено smoke-тестом: текущий Workflow-runtime резолвит ТОЛЬКО built-in типы
 *   (claude, Explore, general-purpose, Plan, …), а они все с web; кастомный .claude/agents/*.md он НЕ
 *   подхватывает. Поэтому по умолчанию hardNoFetch=OFF (soft); helper делает graceful fallback на soft
 *   и честно пишет режим в журнал (hard_nofetch). Файл no-fetch-analyst.md оставлен forward-hook'ом для
 *   рантаймов, где кастомные restricted-типы резолвятся. Реальная гарантия здесь — loop-level (цикл не
 *   вызывает коллектор) + инструкция.
 * Staleness (v0.4): на resume устаревшие time-sensitive источники (окно по depth: Quick 24ч / Standard
 *   7д / Deep 14д) пере-верифицируются — ограниченный re-collect, инкрементит loop_collection_calls_total
 *   (не тихо). «сейчас» прокидывается через args.now (ISO), т.к. скрипт не читает системные часы.
 *   Следствие: loop_collection_calls_total на resume больше НЕ всегда 0 (станет 1 при staleness-reverify).
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

// v0.4 hard no-fetch: Verify/Format через tool-restricted subagent (Read/Grep/Glob, без web).
const ANALYST_TYPE = A.analystAgentType || 'no-fetch-analyst'
const HARD_NOFETCH = A.hardNoFetch === true // OPT-IN: Workflow-runtime НЕ резолвит кастомные agentType (smoke-тест) → дефолт soft

// v0.4 staleness: «сейчас» прокидывается через args.now (ISO) — скрипт не читает системные часы.
const NOW_ISO = A.now || null
const FRESHNESS_HOURS = { Quick: 24, Standard: 168, Deep: 336, Exhaustive: 336 } // 24ч / 7д / 14д
const STALE_WINDOW_H = FRESHNESS_HOURS[DEPTH] || FRESHNESS_HOURS.Standard
function ageHours(createdIso, nowIso) {
  if (!createdIso || !nowIso) return null
  const c = Date.parse(createdIso), n = Date.parse(nowIso)
  if (Number.isNaN(c) || Number.isNaN(n)) return null
  return (n - c) / 3600000
}
function isStale(src, nowIso, windowH) {
  if (!src || src.time_sensitive !== true) return false
  const a = ageHours(src.created_utc, nowIso)
  return a !== null && a > windowH
}

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
    id: { type: 'string' }, url: { type: 'string' }, tier: { type: 'string' }, extract: { type: 'object' },
    created_utc: { type: 'string' }, time_sensitive: { type: 'boolean' } } } },
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

// Verify/Format через tool-restricted agentType, ЕСЛИ runtime его резолвит. Если нет (текущий
// Workflow-runtime: доступны только built-in типы, все с web) — graceful fallback на soft, режим
// честно фиксируется. Никогда не роняет прогон из-за отсутствующего типа.
async function analystAgent(prompt, baseOpts) {
  if (!HARD_NOFETCH) return { result: await agent(prompt, baseOpts), mode: 'soft(instruction-only)' }
  try {
    return { result: await agent(prompt, { ...baseOpts, agentType: ANALYST_TYPE }), mode: `hard(${ANALYST_TYPE})` }
  } catch (e) {
    const msg = String((e && e.message) || e)
    if (/agent type/i.test(msg) && /not found/i.test(msg)) {
      return { result: await agent(prompt, baseOpts), mode: `soft(agentType '${ANALYST_TYPE}' недоступен в runtime)` }
    }
    throw e
  }
}

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
На КАЖДОМ источнике проставь created_utc='${NOW_ISO || '<unknown>'}' (ISO) и time_sensitive:true для цен/«latest»/котировок, иначе false.
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

// ==================== STALENESS RE-VERIFY (только при resume) ====================
// time-sensitive источники старше окна пере-верифицируются; такой re-fetch ОБЯЗАН инкрементить счётчик
// (не тихо). На fresh-пути источники только что собраны — они свежие по построению.
if (resumed) {
  const allSources = (snap && snap.sources) || []
  if (!NOW_ISO) {
    note('staleness', { checked: false, reason: 'args.now не передан → возраст не вычислить', window_hours: STALE_WINDOW_H, loop_invoked_collection: false })
  } else {
    const stale = allSources.filter((s) => isStale(s, NOW_ISO, STALE_WINDOW_H))
    if (stale.length === 0) {
      note('staleness', { checked: true, window_hours: STALE_WINDOW_H, stale_sources: 0, decision: 'time-sensitive источники свежи → re-verify не нужен', loop_invoked_collection: false })
    } else {
      const staleIds = stale.map((s) => s.id)
      note('staleness', { checked: true, window_hours: STALE_WINDOW_H, stale_sources: stale.length, stale_ids: staleIds, decision: 'устаревшие → ОГРАНИЧЕННЫЙ re-verify', loop_invoked_collection: true })
      loopCollectionCalls++ // re-verify ЭТО сбор — считаем ДО вызова, не тихо
      let refreshed
      try {
        refreshed = await agent(
          `Ты Research-агент (STALENESS RE-VERIFY). Эти time-sensitive источники устарели (>${STALE_WINDOW_H}ч, сейчас=${NOW_ISO}).
ПЕРЕ-собери ТОЛЬКО их, Tier-1. По каждому верни обновлённый extract, created_utc='${NOW_ISO}', time_sensitive:true.
Устаревшие (только эти ${staleIds.length}): ${JSON.stringify(stale)}`,
          { schema: SNAPSHOT, label: 'staleness-reverify', phase: 'Research' },
        )
      } catch (e) { refreshed = null }
      if (refreshed && Array.isArray(refreshed.sources) && refreshed.sources.length) {
        const byId = new Map(refreshed.sources.map((s) => [s.id, s]))
        snap = { ...snap, sources: allSources.map((s) => (byId.has(s.id) ? { ...s, ...byId.get(s.id), restaled: true } : s)) }
        note('staleness', { merged: true, refreshed_ids: [...byId.keys()], loop_invoked_collection: true })
      } else {
        snap = { ...snap, sources: allSources.map((s) => (staleIds.includes(s.id) ? { ...s, stale_unrefreshed: true } : s)) }
        note('staleness', { merged: false, reason: 're-verify пусто → stale-значения помечены для дисклеймера', stale_ids: staleIds, loop_invoked_collection: true })
      }
    }
  }
}

// ==================== VERIFY — получает кэш snap; цикл НЕ вызывает коллектор ====================
phase('Verify')
const verifyRun = await analystAgent(
  `Ты FactCheck-агент. Тебе ПЕРЕДАНЫ уже собранные источники (ниже). НЕ делай новых web-вызовов —
работай только по этим extract'ам; если данных не хватает — в rejected, НЕ фетчи. Верни confirmed[] и rejected[] с confidence.
SNAPSHOT.sources: ${JSON.stringify((snap && snap.sources) || [])}`,
  { schema: VERDICT, label: 'verify', phase: 'Verify' },
)
const verdict = verifyRun.result
note('verify', { confirmed: (verdict.confirmed || []).length, rejected: (verdict.rejected || []).length, loop_invoked_collection: false, sources_reused: ((snap && snap.sources) || []).length, hard_nofetch: verifyRun.mode })

// ==================== FORMAT ====================
phase('Format')
const formatRun = await analystAgent(
  `Ты Format-агент. Собери Fact Sheet ≤200 слов по подтверждённым фактам. НЕ фетчи.
confirmed: ${JSON.stringify(verdict.confirmed || [])}`,
  { schema: REPORT, label: 'format', phase: 'Format' },
)
const report = formatRun.result
note('format', { loop_invoked_collection: false, hard_nofetch: formatRun.mode })

// ==================== JOURNAL — пишет run_journal.{json,md} + snapshot.json (для будущего resume) ====================
phase('Journal')
const summary = {
  run_id: RUN_ID, topic: TOPIC, depth: DEPTH,
  resumed,
  research_tries: journal.filter((e) => e.stage === 'research' && e.attempt).length,
  loop_collection_calls_total: loopCollectionCalls, // 0 при resume — внешнее доказательство no-refetch
  collection_calls_in_verify_or_format: 0,
  freshness_window_hours: STALE_WINDOW_H,
  now_provided: !!NOW_ISO,
  staleness_reverify_done: journal.some((e) => e.stage === 'staleness' && e.loop_invoked_collection === true),
  hard_nofetch_mode: verifyRun.mode,
  sources: ((snap && snap.sources) || []).length,
  claims_confirmed: (verdict.confirmed || []).length,
  claims_rejected: (verdict.rejected || []).length,
  final_status: (snap && snap.status) || 'unknown',
  no_refetch_guarantee: 'enforced by control flow — при resume полный Research пропущен, Verify/Format получают кэш; единственный санкционированный re-collect на resume — staleness re-verify устаревших time-sensitive источников (инкрементит loop_collection_calls_total, виден внешне). Verify/Format в hard-режиме идут через tool-restricted agentType без web.',
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
