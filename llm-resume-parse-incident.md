# 简历 LLM 解析问题复盘

## 结论

原问题不是 PDF 无法抽取，也不是全文被输入上下文截断，而是三个问题叠加：

1. LLM 生成 JSON 时可能以 `finish_reason=length` 结束，返回半截 JSON。
2. `.env` 中的 `LLM_THINKING=false` 原先没有真正传给兼容接口，模型可能进行额外思考，增加延迟和输出长度。
3. LLM 虽然返回了完整 JSON，但字段形状与后端 `ResumeAnalysisResult` 不一致，例如 `skills` 返回对象数组、`evidence_spans` 返回字符串数组，Pydantic 校验失败后系统进入 fallback。

因此用户看到的是“完成但内容很差”，表面像 API 没返回，实际是“返回后被后端判定无效”。

## 验证过程

- PDF 抽取结果完整：`LI Linghao-CV.pdf` 得到约 `18,673` 个字符、`174` 行。
- 直接调用 LLM 发送全文可以返回；简化请求约 `5.5` 秒完成。
- 使用过小的 `max_tokens` 时，API 明确返回 `finish_reason=length`。
- 完整请求曾返回约 `18,440` 个字符，但随后因 schema 类型不匹配校验失败。
- 旧数据库任务状态是 `completed + fallback`，所以页面显示的是降级结果，而不是 API 原始结果。

## 解决思路

### 1. 先隔离问题边界

通过独立探针绕过业务封装，分别测试 `Hello`、短文本、5,000 字符和全文，确认网络、模型、PDF 文本和业务校验分别处于哪一层。

### 2. 修复请求和超时控制

在 [app/llm/client.py](app/llm/client.py) 中：

- 传递 `extra_body.enable_thinking`，使 `LLM_THINKING=false` 真正生效。
- 增加 `LLM_MAX_OUTPUT_TOKENS`，避免输出预算不可控。
- 正确使用流式读取超时。
- 检测 `finish_reason=length`，明确报告“输出被截断”，不再把半截内容当正常响应。

### 3. 让模型输出更容易成功

在 [app/services/job_portal_service.py](app/services/job_portal_service.py) 中明确要求：只返回 JSON、固定字段类型、限制各列表数量，并为每个简历分块设置合理的输出上限。

### 4. 兼容真实模型返回

在 [app/schemas/ai.py](app/schemas/ai.py) 中增加有限的归一化：

- `{name: "Python"}` 转为技能名字符串。
- 对象形式的经历高亮转为可展示文本。
- 字符串证据转为 `EvidenceSpan`。
- 字典形式的 `skill_evidence` 转为列表。

这不是放弃校验，而是兼容语义等价、可安全转换的返回形式。

## 修复后结果

重新解析 `LI Linghao-CV.pdf` 后：

- `analysis_mode=llm`
- `fallback_used=false`
- `schema_valid=true`
- 4 个文本分块完成
- 20 个技能、17 条经历、1 条教育、15 个项目、15 个成就、1 条发表、29 条证据

相关回归测试为 `10 passed`；完整测试中的唯一失败是既有职位导入测试，与本次 LLM 修复无关。

## 当前注意事项

完整学术简历采用分块解析，当前样例约需 100 秒。前端应持续展示 `analyzing` 状态，并展示 `analysis_mode`、错误摘要和诊断信息。此前暴露过的 API key 仍应立即轮换。
