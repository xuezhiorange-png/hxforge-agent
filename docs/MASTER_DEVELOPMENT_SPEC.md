# HXForge 换热器设计 Agent 开发实施规范

版本：0.1.0

## 1. 产品定位

HXForge 是工程辅助设计系统，用于换热器技术筛选、热工水力计算、结构初设、材料与成本分析、方案对比、仿真任务编排和标准化报告生成。系统首期覆盖套管式、壳管式、板式、空冷器和微通道换热器。

系统不自动签章，也不自动出具法定合规结论。涉及承压边界、危险介质、疲劳、振动、地震、风载、焊接、无损检测和法定检验的最终结论，必须由具备资质的工程师审核，并使用合法授权的标准文本和企业规则。

## 2. 核心原则

### 2.1 确定性内核与 Agent 分离

所有工程数值由确定性、版本化的 Python 函数计算。大模型只负责需求理解、工作流规划、工具调用、结果解释、方案对比和报告组织，不得自由生成最终工程数值。

### 2.2 全过程可追溯

每次计算保存输入快照、单位、物性后端、关联式 ID、适用范围、中间量、收敛状态、警告、软件版本、Git commit 和结果哈希。

### 2.3 SI 内核

API 支持多种单位制，内核统一使用 SI。禁止在公共接口传递无单位裸值；绝对温度和温差必须分开处理。

### 2.4 分级精度

- L0 Screening：技术路线筛选和快速估算。
- L1 Sizing：0D 或分区解析模型进行结构初设。
- L2 Rating：给定结构的完整热工水力核算。
- L3 Simulation：1D、CFD 和 FEA，用于高风险或局部问题。

## 3. 功能范围

用户输入两侧流体、流量、进出口状态、允许压降、设计压力温度、污垢系数、材料限制、安装条件、成本边界和标准体系后，系统应完成：

1. 输入完整性、单位和物性可用性检查。
2. 热平衡、相态识别和换热区段划分。
3. 候选换热器技术筛选与排序。
4. 可制造结构枚举、Sizing 和 Rating。
5. 热工、水力、初步机械、材料、清洗、结垢、腐蚀、振动和冻堵风险检查。
6. BOM、重量、制造复杂度、CAPEX、OPEX 和全寿命成本估算。
7. 多方案 Pareto 对比和推荐理由。
8. 标准化计算书、数据表、报告和计算追溯附件。
9. 0D/1D 模型以及 CFD/FEA 任务准备、执行和后处理。

首期支持稳态单相液体和气体、套管式完整闭环、壳管式和板式单相初步设计、技术筛选、材料建议、参数化成本、方案对比及 HTML/PDF 报告。

两相换热、空冷器完整风机联算、微通道流量分配、详细机械设计、CFD、FEA 和 CAD 参数化在后续里程碑实现。未实现能力必须返回 `NOT_IMPLEMENTED`，不得伪造结果。

## 4. 总体架构

```text
Web / CLI
  -> FastAPI
  -> Agent Orchestrator
  -> Engineering Application Services
  -> Deterministic Engineering Kernel
  -> PostgreSQL / Object Storage / Task Queue
```

Agent 编排层包含需求解析、工作流规划、工具路由、结果批判器和报告组织器。工程应用层包含工况、技术筛选、Sizing、Rating、优化、成本、仿真和报告服务。工程内核包含单位、物性、关联式注册中心、热平衡、几何生成器、机械边界、材料规则、成本模型和计算追溯。

首期采用模块化单体。CFD 和 FEA Worker 独立容器化，但不提前拆分大量微服务。

## 5. 技术栈

- Python 3.11+
- FastAPI、Pydantic
- NumPy、SciPy、Pint
- CoolProp；REFPROP 为可选商业后端
- SQLAlchemy、Alembic、PostgreSQL
- Redis 与 Celery 或 Dramatiq
- pytest、Hypothesis、Ruff、mypy
- Jinja2 与 HTML/PDF 渲染
- Docker；生产环境按需使用 Kubernetes
- OpenFOAM、CalculiX 或 Code_Aster、FreeCAD/OCCT 作为后续适配器

## 6. 领域模型

核心对象包括：

