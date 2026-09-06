## 2026-09-03 13:00 SGT - 接入真实 Groq / pgvector

- Request: 将后端的 AI 与向量检索改成真实 Groq / pgvector。
- Actions: 修正 `app/services/job_portal_service.py` 的 DOCX 解析与向量检索查询，补齐 `JSONB` 导入，更新 Alembic 基础迁移为 `vector(384)`，增加 `CREATE EXTENSION vector` 的建库钩子，补充 `python-multipart`、`python-docx`、`pypdf` 依赖，并为本机 PostgreSQL 14 编译安装 pgvector 扩展。
- Result: 简历解析、职位匹配、职位摄取和改写链路继续走真实 Groq + sentence-transformers + pgvector；模型和迁移可以正常生成。
- Verification: `uv run python -m compileall app alembic`，`uv run --group dev python -m pytest -q`，结果 4 passed。
- Follow-ups: 前端尚未同步这批后端接口与上传流程，后续需要继续联调。

## 2026-09-05 14:35 SGT - 导入职位市场 CSV

- Request: 将 `data/job_market_data.csv` 的关键数据整理为 `jobs` 表基础格式并写入数据库。
- Actions: 新增 Alembic 数据迁移 `alembic/versions/20260905_0002_import_job_market_data.py`，将 CSV 的 `source_id`、`job_title`、`job_description`、`company_name`、`city_location`/`country_location` 映射到 `jobs` 表字段，并为 `external_apply_url` 生成稳定占位地址。
- Result: `jobs` 表已写入 100 条来自 `job_market_csv` 的职位记录，可通过同一迁移回滚清理。
- Verification: `uv run python -m alembic upgrade head`，数据库查询确认 `select count(*) from jobs where source = 'job_market_csv'` 结果为 100。
- Follow-ups: 如需更真实的投递链接，可再把占位 `external_apply_url` 替换为外部来源的实际地址。

## 2026-09-05 14:45 SGT - 修复 Jobs 页面空列表

- Request: 让前端 `/dashboard/jobs` 默认显示所有 jobs，而不是空白页。
- Actions: 修改 `app/services/job_portal_service.py` 中的 `list_jobs()`，移除“必须有激活简历和 embedding 才返回职位”的门槛，改为始终返回所有 active jobs；新增回归测试 `tests/test_jobs.py`。
- Result: 职位列表在没有简历的情况下也会返回数据，页面不再因为缺少 embedding 而空白。
- Verification: `uv run --group dev python -m pytest -q tests/test_jobs.py tests/test_auth.py tests/test_example_items.py`，结果 4 passed。
- Follow-ups: 前端页面仍可继续保留筛选与申请功能，后续若需要可再加分页 UI。

## 2026-09-05 14:55 SGT - 隐藏无简历时的 Jobs 分数徽章

- Request: 用户没有上传简历时，Jobs 列表不显示每个岗位的分数 badge。
- Actions: 在前端 `src/app/(dashboard)/dashboard/jobs/page.tsx` 中并行获取 dashboard summary 与 jobs 列表，并基于 `active_resume_exists` 条件渲染 score badge。
- Result: 没有活跃简历时，Jobs 仍显示列表与操作按钮，但不再显示相关度百分比。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 若后续希望没有简历时连 “Tailor resume” 按钮也隐藏，可以再补一层条件。

## 2026-09-05 15:20 SGT - 去除 Jobs 地点重复显示

- Request: 前端 Jobs 卡片中的国家/城市信息不要重复显示。
- Actions: 删除 `src/app/(dashboard)/dashboard/jobs/page.tsx` 中对 `city_location` / `country_location` 的第二行展示，仅保留 `location` 一处。
- Result: 卡片现在只显示一条地点文本，不再出现 `Singapore, Singapore` 这类重复内容。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 如果后续想把 `location` 改成更规范的单一格式，可以在后端统一输出。

## 2026-09-05 15:30 SGT - Jobs 元信息拆成 badges

- Request: 将 Jobs 卡片中的公司名、地点、薪资周期改成三种 badge 展示。
- Actions: 更新 `src/app/(dashboard)/dashboard/jobs/page.tsx`，把原来的 `·` 拼接文本替换为三枚 badge，分别承载公司名、地点和 `SGD x / Period`。
- Result: Jobs 卡片头部信息更清晰，元信息不再挤成一行。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 如需进一步区分不同 badge 颜色，可以再按字段类别微调样式。

## 2026-09-05 15:40 SGT - Jobs 默认按公司名排序

