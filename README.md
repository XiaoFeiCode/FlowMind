<p align="center">
  <h1 align="center">FlowMind · 汇智智能客服系统</h1>
  <p align="center">基于 LLM 驱动的多轮对话系统 — 让大模型理解，让框架控制，让开发者专注业务</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/LangGraph-0.2+-orange.svg" alt="LangGraph">
  <img src="https://img.shields.io/badge/LangChain-0.3+-green.svg" alt="LangChain">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-teal.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey.svg" alt="License">
</p>

---

## 📖 项目简介

FlowMind 是一个基于 **LangGraph 图式编排** 的 LLM 驱动智能对话系统框架，专为电商客服场景设计。核心设计思想是 **「命令驱动」**——大模型不直接生成回复，而是生成结构化命令（StartFlow / SetSlot / KnowledgeAnswer 等），由框架调度执行，兼顾理解灵活度与流程可控性。

### ✨ 核心特性

- **🧠 命令驱动架构** — LLM 生成结构化命令，系统解析执行，解耦理解与控制
- **🔀 LangGraph 五节点流水线** — Understand → Policy → Action → Guard → Response，支持单轮多命令循环执行
- **📋 YAML 声明式 Flow 引擎** — 7 种步骤类型，零代码扩展业务流程
- **🔄 对话栈管理** — 原生支持 Flow 中断、嵌套、恢复，多模式无缝切换
- **🔍 GraphRAG 知识检索** — Neo4j 七步检索流水线，支撑复杂问答与多跳推理
- **🎯 双策略融合决策** — FlowPolicy（任务型）+ EnterpriseSearchPolicy（知识型/闲聊型）
- **🔌 多渠道接入** — REST API / WebSocket / Console，一套代码多端服务

---

## 🏗️ 系统架构

```
用户输入
   │
   ▼
┌──────────────────────────────────────────────────┐
│                  LangGraph 消息处理图               │
│                                                    │
│   START → [understand] → [policy] → [action]      │
│                          ↑           │             │
│                          └─[guard]───┘             │
│                                      │             │
│                                  [response] → END  │
└──────────────────────────────────────────────────┘
   │        │            │              │
   ▼        ▼            ▼              ▼
 LLM命令   策略决策    动作执行        响应组装
 生成器    集成器      注册表           & 发送
```

### 五大核心节点

| 节点 | 职责 | 核心逻辑 |
|------|------|----------|
| **understand** | 对话理解 | LLM生成命令文本 → CommandParser解析 → CommandProcessor执行 |
| **policy** | 策略决策 | PolicyEnsemble 按优先级选择 FlowPolicy / EnterpriseSearchPolicy |
| **action** | 动作执行 | ActionRegistry 查找、执行、支持 fallback |
| **guard** | 循环守卫 | 检查 action_count 防止死循环，决定继续或退出 |
| **response** | 响应组装 | 收集执行结果，标记会话完成，返回最终回复 |

### 命令系统（Command）

LLM 不直接输出自然语言，而是生成结构化命令：

| 命令 | 示例 | 作用 |
|------|------|------|
| `StartFlowCommand` | `StartFlow(flow="query_logistics")` | 启动业务流程 |
| `SetSlotCommand` | `SetSlot(name="order_id", value="12345")` | 填充槽位 |
| `KnowledgeAnswerCommand` | `KnowledgeAnswer(query="退货政策")` | 触发知识检索 |
| `ChitChatAnswerCommand` | `ChitChatAnswer()` | 处理闲聊 |
| `CancelFlowCommand` | `CancelFlow(flow="query_order")` | 取消当前流程 |
| `CannotHandleCommand` | `CannotHandle(reason="权限不足")` | 无法处理时降级 |

### Flow 流程引擎

YAML 声明式定义，7 种步骤类型：

```yaml
# 示例：订单查询 Flow
query_order_detail:
  description: 查询订单详情
  steps:
    - collect: order_id                      # COLLECT — 收集订单号
      ask_before_filling: true
      next:
        - if: slots.order_id != "false"       # CONDITION — 条件分支
          then:
            - action: action_get_order_detail  # ACTION — 查询订单
              next: END
        - else: END
```

| 步骤类型 | 说明 | 使用场景 |
|----------|------|----------|
| **ACTION** | 执行动作 | 查数据库、调API、发消息 |
| **COLLECT** | 收集槽位 | 让用户提供订单号、地址等 |
| **CONDITION** | 条件分支 | 根据槽位值走不同路径 |
| **LINK** | 切换Flow | 结束当前跳转到新Flow |
| **CALL** | 调用子Flow | 嵌套执行，完成后返回 |
| **SET_SLOT** | 程序化设槽位 | 批量初始化槽位值 |
| **END** | 结束标记 | Flow 正常终止 |

---

## 📁 项目结构