- `FluidSpec`：物性后端、流体标识、组分和相态提示。
- `StreamSpec`：流量、温度、压力、允许压降、污垢、固含量和危险性。
- `DesignConstraints`：设计压力温度、腐蚀裕量、寿命、外形、材料和标准体系。
- `DesignCase`：不可变工况版本。
- `CalculationRun`：运行 ID、输入快照、版本、追溯、警告和结果。
- `DesignCandidate`：设备类型、结构、性能、材料、成本和风险。

修改工况时创建新 revision，不覆盖历史。

## 7. 物性和关联式

物性统一通过 `PropertyProvider` 接口调用，至少支持 `state_tp`、`state_ph`、饱和状态和相态判断。每次调用保存后端名称、版本、流体、输入状态、输出属性和范围状态。

每个关联式必须在注册中心登记：

- 唯一 ID 和版本；
- 用途、几何和相态；
- Reynolds、Prandtl、粗糙度等适用范围；
- 文献来源；
- 不确定度；
- 超范围处理策略。

业务代码中禁止散落匿名公式。超出适用范围时必须更换模型、返回警告或阻止推荐。

## 8. 设备模块

### 8.1 套管式

作为首个完整垂直切片，支持圆管和环隙单相换热、LMTD、epsilon-NTU、换热系数、直管与局部压降、回弯损失、管径和长度枚举、hairpin 数量、材料重量和成本。

### 8.2 壳管式

第一阶段支持常用 TEMA 型式、固定管板/U 管/浮头基本选择、管程、简化壳程、管数管排、折流板、壳径、压降、污垢、热膨胀提示和初步成本。第二阶段增加 Bell-Delaware、泄漏与旁路修正、流致振动、冷凝、蒸发、再沸器和详细机械适配器。

### 8.3 板式

支持可拆式、钎焊式和半焊式。计算板片数量、通道、波纹几何、水力直径、通道和端口压降、流程组合、垫片兼容性和 CIP 风险。厂家专有板型通过授权目录导入，不伪造通用板片并声称等同厂家选型。

### 8.4 空冷器

支持强制通风和引风、翅片管束、空气侧换热与压降、翅片效率、风量、迎面风速、风机功率、海拔、热风回流、噪声、防冻、占地和运行成本。

### 8.5 微通道

支持多孔扁管、百叶窗翅片、集流管、回路、单相与两相分区、压降、充注量和流量不均风险。模块拆分为核心模型、分配模型、结霜模型和 CFD 适配器。

## 9. 机械、材料和标准

机械模块分为：

- M0：设计条件和材料边界。
- M1：壳体、封头和管子初步厚度。
- M2：法兰、管板、接管、膨胀节和支座。
- M3：疲劳、局部应力、外载和 FEA。
- M4：制造、焊接、NDE 和法定文档。

首期只承诺 M0/M1，并在报告中明确为初步机械设计。

标准采用外部规则包管理，可配置 ASME VIII-1、TEMA、API 660、API 661、ISO 16812、ISO 13706、ISO 15547-1、AHRI 410 和企业规则。开源仓库不提交标准全文、商业物性文件、厂家保密目录或客户数据。

材料模块输出接液和非接液材料、管/壳/板/翅片/垫片/钎料/紧固件/涂层、腐蚀裕量、相容性等级、替代方案、风险、重量和成本。所有建议必须显示证据、温度范围、介质限制和不确定性。

## 10. 成本和优化

成本分为 C0 经验估算、C1 材料重量与工时、C2 历史项目和厂家目录回归、C3 供应商询价。每个结果必须带币种、地区、基准日期、税费与安装口径、来源和误差区间。

全寿命成本包括泵和风机功率、清洗、备件、维护、停机损失、污垢能耗、折现率、寿命和残值。

优化采用两阶段：先枚举标准化、可制造的离散结构并执行硬约束过滤，再进行局部连续优化和多目标排序。不得让优化器产生任意但不可采购的尺寸。

## 11. Agent 工具和状态机

Agent 只能调用白名单工具：

`validate_case`、`resolve_units`、`resolve_fluid`、`calculate_properties`、`classify_thermal_service`、`solve_heat_balance`、`screen_technologies`、`generate_geometry_candidates`、`size_candidate`、`rate_candidate`、`check_mechanical_boundary`、`select_materials`、`estimate_cost`、`optimize_candidates`、`run_uncertainty_analysis`、`prepare_simulation`、`run_simulation`、`verify_results`、`generate_report`。

