# Project Technical Documentation

## Overview
这是一个 Job Portal MVP 后端，目标是支持真实注册登录、个人资料、简历上传、职位摄取、职位匹配、申请追踪和通知。
当前职位表同时支持在线摄取与本地 CSV 数据导入；`data/job_market_data.csv` 已通过 Alembic 迁移写入 `jobs` 表。

## Architecture
- Web 层：FastAPI 路由位于 `app/api/v1/endpoints/`。
- 业务层：核心求职门户逻辑集中在 `app/services/job_portal_service.py`。
- LLM 层：统一通过 `app/llm/` 的 OpenAI 兼容客户端访问 Groq。
- 向量层：简历与职位 embedding 使用 `sentence-transformers/all-MiniLM-L6-v2`，数据库类型使用 `pgvector.Vector(384)`。
- 数据层：SQLAlchemy + Alembic + PostgreSQL。

## Key Files and Directories
- `app/services/job_portal_service.py`: 简历解析、职位匹配、申请状态、通知、摄取。
- `app/services/embedding_service.py`: sentence-transformers 向量编码。
- `app/llm/structured_client.py`: Groq 结构化输出封装。
- `app/db/session.py`: psycopg 连接时注册 pgvector。
- `app/db/base_class.py`: `Base.metadata` 的扩展钩子。
- `alembic/versions/20260831_0001_create_base_tables.py`: 基础表迁移，包含 `vector(384)` 和 HNSW 索引。
- `alembic/versions/20260905_0002_import_job_market_data.py`: 将 `data/job_market_data.csv` 导入 `jobs` 表的数据迁移。
- `data/job_market_data.csv`: 100 条职位市场样本数据，字段包含 `source_id`、`job_title`、`job_description`、`company_name`、`mid_salary_sgd`、`pay_period`、`country_location`、`city_location`。

## Setup and Runbook
- 安装依赖：`uv sync --group dev`
- 运行测试：`uv run --group dev python -m pytest -q`
- 语法检查：`uv run python -m compileall app alembic`
- 运行迁移：`uv run python -m alembic upgrade head`
- 本机 PostgreSQL 需要可用 `vector` 扩展；当前环境已为 `postgresql@14` 编译安装 pgvector。

## Testing and Verification
- 当前后端测试已通过，结果为 4 passed。
- 曾遇到的环境问题是 `python-multipart` 缺失与 PostgreSQL 14 未安装 pgvector 扩展，已处理。

## Current Decisions and Conventions
- 使用 Groq OpenAI 兼容接口，默认 `https://api.groq.com/openai/v1`。
- 使用真实向量检索，不保留假 embedding 实现。
- 上传的简历会先落盘，再抽取文本、脱敏、调用 Groq 结构化分析。
- 职位检索按向量相似度排序，并用 `MATCH_SCORE_THRESHOLD` 约束返回范围。
- CSV 导入的职位统一使用 `source = 'job_market_csv'`，`external_id` 对应 `source_id`，`external_apply_url` 目前使用稳定占位链接。
- `GET /api/v1/jobs` 现在默认返回所有 active jobs；如果用户有可用简历 embedding，再附加 `match_score` 作为相关度信息。
- `GET /api/v1/jobs` 默认按岗位名英文文本升序排序，再按公司名和入库时间做稳定排序。
- 前端 Jobs 页面仅在 `active_resume_exists` 为真时显示分数 badge；无简历时保留列表和操作按钮。
- 前端 Jobs 卡片只展示一条聚合后的 `location` 文本，避免将 `city_location` 与 `country_location` 重复渲染。
- 前端 Jobs 卡片将公司名、地点、薪资周期拆成三枚 badge 展示，不再用 `·` 拼接在一行。
- 前端 Jobs 卡片的地点信息独立成下一行，并在左侧使用 `MapPin` 图标。
- 前端 Jobs 卡片按年化薪资分为低/中/高三档，阈值约为 74.5k / 95.5k SGD，并使用蓝色系背景区分。
- 前端 Jobs 采用按钮触发搜索，输入框只保留草稿值。
- 点击搜索后先进入至少 1 秒的 `Loading jobs...` 状态，结束后一次性展示结果与居中 `primary` 蓝句子式结果卡片。

## Known Issues and Follow-ups
- 前端仍需继续对接这些后端接口。
- 生产/新机器环境要先安装 PostgreSQL `vector` 扩展，否则建表会失败。
- 如果需要真实投递地址，`job_market_data.csv` 还要补充来源链接或外部抓取映射。