```
llm_customer_service/
├── flowmind/                      # 核心框架包
│   ├── agent/                        # Agent 层
│   │   ├── agent.py                  # Agent 主类
│   │   ├── actions.py                # 动作注册与内置动作（15+）
│   │   └── graph/                    # LangGraph 编排
│   │       ├── builder.py            # 图构建器（五节点）
│   │       ├── state.py              # 状态定义
│   │       ├── edges.py              # 条件边逻辑
│   │       └── nodes/                # 节点实现
│   ├── core/                         # 核心层
│   │   ├── tracker.py                # 对话状态追踪器
│   │   ├── domain.py                 # 领域定义
│   │   ├── slots.py                  # 槽位系统（6种类型）
│   │   └── stores/                   # 存储后端（JSON/MySQL/Memory）
│   ├── dialogue_understanding/       # 对话理解层
│   │   ├── commands/                 # 命令系统（6种命令）
│   │   ├── generator/                # LLM命令生成 & 解析
│   │   ├── processor/                # 命令处理器
│   │   ├── stack/                    # 对话栈（6种栈帧）
│   │   └── flow/                     # Flow定义/加载/执行
│   ├── policies/                     # 策略层
│   │   ├── flow_policy.py            # FlowPolicy（优先级100）
│   │   ├── enterprise_search_policy.py # EnterpriseSearchPolicy（优先级50）
│   │   └── policy_ensemble.py        # 策略集成器
│   ├── nlg/                          # 自然语言生成
│   │   ├── template_nlg.py           # 模板层（变量替换）
│   │   └── response_rephraser.py     # LLM重述层（4种风格）
│   ├── channels/                     # 通道层
│   │   ├── rest_channel.py           # REST API
│   │   ├── socketio_channel.py       # WebSocket
│   │   └── console_channel.py        # 命令行交互
│   ├── retrieval/                    # 检索基类
│   ├── cli/                          # CLI工具（6个子命令）
│   ├── training/                     # 训练 & 微调
│   └── shared/                       # 配置/常量/LLM客户端
├── ecs_demo/                         # 电商客服 Demo
│   ├── config.yml                    # 主配置
│   ├── endpoints.yml                 # 模型/数据库/存储端点
│   ├── data/flows/                   # Flow YAML 定义
│   ├── actions/                      # 自定义 Action（订单/物流/售后）
│   ├── addons/                       # GraphRAG 扩展
│   └── .env.example                  # 环境变量模板
├── display_data/                     # 业务演示数据
│   ├── 业务数据准备/                   # MySQL 初始化 SQL
│   └── neo4j导入数据/                 # Neo4j 图数据库 dump
├── setup.py                          # pip install 配置
├── requirements-flowmind.txt         # 依赖清单
└── .gitignore                        # Git 忽略规则
```

---

## 🚀 快速开始

### 环境要求

- Python **3.10+**
- MySQL **8.0+**
- Neo4j **5.x**（需安装 APOC 插件）
- 阿里云百炼平台 API Key（或其他兼容 OpenAI API 的 LLM 服务）

### 1. 克隆项目

```bash
git clone https://github.com/XiaoFeiCode/FlowMind.git
cd FlowMind/llm_customer_service
```

### 2. 安装依赖

```bash
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 配置环境变量

```bash
cd ecs_demo
cp .env.example .env
# 编辑 .env，填入你的 API Key 和数据库密码
```

`.env` 文件内容：

```env
DASHSCOPE_API_KEY=你的百炼平台API_KEY
NEO4J_PASSWORD=你的neo4j密码
MYSQL_PASSWORD=你的mysql密码
EMBEDDING_MODEL=./models/bge-base-zh-v1.5
```

> ⚠️ **`.env` 已加入 `.gitignore`，不会被提交到 Git。切勿将真实密钥硬编码在代码中。**

### 4. 准备数据

#### 4.1 MySQL 业务数据

**① 创建数据库并导入表结构：**

```sql
-- 连接 MySQL 后执行
DROP DATABASE IF EXISTS ecommerce;
CREATE DATABASE ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecommerce;
SOURCE display_data/业务数据准备/ecs.sql;
```

或命令行一键导入：
```bash
mysql -u root -p --default-character-set=utf8mb4 ecommerce < display_data/业务数据准备/ecs.sql
```

**② 生成模拟数据：**

修改 `ecs_demo/actions/db.py` 中的数据库连接信息（本地开发用）或设置环境变量（Docker 用，已自动配置），然后执行：

```bash
cd ecs_demo
python gen_data.py
```

> 会生成 200 条订单 + 30 条收货地址 + 完整物流轨迹和售后记录。

#### 4.2 Neo4j 知识图谱

```bash
neo4j-admin database load --from-path=display_data/neo4j导入数据 --overwrite-destination=true neo4j
```

#### 4.3 嵌入模型

下载 [bge-base-zh-v1.5](https://huggingface.co/BAAI/bge-base-zh-v1.5) 放入 `ecs_demo/models/`

### 5. 启动服务

```bash
# 编译验证
flowmind train

# 启动可视化调试页面（推荐开发时使用）
flowmind inspect

# 或直接启动 API 服务
flowmind run
```

### 6. 测试对话

- **Web 调试页面**：访问 `flowmind inspect` 输出的地址
- **REST API**：`POST http://localhost:8000/conversations/{sender_id}/messages`
- **命令行交互**：`flowmind shell`