状态机：

`DRAFT -> INPUT_VALIDATED -> THERMAL_SERVICE_RESOLVED -> TECHNOLOGIES_SCREENED -> CANDIDATES_GENERATED -> CANDIDATES_RATED -> ENGINEERING_CHECKED -> COSTED -> VERIFIED -> REPORT_READY`

严重错误进入 `BLOCKED`，不得强行生成推荐方案。

## 12. API 和数据

建议端点包括：

- `POST /v1/projects`
- `POST /v1/cases`
- `POST /v1/cases/{id}/validate`
- `POST /v1/cases/{id}/screen`
- `POST /v1/cases/{id}/design`
- `POST /v1/cases/{id}/rate`
- `POST /v1/cases/{id}/optimize`
- `POST /v1/cases/{id}/simulations`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/trace`
- `POST /v1/runs/{run_id}/reports`

核心表包括 projects、design_cases、case_revisions、calculation_runs、calculation_nodes、design_candidates、catalogs、standard_rule_sets、cost_bases、simulation_jobs、reports、reviews 和 audit_logs。

## 13. 仿真和报告

0D 用于快速设计、核算和参数扫描；1D 沿程计算温度、压力、焓、干度、局部换热系数、壁温和污垢；CFD 自动生成几何、网格、边界、求解器和后处理配置；FEA 用于管板、集流管、接管、支座和热应力。

仿真必须检查网格独立性、边界条件、湍流模型、壁面处理、物性温度依赖、质量和能量守恒。CFD/FEA 结果不能天然视为正确。

标准报告包含设计依据、输入、热平衡、技术筛选、候选方案、推荐结构、热工、水力、初步机械、材料 BOM、成本、方案对比、风险、仿真、计算追溯和审核页。

## 14. 测试和质量门槛

测试包括单元测试、属性测试、集成测试、Golden 测试、回归测试、性能测试、安全测试和仿真验证。基准来源按公开算例、内部手算、投运实测、厂家选型、商业软件和试验台数据排序。

首期门槛：

- 能量不平衡小于 0.1%；
- 核心模块覆盖率不低于 90%；
- 无未处理 NaN/Inf；
- 所有外推有显式警告；
- 同一输入重复运行一致；
- Golden 变化必须人工批准；
- 报告包含全部输入、版本和警告。

## 15. GitHub 工作流

采用受保护的 `main` 和短生命周期 `codex/*`、`feat/*`、`fix/*`、`docs/*` 分支。所有功能通过 Pull Request，使用 Conventional Commits、SemVer、CODEOWNERS 和 GitHub Actions。

PR 必须通过 Ruff、mypy、pytest、coverage、Golden regression、dependency audit、secret scan、文档构建和 Docker 构建。公式变更必须由工程 CODEOWNER 审核。

仓库禁止提交标准全文、REFPROP 授权文件、厂家保密目录、客户工况、密钥、许可证、CFD 大结果和网格。

## 16. 里程碑

- M0：工程规则、输入输出、标准矩阵、20 个基准案例和验收指标。
- M1：单位、领域模型、物性接口、关联式注册、追溯、API、数据库和报告骨架。
- M2：套管式完整 Sizing/Rating、结构枚举、材料、成本、优化和 Golden Cases。
- M3：壳管式单相。
- M4：板式单相。
- M5：空冷器。
- M6：冷凝、蒸发和制冷剂。
- M7：微通道。
- M8：1D、CFD、FEA 和 CAD。
- M9：企业权限、目录、价格库、历史项目反标定、部署和灾备。

M2 是架构验收点，未通过前不并行铺开全部设备类型。

## 17. v0.1.0 承诺

v0.1.0 只承诺单相液-液/气-液套管式、单相壳管式初步设计、技术筛选、材料建议、参数化成本、方案比较、可追溯计算、HTML/PDF 报告、CLI 和 API。

不宣称完整 ASME/TEMA/API 合规，不宣称替代 HTRI、Aspen EDR 或厂家选型软件，也不宣称两相、微通道、CFD 和 FEA 已达到自动采购或法定设计精度。
