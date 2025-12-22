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

**推荐方式**：复制 `env.example` 文件为 `.env`，然后取消注释并填入你选择的提供商 API 密钥。

```bash
cp env.example .env
# 然后编辑 .env 文件，填入你的 API 密钥
```

**支持的 AI 提供商**（按推荐顺序）：

1. **Anthropic (Claude)** - 推荐，性能优秀
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```
   获取密钥：https://console.anthropic.com/

2. **OpenAI (GPT-4, GPT-3.5)** - 广泛使用
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   获取密钥：https://platform.openai.com/api-keys

3. **Perplexity** - 推荐用于研究，可访问实时信息
   ```bash
   PERPLEXITY_API_KEY=your_perplexity_api_key_here
   ```
   获取密钥：https://www.perplexity.ai/settings/api

4. **Google Gemini**
   ```bash
   GOOGLE_GEMINI_API_KEY=your_google_gemini_api_key_here
   # 或
   GOOGLE_API_KEY=your_google_api_key_here
   ```
   获取密钥：https://makersuite.google.com/app/apikey

5. **xAI (Grok)**
   ```bash
   XAI_API_KEY=your_xai_api_key_here
   ```
   获取密钥：https://x.ai/

6. **OpenRouter** - 支持多种模型
   ```bash
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```
   获取密钥：https://openrouter.ai/keys

7. **Azure OpenAI**
   ```bash
   AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
   AZURE_OPENAI_ENDPOINT=your_azure_endpoint_here
   ```
   获取密钥：https://azure.microsoft.com/en-us/products/ai-services/openai-service

8. **Mistral AI**
   ```bash
   MISTRAL_API_KEY=your_mistral_api_key_here
   ```
   获取密钥：https://console.mistral.ai/

9. **Ollama** - 本地运行，无需 API 密钥
   ```bash
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2  # 或其他模型名称
   ```
   安装：https://ollama.ai/

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

