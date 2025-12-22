# Task Master AI 使用指南

## 目录结构

```
.taskmaster/
├── config.json          # Task Master AI 配置文件
├── docs/
│   └── prd.txt         # 产品需求文档（PRD）
├── templates/
│   └── example_prd.txt # PRD 示例模板
└── tasks/              # 生成的任务文件（自动生成）
```

## 快速开始

### 1. 安装 Task Master AI

```bash
# 全局安装（推荐）
npm install -g task-master-ai

# 或使用 npx（无需安装）
npx task-master-ai <command>
```

### 2. 配置 AI 提供商的 API 密钥

**重要**：Task Master AI 需要配置 AI 提供商的 API 密钥才能从 PRD 生成任务。

在项目根目录创建 `.env` 文件，并添加以下内容（选择一个提供商）：

```bash
# Anthropic (Claude) - 推荐
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 或使用 OpenAI
# OPENAI_API_KEY=your_openai_api_key_here

# 或使用 Perplexity
# PERPLEXITY_API_KEY=your_perplexity_api_key_here

# 或使用 Google Gemini
# GOOGLE_GEMINI_API_KEY=your_google_gemini_api_key_here
```

**获取 API 密钥**：
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys
- Perplexity: https://www.perplexity.ai/settings/api
- Google Gemini: https://makersuite.google.com/app/apikey

### 3. 使用 Task Master AI

```bash
# 从 PRD 生成任务（首次使用）
task-master generate

# 或使用 npx
npx task-master-ai generate

# 查看任务列表
task-master list

# 更新任务
task-master update

# 查看帮助
task-master --help
```

**注意**：如果运行 `generate` 命令时显示 "No tasks found"，请确保：
1. 已正确配置 `.env` 文件中的 API 密钥
2. `.taskmaster/docs/prd.txt` 文件存在且包含有效的 PRD 内容

### 4. 编辑 PRD

编辑 `.taskmaster/docs/prd.txt` 文件来更新项目需求，然后运行 `task-master generate` 重新生成任务。

## 配置文件说明

`config.json` 包含以下配置：
- `version`: 配置版本
- `projectName`: 项目名称
- `prdPath`: PRD 文档路径
- `templatesPath`: 模板目录路径
- `tasksPath`: 任务文件存储路径

## 更多信息

参考 [Task Master AI 官方文档](https://opendeep.wiki/eyaltoledano/claude-task-master)