---

## 🛠️ CLI 工具

| 命令 | 说明 |
|------|------|
| `flowmind init` | 初始化新项目，生成目录结构和配置 |
| `flowmind train` | 验证配置，打包模型文件 |
| `flowmind run` | 启动 FastAPI 服务（REST + WebSocket） |
| `flowmind shell` | 命令行交互式对话测试 |
| `flowmind inspect` | 启动 Web 可视化调试面板 |
| `flowmind export` | 打包导出项目（tar/zip/json） |

---

## 🐳 Docker 部署（推荐）

### 服务器要求

- **系统**：Linux（Ubuntu 20.04+ / CentOS 7+），已安装 Docker + Docker Compose
- **内存**：≥ 8GB（MySQL + Neo4j + Python 应用）
- **磁盘**：≥ 10GB 可用空间

### 1. 克隆项目

```bash
git clone https://github.com/XiaoFeiCode/FlowMind.git
cd FlowMind/llm_customer_service
```

### 2. 下载嵌入模型

```bash
# 项目仓库只含配置文件，391MB 的 pytorch_model.bin 需单独下载
cd ecs_demo/models/bge-base-zh-v1.5
wget https://huggingface.co/BAAI/bge-base-zh-v1.5/resolve/main/pytorch_model.bin
cd ../../..
```

### 3. 配置环境变量

```bash
cp .docker.env.example .docker.env
vim .docker.env  # 填入 DASHSCOPE_API_KEY、MYSQL_PASSWORD、NEO4J_PASSWORD
```

### 4. 导入 Neo4j 知识图谱

```bash
# ① 先让 Neo4j 启动一次，生成数据目录结构
docker compose --env-file .docker.env up -d neo4j

# ② 等待 neo4j Healthy（约 30 秒）
docker compose ps neo4j

# ③ 停止 neo4j（导入数据要求数据库离线）
docker compose stop neo4j

# ④ 执行数据导入（dump 文件已挂载到容器的 /import 目录）
docker compose --env-file .docker.env run --rm neo4j-init

# ⑤ 导入成功后会显示 "Neo4j 数据导入完成！"
```

> 💡 如果之前已经导入过数据，`--overwrite-destination=true` 会覆盖已有数据，可放心重复执行。

### 5. 启动全部服务

```bash
docker compose --env-file .docker.env up -d
```

### 6. 查看状态

```bash
docker compose logs -f app    # 查看应用日志
docker compose ps              # 查看所有服务状态
```

### 7. 宝塔面板配置反向代理

在宝塔面板中添加反向代理：

| 配置项 | 值 |
|--------|-----|
| **代理名称** | FlowMind |
| **目标 URL** | `http://127.0.0.1:8002` |
| **发送域名** | 你的真实域名 |

服务端口映射关系：

```
用户 → 域名(HTTPS) → 宝塔 Nginx → 127.0.0.1:8002 → Docker 容器:8000
```

### 8. 测试接口

```bash
# 健康检查
curl http://127.0.0.1:8002/health

# 发送对话
curl -X POST http://127.0.0.1:8002/conversations/test/messages \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，帮我查一下订单"}'
```

---

## 🔐 安全说明

- 所有 API Key、数据库密码通过 `.env` 环境变量注入，**不硬编码在代码中**
- `endpoints.yml` 中使用 `${VARIABLE}` 占位符引用环境变量
- `.env` 已加入 `.gitignore`，`.env.example` 作为安全模板提交
- 建议生产环境使用密钥管理服务（如阿里云 KMS、HashiCorp Vault）

---

## 🧪 微调命令生成模型

为提升 LLM 命令生成准确率，使用 LoRA 对 Qwen3-8B 进行微调：

| 指标 | 数值 |
|------|------|
| 训练数据 | 10,000 条（覆盖模糊意图、多意图、口语化边界场景） |
| 基础模型 | Qwen3-8B |
| 微调方式 | LoRA（r=16, α=16） |
| 训练环境 | V100 32G 单卡 |
| 训练时长 | ~2 小时 |
| 验证损失 | 2.4 → **1.0** |
| 推理部署 | vLLM，显存 ~20G |

---

## 🎯 适用场景

- 🛒 **电商客服** — 订单查询、物流跟踪、售后处理
- 🏦 **金融客服** — 账户查询、交易记录、贷款申请
- 📞 **电信客服** — 套餐查询、账单管理、故障报修
- 🏥 **医疗导诊** — 科室导航、预约挂号、报告查询
- 🎓 **教育咨询** — 课程查询、报名流程、成绩查询

---

## 📄 License

本项目基于 [MIT License](LICENSE) 开源。

---

## 🙏 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph) — 图式编排引擎
- [LangChain](https://github.com/langchain-ai/langchain) — LLM 应用框架
- [Neo4j](https://neo4j.com/) — 图数据库
- [BAAI/bge-base-zh-v1.5](https://huggingface.co/BAAI/bge-base-zh-v1.5) — 中文嵌入模型
