# Установка — Deep Research Skill

Навык поставляется как **плагин Claude Code** (маркетплейс на GitHub) и одновременно как **self-contained скилл**, который можно загрузить в Claude.ai.

---

## Способ 1: Claude Code / Cowork — плагин-маркетплейс (рекомендуется)

### Cowork (GUI, без файлов)

1. Открой **Customize** (слева внизу).
2. **Browse plugins → Personal → +**.
3. **Add marketplace from GitHub**.
4. Введи: `azagreev/DResearch-Skill`.
5. Установи плагин **deep-research-skill** — навык подключится автоматически.

### Claude Code (CLI)

```bash
# 1. Добавить маркетплейс из GitHub
/plugin marketplace add azagreev/DResearch-Skill

# 2. Установить плагин (формат: <плагин>@<маркетплейс>)
/plugin install deep-research-skill@deep-research-skill
```

После установки навык активируется автоматически по запросам вроде «проведи исследование», «deep research», «анализ рынка». Явный вызов: `/deep-research-skill:deep-research-skill`.

### Локальная проверка перед публикацией (из клона)

Маркетплейс можно добавить из локальной папки — удобно, пока репозиторий не на GitHub:

```bash
git clone https://github.com/azagreev/DResearch-Skill.git
cd DResearch-Skill
/plugin marketplace add ./           # путь до папки с .claude-plugin/marketplace.json
/plugin install deep-research-skill@deep-research-skill
```

> Относительные пути `source` в манифесте резолвятся от корня репозитория, поэтому локальное добавление работает так же, как из GitHub.

---

## Способ 2: Claude.ai (ZIP-скилл)

Навык self-contained, поэтому загружается в Claude.ai как обычный скилл:

1. Заархивируй папку `plugins/deep-research-skill/skills/deep-research-skill/` в ZIP.
   В **корне** архива должны лежать `SKILL.md` и каталог `references/`.
2. Claude → **Настройки → Возможности** → включи «Code execution and file creation».
3. **Настроить → Скиллы → +** → загрузи ZIP.
4. В любом чате попроси «проведи исследование …» — навык активируется.

---

## Способ 3: Ручная установка (Claude Code skills dir)

Скопируй self-contained папку навыка в каталог скиллов Claude:

- **macOS**: `~/Library/Application Support/Claude/skills/`
- **Windows**: `%APPDATA%/Claude/skills/`
- **Linux**: `~/.config/Claude/skills/`

```bash
cp -r plugins/deep-research-skill/skills/deep-research-skill \
      ~/.config/Claude/skills/deep-research-skill
```

Перезапусти Claude.

---

## Опционально: внешние API

Для расширенных возможностей задай ключи (все опциональны — без них работает Tier 1):

```bash
export JINA_API_KEY="jina_xxxxxxxx"            # извлечение статей
export BROWSERBASE_API_KEY="bb_live_xxxxxxxx"  # облачный браузер
export FIRECRAWL_API_KEY="fc_xxxxxxxx"         # web scraping (premium)
```

## Опционально: MCP-серверы

```json
{
  "mcpServers": {
    "browserbase": {
      "command": "npx",
      "args": ["@browserbase/mcp@latest"],
      "env": { "BROWSERBASE_API_KEY": "your-api-key" }
    },
    "file-system": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/research/output"]
    }
  }
}
```

---

## Проверка

Попроси в чате:

```
Проведи исследование трендов в AI-чипах 2026
```

Навык должен активироваться и запустить 6-фазный workflow.

### Если навык не активируется

1. **Claude Code:** `/plugin` → проверь, что `deep-research-skill` установлен и включён; при необходимости `/reload-plugins`.
2. Убедись, что версия плагина в `/plugin` → Marketplaces соответствует свежему релизу (сторонние маркетплейсы не авто-обновляются — см. README → «Обновление плагина»).
3. Попробуй явный вызов `/deep-research-skill:deep-research-skill` или фразу «deep research».

---

## Удаление

```bash
# Claude Code
/plugin uninstall deep-research-skill@deep-research-skill
/plugin marketplace remove deep-research-skill

# Ручная установка
rm -rf ~/.config/Claude/skills/deep-research-skill
```

---

## Дальше

- `plugins/deep-research-skill/skills/deep-research-skill/SKILL.master.md` — полная документация
- `references/tool_matrix.md` — доступные инструменты
- `AGENT.MD` — детали оркестрации
- [CHANGELOG.md](../CHANGELOG.md) — история версий
