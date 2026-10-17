# agent-orchestration Specification

## Purpose

让系统能够接收一个自然语言任务，由主管 agent 识别类型并路由到专职 worker agent 执行，最终汇总返回一个完整结果。

## Requirements

### Requirement: 任务路由到匹配的专职 worker
系统 SHALL 接收一个自然语言任务，识别其类型，并将任务分派给对应的专职 worker agent 执行。

#### Scenario: 翻译类任务被路由到翻译 worker
- **WHEN** 用户提交一个翻译任务（如「把这段文字翻译成英文」）
- **THEN** 系统将任务分派给翻译 worker 处理，并返回翻译后的结果

#### Scenario: 总结类任务被路由到总结 worker
- **WHEN** 用户提交一个总结任务（如「总结这段文字的要点」）
- **THEN** 系统将任务分派给总结 worker 处理，并返回总结结果

#### Scenario: 无法识别的任务类型给出明确反馈
- **WHEN** 用户提交一个系统无法识别类型的任务
- **THEN** 系统返回一条明确提示，说明当前无法处理该类型任务

### Requirement: 汇总 worker 结果并返回单一输出
当一次任务需要多个 worker 参与时，系统 SHALL 汇总各 worker 的输出，返回一个完整的单一结果。

#### Scenario: 多 worker 任务的输出被汇总
- **WHEN** 一个任务被拆解并分派给多个 worker 执行
- **THEN** 最终输出按顺序包含每个 worker 的结果，而不是零散的中间输出

### Requirement: 缺失 API Key 时快速失败并给出清晰错误
当驱动智能体所需的 API Key 未配置时，系统 SHALL 快速失败，并返回清晰的错误提示。

#### Scenario: 未配置 API Key
- **WHEN** 运行 demo 时环境变量中缺少 `DEEPSEEK_API_KEY`
- **THEN** 系统立即报错，并在错误信息中说明需要设置 `DEEPSEEK_API_KEY`
