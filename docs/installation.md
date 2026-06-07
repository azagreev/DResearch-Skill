# Installation Guide

## Deep Research Skill — Installation Instructions

---

## Method 1: Claude Code CLI (Recommended)

### Step 1: Clone or Download the Repository

```bash
# Clone from GitHub
git clone https://github.com/deep-research-skill/deep-research-skill.git
cd deep-research-skill

# Or download and extract the archive
# unzip deep-research-skill.zip && cd deep-research-skill
```

### Step 2: Install via `npx skills add`

```bash
# Install the skill from the plugins directory
npx skills add ./plugins/deep-research-skill
```

The `npx skills add` command will:
1. Validate the `SKILL.md` file
2. Register the skill in Claude Desktop
3. Make it available for automatic activation

### Step 3: Verify Installation

```bash
# List installed skills
npx skills list

# You should see "deep-research-skill" in the output
```

---

## Method 2: Claude Marketplace

1. Open **Claude Code** application
2. Navigate to **Skills** → **Marketplace**
3. Search for: `deep-research-skill`
4. Click **Install** on the skill card
5. Wait for installation confirmation

---

## Method 3: Manual Installation

1. Locate your Claude Desktop skills directory:
   - **macOS**: `~/Library/Application Support/Claude/skills/`
   - **Windows**: `%APPDATA%/Claude/skills/`
   - **Linux**: `~/.config/Claude/skills/`

2. Copy the skill directory:
   ```bash
   cp -r plugins/deep-research-skill ~/.config/Claude/skills/
   ```

3. Restart Claude Desktop

---

## Post-Installation Setup

### Create Output Directory Structure

The skill uses a structured output directory for research artifacts:

```bash
mkdir -p ./research_output/
mkdir -p ./research_output/heartbeats
mkdir -p ./research_output/subtasks
mkdir -p ./research_output/sources
mkdir -p ./research_output/reports
```

> This is optional — the skill will create directories as needed.

### Optional: Configure External APIs

For enhanced capabilities, set up these optional API keys:

```bash
# Jina AI Reader — article extraction and summarization
export JINA_API_KEY="jina_xxxxxxxx"

# Browserbase — cloud browser automation
export BROWSERBASE_API_KEY="bb_live_xxxxxxxx"

# Firecrawl — web scraping (premium tier)
export FIRECRAWL_API_KEY="fc_xxxxxxxx"
```

Add these to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) for persistence.

### Optional: Configure MCP Servers

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "browserbase": {
      "command": "npx",
      "args": ["@browserbase/mcp@latest"],
      "env": {
        "BROWSERBASE_API_KEY": "your-api-key"
      }
    },
    "file-system": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/research/output"]
    }
  }
}
```

---

## Verification

### Test Basic Activation

After installation, try these commands in Claude Code:

```
"Проведи исследование трендов в AI"
```

The skill should activate automatically and begin the research workflow.

### Check Available Commands

The skill provides these automatic triggers:

| Trigger Type | Examples |
|-------------|----------|
| Research | "проведи исследование", "deep research" |
| Analysis | "анализ рынка", "конкурентный анализ" |
| Information | "собери информацию о", "что известно о" |
| Comparison | "сравни", " versus" |
| Trends | "тренды в", "обзор технологий" |
| Due Diligence | "due diligence", "внешний аудит" |

---

## Troubleshooting

### Skill Not Activating

1. Check installation:
   ```bash
   npx skills list | grep deep-research
   ```

2. Verify SKILL.md exists:
   ```bash
   ls ~/.config/Claude/skills/deep-research-skill/SKILL.md
   ```

3. Try manual activation by mentioning "deep research" explicitly

### API Rate Limits

- **Tier 1 tools** (native): No rate limits
- **Tier 2 tools** (Jina, arXiv): Free tiers available
- **Tier 3-4 tools**: Require API keys, see `references/cost_matrix_full.md`

### Token Budget Issues

- Use **Quick** depth for simple queries
- The skill automatically manages token budgets
- Check `references/cost_matrix_full.md` for estimates

### Checkpoint Recovery

If research is interrupted:
1. Re-ask the same question
2. The skill will detect previous checkpoints
3. Resume from the last completed phase

---

## Uninstallation

```bash
# Via CLI
npx skills remove deep-research-skill

# Or manually
rm -rf ~/.config/Claude/skills/deep-research-skill
```

---

## Next Steps

- Read `SKILL.master.md` for complete documentation
- Check `references/tool_matrix.md` for available tools
- Review `AGENT.MD` for orchestration details
- See `CHANGELOG.md` for version history
