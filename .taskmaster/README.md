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

### 2. 使用 Task Master AI

```bash
# 生成任务（基于 PRD）
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

### 3. 编辑 PRD

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