- Request: Jobs 列表默认按公司名称英文文本顺序排序。
- Actions: 更新 `app/services/job_portal_service.py` 的 `list_jobs()` 排序规则，改为按公司名英文小写升序，随后按职位名和入库时间做稳定排序；新增回归测试覆盖该排序。
- Result: `/api/v1/jobs` 默认返回的职位顺序与公司名字母序一致。
- Verification: `uv run --group dev python -m pytest -q tests/test_jobs.py tests/test_auth.py tests/test_example_items.py`，结果 6 passed。
- Follow-ups: 若后续需要更严格的 locale 排序，可再按地区规则微调。

## 2026-09-05 16:00 SGT - Jobs 薪资等级背景

- Request: 引入三级薪水等级，不同等级的 job 卡片使用符合当前主题的蓝色系背景。
- Actions: 更新前端 `src/app/(dashboard)/dashboard/jobs/page.tsx`，按年化薪资计算低/中/高三档，并分别应用蓝色系 card 背景。
- Result: Jobs 卡片会根据薪资等级显示不同蓝色背景；月薪会先转换成年薪参与分级。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 当前阈值基于 CSV 分布约为 74.5k / 95.5k SGD 年化，可按产品需求继续调整。

## 2026-09-05 15:50 SGT - Jobs 地点独立换行

- Request: 每个 job 的国家/城市信息放到下一行，并在左侧增加位置 icon。
- Actions: 调整 `src/app/(dashboard)/dashboard/jobs/page.tsx`，把 `location` 从 badge 行拆出，改为独立文本行并加入 `MapPin` 图标。
- Result: 职位卡片的地点信息现在单独成行，阅读更清晰。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 无。

## 2026-09-05 16:10 SGT - Jobs 搜索输入防抖

- Request: 当前 Jobs 搜索框输入文本时页面抖动严重。
- Actions: 在 `src/app/(dashboard)/dashboard/jobs/page.tsx` 中为搜索条件增加 250ms debounce，输入值与查询请求拆分。
- Result: 搜索框输入时不再每个按键都立即触发重拉列表，页面抖动显著降低。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 若还想更丝滑，可进一步保留旧列表直到新结果返回。

## 2026-09-05 16:20 SGT - Jobs 去除加载提示

- Request: 认为 Jobs 页面抖动来自 “Loading jobs...” 文本，希望直接去除。
- Actions: 删除 `src/app/(dashboard)/dashboard/jobs/page.tsx` 中独立的 loading 提示分支，页面在拉取数据时保留原列表区域。
- Result: 搜索时不再因加载文本反复进出导致页面上下跳动。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 无。

## 2026-09-05 16:30 SGT - Jobs 改为按钮搜索与全局摘要

- Request: 不要实时搜索，改为点击搜索按钮后显示加载文本，并显示搜索结果和全局信息。
- Actions: 将 `src/app/(dashboard)/dashboard/jobs/page.tsx` 改为按钮触发搜索；加载期间显示 `Loading jobs...`；在结果上方显示 `Jobs total` 与 `salary range`；后端 `list_jobs()` 增加 `summary` 返回值。
- Result: 搜索行为不再跟着每次输入实时刷新，用户点击按钮后再统一更新结果和摘要。
- Verification: `uv run --group dev python -m pytest -q tests/test_jobs.py tests/test_auth.py tests/test_example_items.py`，`pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 如需保留上一次搜索结果直到新结果返回，也可以继续优化。

## 2026-09-05 16:40 SGT - 去除 Jobs 薪资范围摘要

- Request: 去除 Jobs 页面上的 \"Salary range\"。
- Actions: 从 `src/app/(dashboard)/dashboard/jobs/page.tsx` 删除薪资范围 badge，只保留 `Jobs total`。
- Result: 搜索结果上方不再显示薪资范围摘要。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 无。

## 2026-09-05 16:50 SGT - Jobs 默认按岗位名排序

- Request: Jobs 默认排序改为岗位名称英文文本顺序。
- Actions: 将 `app/services/job_portal_service.py` 的 `list_jobs()` 排序规则改为按 `job_title` 升序，并更新回归测试。
- Result: `/api/v1/jobs` 默认按岗位名英文顺序返回。
- Verification: `uv run --group dev python -m pytest -q tests/test_jobs.py tests/test_auth.py tests/test_example_items.py`，结果 6 passed。
- Follow-ups: 无。

## 2026-09-05 17:00 SGT - Jobs 结果摘要改为卡片

- Request: 将 `Jobs total` badge 改为一个更低矮的宽卡片，并用英文句子显示结果数量。
- Actions: 更新 `src/app/(dashboard)/dashboard/jobs/page.tsx`，把摘要 badge 改成扁平卡片，文案改为 `Search results contain xxx job(s).`。
- Result: 搜索结果摘要现在以小卡片展示，视觉上比 badge 更稳定。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 无。

## 2026-09-05 17:10 SGT - Jobs 摘要卡片居中蓝色化

- Request: 搜索结果摘要句子去除句号，并且文本水平居中，卡片改为主题蓝色。
- Actions: 更新 `src/app/(dashboard)/dashboard/jobs/page.tsx` 的摘要卡片样式，改为居中蓝色卡片，并移除句号。
- Result: 摘要卡片现在是居中的蓝色条幅，文案更干净。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 无。

## 2026-09-05 17:20 SGT - Jobs 摘要卡片切换为侧栏蓝

- Request: 搜索结果摘要卡片颜色改为左侧导航栏背景蓝色。
- Actions: 将 `src/app/(dashboard)/dashboard/jobs/page.tsx` 的摘要卡片从 sky 蓝改为 `primary` 蓝系。
- Result: 搜索结果摘要卡片与侧边导航的蓝色更一致。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 无。

## 2026-09-05 17:30 SGT - Jobs 搜索加载最短 2 秒

- Request: 搜索按钮点击后的加载状态至少持续 2 秒。
- Actions: 在 `src/app/(dashboard)/dashboard/jobs/page.tsx` 中加入最小时长控制，搜索结果返回后若未满 2 秒则继续保持 loading。
- Result: 点击搜索后 loading 反馈更稳定，不会瞬间闪退。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit -- pretty false`。
- Follow-ups: 无。

