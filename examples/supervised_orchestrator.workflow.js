/**
 * supervised_orchestrator.workflow.js — ОБРАЗЕЦ / teaching skeleton (НЕ для прод-запуска как есть)
 * =============================================================================================
 *
 * Зачем он здесь.
 * AGENT.MD описывает многоагентную отказоустойчивость (watchdog, circuit breaker,
 * deadlock-детектор, авто-рестарт) как работающую распределённую систему. Внутри Claude Code
 * это исполняется одним контекстом Claude, который читает markdown. «Research / FactCheck /
 * Format agent» — роли в ОДНОМ контексте, а не процессы. Поэтому когда контекст переполняется
 * на ~20-й минуте и компактится, оркестратор теряет состояние и тихо останавливается —
 * а перезапустить его некому, ведь «супервизор» из доки живёт в том же умершем контексте.
 *
 * Этот файл показывает ПРАВИЛЬНУЮ форму «корректирующего» механизма: не пятый агент-роль,
 * а CONTROL-LOOP снаружи агентского контекста. Цикл — детерминированный JS, у него НЕТ
 * контекста, который можно потерять, поэтому он переживает смерть любого воркера.
 *
 * Контраст, который надо увидеть:
 *   - «агент-роль»  : живёт в контексте воркера, делит его судьбу, добавляет нагрузку на контекст.
 *   - «control-loop»: живёт вне воркера, ловит его падение как ДАННЫЕ, переспавнивает в ЧИСТЫЙ контекст.
 *
 * ✅ `snapshot` — реальный сериализованный снимок состояния (sources с extract'ами, claims,
 *    budget, next_phase), а НЕ строка-заглушка. correct() прокидывает его в новый спавн, поэтому
 *    переспавн продолжает с собранных данных, НЕ пере-собирая источники. Схема — AGENT.MD §8.0.
 *
 * Запуск (когда checkpoint станет реальным):  Workflow({ scriptPath: '<этот файл>', args: { topic: '...' } })
 */

export const meta = {
  name: 'deep-research-supervised',
  description: 'Внешний control-loop: спавнит research-агента, корректирует и переспавнивает на сбое',
  phases: [{ title: 'Plan' }, { title: 'Research (supervised)' }, { title: 'Verify' }, { title: 'Retro' }],
}

// Что воркер ОБЯЗАН вернуть структурой. Структура = control-plane ВИДИТ состояние,
// а не угадывает его по heartbeat-файлу, который мог и не записаться (тигр T3 из пре-мортема).
const RESULT = {
  type: 'object',
  required: ['status', 'blockedBy', 'snapshot', 'findings', 'spent', 'quality'],
  properties: {
    status:     { enum: ['done', 'partial', 'blocked'] },
    blockedBy:  { enum: ['budget', 'timeout', 'paywall', 'low_quality', 'none'] },
    snapshot:   { type: 'object',                         // сериализованный resume-снимок (AGENT.MD §8.0)
                  properties: { stage:      { type: 'string' },
                                next_phase: { type: 'number' },
                                sources:    { type: 'array', items: { type: 'object' } },  // с extract'ами
                                claims:     { type: 'array', items: { type: 'object' } },
                                budget:     { type: 'object' } } },
    findings:   { type: 'array', items: { type: 'object' } },
    spent:      { type: 'number' },
    quality:    { type: 'number' },                       // 0-100
  },
}

// ЭТО и есть «корректирующий агент» — но это КОД, не LLM-персона, и он живёт СНАРУЖИ
// контекста воркера, поэтому переживает его смерть. Детерминированное правило коррекции:
function correct(prev) {
  // Прокидываем РЕАЛЬНЫЙ снимок в новый спавн: уже собранные sources/claims не пере-собираются.
  const resume = prev?.snapshot
    ? `Возобнови по сохранённому состоянию (НЕ пере-собирай sources со status rendered/done):\n${JSON.stringify(prev.snapshot)}\n`
    : ''
  switch (prev?.blockedBy) {
    case 'budget':      return `${resume}Бюджет на исходе: только Tier-1, финализируй по собранному.`
    case 'timeout':     return `${resume}Источник завис: пропусти, failover на следующий tier.`
    case 'paywall':     return `${resume}Paywall: НЕ эскалируй человеку, возьми открытые альтернативы.`
    case 'low_quality': return `${resume}quality<70: переразбей слабую subtask на узкие запросы.`
    default:            return null                       // первая попытка — коррекции нет
  }
}

phase('Plan')
const plan = await agent(`Декомпозируй задачу и дай план сбора: ${args.topic}`)

phase('Research (supervised)')
let state = null
const attempts = []
for (let i = 1; i <= 4; i++) {                            // bounded respawn — заменяет невнятный «2×interval watchdog»
  const fix = correct(state)
  const directive = `${fix ?? 'Выполни план. Верни структурой состояние + возобновляемый checkpoint.'}\n\nПлан:\n${plan}`
  try {
    // СВЕЖИЙ subagent = СВЕЖИЙ контекст. Накопление контекста, убивающее схему на 20-й мин,
    // обнуляется на каждом спавне. Состояние держит JS-цикл, а он не компактится.
    state = await agent(directive, { schema: RESULT, label: `research:try-${i}`, phase: 'Research (supervised)' })
  } catch (e) {
    // Воркер умер (throw BudgetExceededException и т.п.). Цикл — жив, он здесь, снаружи.
    // Реальный код классифицирует причину по `e`; здесь консервативно считаем бюджетом.
    state = { status: 'blocked', blockedBy: 'budget',
              snapshot: state?.snapshot ?? { stage: 'cp_00', next_phase: 1, sources: [], claims: [], budget: {} },
              findings: state?.findings ?? [], spent: 0, quality: 0 }
  }
  attempts.push({ try: i, status: state.status, blockedBy: state.blockedBy, spent: state.spent })
  log(`try ${i}: ${state.status}${state.blockedBy !== 'none' ? ` (blocked: ${state.blockedBy})` : ''}`)
  if (state.status === 'done') break                      // успех
  if (state.status === 'partial' && i >= 2) break         // good-enough fallback, не жжём вечно
}

phase('Verify')
const verdict = await agent(
  `Состязательно проверь факты, помечай неподтверждённое:\n${JSON.stringify(state.findings)}`,
  { schema: { type: 'object', required: ['confirmed'], properties: { confirmed: { type: 'array' }, rejected: { type: 'array' } } } },
)

phase('Retro')   // ретроспектива — на СВОЁМ месте: ПОСЛЕ выживания, и её отдают наружу для СЛЕДУЮЩЕГО прогона
const retro = await agent(
  `По логу попыток выпиши 1-3 устойчивых урока (надёжность источников, ошибки декомпозиции): ${JSON.stringify(attempts)}`,
)

// Вызывающий персистит `retro` на диск (напр. lessons.md); следующий прогон читает его в фазе Plan.
// Это и есть кросс-прогонная память — но второй очередью, ПОСЛЕ того как прогон научился доживать.
return { findings: verdict.confirmed, attempts, retro }