## 2026-09-05 17:40 SGT - Jobs 两段式搜索加载

- Request: 搜索按钮点击后应先只显示加载状态，持续至少 2 秒后再显示结果。
- Actions: 调整 `src/app/(dashboard)/dashboard/jobs/page.tsx` 的搜索流程，改为完成搜索后等待满 2 秒再统一提交结果；加载期间隐藏结果区并禁用搜索按钮。
- Result: 搜索界面现在是两段式反馈，先 loading，再整体切换到结果。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 无。

## 2026-09-05 17:50 SGT - Jobs 搜索最短加载改为 1 秒

- Request: 将搜索按钮点击后的最短加载时长从 2 秒改为 1 秒。
- Actions: 把 `src/app/(dashboard)/dashboard/jobs/page.tsx` 的 `MIN_LOADING_MS` 调整为 1000，并同步更新技术文档。
- Result: 搜索仍保持两段式反馈，但等待时长缩短到 1 秒。
- Verification: `pnpm lint -- src/app/(dashboard)/dashboard/jobs/page.tsx`，`pnpm exec tsc --noEmit --pretty false`。
- Follow-ups: 无。
## 2026-09-06 15:32 SGT - 修复简历 LLM API 无结果

- Request: 解决当前 `.env` 配置下简历全文发送到 LLM 后长时间无结果或被系统回退的问题。
- Actions: 为 OpenAI 兼容客户端加入 `LLM_MAX_OUTPUT_TOKENS`、`enable_thinking`、流式读取超时和 `finish_reason=length` 检测；修复结构化调用参数合并；增强简历 schema 对模型对象/字符串返回形状的兼容；收紧学术 CV JSON 提示词与单块输出上限；补充客户端和 schema 回归测试。
- Result: 确认 18,673 字符全文可返回；此前失败主要是输出截断和 schema 形状不匹配。修复后四块完整解析约 100 秒完成，未触发 fallback，产生技能、经历、教育、项目、成就、发表和证据结果。
- Verification: 真实 `Hello` 调用成功；首块真实生产链路约 28 秒通过 schema；完整四块约 100 秒完成；相关测试 10 passed；新增文件静态检查通过；`compileall` 通过。
- Follow-ups: 当前 `LLM_MAX_OUTPUT_TOKENS` 默认 8192，简历块请求使用 4096；完整解析仍受供应商延迟影响。此前暴露的 API key 应立即轮换。
## 2026-09-06 15:45 SGT - 新增简历 LLM 故障复盘文档

- Request: 将原有 LLM API 问题的原因和解决思路整理成精简 Markdown 文档。
- Actions: 新增 `llm-resume-parse-incident.md`，记录根因、验证证据、修复方法、修复后结果和注意事项。
- Result: 文档已写入后端根目录，明确区分 API 未返回、输出截断、schema 校验失败和 fallback。
- Verification: 检查文档内容与当前代码及样例重跑结果一致。
