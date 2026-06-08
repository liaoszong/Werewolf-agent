# BYO-key 一线供应商预设(OpenAI-compatible preset 扩展)

> 状态:brainstorm 完成,用户批准方向 + 5 点修订(2026-06-08)。下一步 → writing-plans。
> 对应路线图:P2-B 收尾(在 capabilities per-provider 之后,B5 之前/并行)。

## Context(为什么做)

P2-B 已把方向锁死:**用户自带 key、本地 Python server 执行 provider 调用、Qt 只做配置与观战**(不是 Qt 直连厂商 API)。头号卖点是「同一局每座位可接不同 AI」。当前 `PROVIDER_REGISTRY` 只有 4 个条目(deepseek / openai / anthropic / openai_compatible 自定义),供应商设置页只能配这 4 个。

参考 https://github.com/farion1231/cc-switch 的预设清单,但**只取其中的一线模型厂商**(cc-switch 大部分预设是代理 Claude 的中转网关 —— 在狼人局里是「同一个 Claude 套不同入口」,不产生不同的 AI 个性,YAGNI 排除)。目标:把一批主流厂商做成**开箱即用的预设**,用户选厂商→填 key→即可让不同座位接不同的真实 AI。

## 确定的产品决策

- **范围**:精选一线模型厂商(用户已确认勾选全部候选)。新增 9 家:`zhipu / moonshot / qwen / minimax / siliconflow / xai / gemini / modelscope / openrouter`。共 13 个 provider。
- **不做**:cc-switch 的几十个 Claude 中转网关;厂商专属 provider 类;供应商图标。

## 核心架构决策(为什么是「registry 加行」而非「前端清单」)

| | 方案 | 结论 |
|---|---|---|
| ① | 前端 base_url 清单,底层共用 `openai_compatible` 单槽 | ❌ 破坏卖点:多个厂商共用一个凭证槽会**互相覆盖 key**,无法同局并存 |
| ② | **每厂商一行 `ProviderSpec`**(独立 provider_id = 独立凭证槽 + base_url,复用 `OpenAIProvider` 类) | ✅ **采用** —— 不是写新类,只加数据行 |
| ③ | 每厂商一个新 provider 类 | ❌ 过度工程,这批全是 OpenAI 兼容线 |

**②的关键事实**:这 9 家全部讲 OpenAI 兼容协议(`Authorization: Bearer` + `{base_url}/chat/completions` + `choices[0].message.content`),所以 `provider_cls` 全部复用现有 `OpenAIProvider`,仅 `default_base_url`/`label`/`default_models` 不同。

## 单一真相源 = `provider_registry.PROVIDER_REGISTRY`

`ProviderSpec` 字段(现有 + 新增):

```python
@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str          # 也是 credential_slot(约定:credential_slot == provider_id,不另设字段)
    label: str
    provider_cls: type[BaseChatProvider]
    default_base_url: str
    models_path: str
    source_label: str
    requires_base_url: bool = False   # 语义:是否【必须用户手动填写】base_url,而非「是否有 base_url」
    default_models: tuple[str, ...] = ()   # 【新增】provider 级 UI 兜底模型(live 拉取前的下拉建议)
```

### 修订点说明(对应用户 5 条)

1. **`default_models` 随 `provider_specs` 下发给 Qt** —— 前端按当前 provider 过滤模型下拉,而非从全局 `ALLOWED_MODELS` 拿一大锅(否则选 moonshot 还会看到 grok/gemini 的模型)。`ALLOWED_MODELS` 仍是 schema/validator 的全局兜底集合,但 UI **优先**用 `provider_specs[].default_models`。
2. **source_label 沿用 generic,但 artifact 必须记真实 provider** —— `source_label` 这批统一是 `[OpenAI-compatible API output]`(不动 `VALID_SOURCE_LABELS`)。但厂商身份不能糊:per-seat `provider`(id)+ `model` **已**记录在运行时脊柱(`runtime_events.py:554/565`)、provider-turns、resolved-profile;本设计**保持并加测试守住**(混局断言每座位 `provider_id` 原样出现在 manifest/trace,不被 generic label 抹平)。base_url 可选记 hash(非秘密,nice-to-have,不阻塞)。
3. **`credential_slot == provider_id`(约定)** —— 不新增字段。凭证库已按 provider_id 键(`store.set/has/get(provider_id)`),capability/credential 状态(`providers.qwen.available` 等)天然 data-driven。spec 写死此约定,避免 Qt/server/credential API 三边各自猜。
4. **Qwen base_url 地区相关** —— registry 给默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`(北京),但 **base_url 用户可覆盖**;新加坡/国际是 `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`。设置页本就有 Base URL 框(可选/可改),海外账号自行覆盖。同类地区分裂的还有 Moonshot(`api.moonshot.ai` 国际 / `api.moonshot.cn` 国内)、MiniMax(`api.minimax.io` 国际 / `api.minimaxi.com` 国内)—— 默认取国际域名,均可覆盖。
5. **`requires_base_url` 精确语义** —— = 「是否**必须用户手动填** base_url」。这 9 家都有官方默认 base_url,故 `requires_base_url=False`;只有 `openai_compatible`(未来自定义网关)是 `True`。

### 新增 9 行(默认值)

| provider_id | label | default_base_url | requires_base_url | default_models(示例,可覆盖) |
|---|---|---|---|---|
| `zhipu` | 智谱 GLM | `https://api.z.ai/api/paas/v4` | false | `glm-4.7`, `glm-4.6`, `glm-4.5-air` |
| `moonshot` | Moonshot Kimi | `https://api.moonshot.ai/v1` | false | `kimi-k2.6`, `moonshot-v1-8k` |
| `qwen` | 阿里 Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | false | `qwen3-max`, `qwen-plus`, `qwen-flash` |
| `minimax` | MiniMax | `https://api.minimax.io/v1` | false | `MiniMax-M3`, `MiniMax-Text-01` |
| `siliconflow` | 硅基流动 | `https://api.siliconflow.cn/v1` | false | `deepseek-ai/DeepSeek-V3`, `Qwen/Qwen2.5-72B-Instruct` |
| `xai` | xAI Grok | `https://api.x.ai/v1` | false | `grok-4.3`, `grok-4` |
| `gemini` | Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | false | `gemini-3.5-flash`, `gemini-2.5-flash`, `gemini-2.5-pro` |
| `modelscope` | 魔搭 ModelScope | `https://api-inference.modelscope.cn/v1` | false | `Qwen/Qwen2.5-72B-Instruct`, `deepseek-ai/DeepSeek-V3` |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` | false | `~openai/gpt-latest`, `~anthropic/claude-sonnet-latest`, `openrouter/auto` |

**地区/入口备注**(default_base_url 均可被用户覆盖):
- `zhipu`:默认走 **Z.AI 国际入口** `api.z.ai/api/paas/v4`;**国内用户可覆盖为** `https://open.bigmodel.cn/api/paas/v4`。
- `qwen`:默认北京 `dashscope.aliyuncs.com`;国际/美国弗吉尼亚/香港账号按官方地区 URL 覆盖(如 `dashscope-intl.aliyuncs.com/compatible-mode/v1`)。
- `moonshot`:默认国际 `api.moonshot.ai/v1`;国内 `api.moonshot.cn/v1`。
- `minimax`:默认国际 `api.minimax.io/v1`;国内 `api.minimaxi.com/v1`。

> **默认模型说明**:`kimi-k2-0905-preview` 已被 Kimi 官方标记 deprecated(官方 Quickstart 现用 `kimi-k2.6`),故不作默认。其余默认值按各厂商 2026 官方文档主线商业模型选取。模型 id 时效性快(尤其 ModelScope/SiliconFlow/各家版本号),但模型定位为「离线兜底、非 allowlist」—— live 拉取/手填覆盖,风险可接受。
>
> **base_url 拼接正规化(实现+测试约束)**:`default_base_url` 统一**无尾斜杠**存储,但 `model_list_url()` 与 `{base}/chat/completions` 拼接前必须 `rstrip("/")`(用户也可能填带尾斜杠的 base,如 Gemini 官方示例 `…/v1beta/openai/`)—— 避免双斜杠/漏斜杠。`models_path="/models"` 沿用,逐 base_url 解析为 `{base}/models`(moonshot→`/v1/models`、gemini→`/v1beta/openai/models`)。少数厂商 `/models` GET 可能不存在 → `default_models` 兜底 + 手填。

## 后端切片

- **`provider_registry.py`**:`ProviderSpec` 加 `default_models` 字段;`PROVIDER_REGISTRY` +9 行(全部 `provider_cls=OpenAIProvider`,`source_label=OPENAI_COMPATIBLE_PROVIDER_SOURCE_LABEL`)。
- **`provider_contract.py`**:仅加各厂商**显示用 label 常量**(若集中管理 label);**不**新增 source_label 常量。
- **`profile_config.py`**(保持 registry-free 纯净,字面量同步,现有一致性测试守 `ALLOWED_PROVIDERS ⊇ registry`):
  - `ALLOWED_PROVIDERS` 字面量 +9 id。
  - `ALLOWED_MODELS` 加各厂商兜底模型(仅作 schema/下拉全局兜底,**不进** `_MODEL_ALLOWLIST_PROVIDERS`;后者仍只含 `fake_deterministic`,即 live provider 的 model 仍只做格式校验、不卡 allowlist)。
- **`observer_server.py`**(schema handler,`:491`):把 `provider_specs:[{id,label,default_base_url,requires_base_url,default_models}]`(从 registry 读)并入 `build_profile_schema()` 响应。server 可 import registry,profile_config 保持纯净。

## 前端切片(去硬编码,data-driven)

- **`ProviderSettingsView.qml`**:`providerCatalog`(现硬编码 4 行)+ `labelFor`(switch)改读 `ObserverClient.profileSchema.provider_specs`(13 行自动出现);左列 provider 列表加滚动(`Flickable`/`ListView`,13 行超出 320px 高度)。
- **`SeatEditorPanel.qml` / `MatchSetupView.qml`**:provider 友好标签从 `provider_specs` 取(退本地 `_providerLabel` 小 switch);模型下拉兜底优先用 `provider_specs[id].default_models`,live `providerModels[id]` 覆盖。

## 数据流(不变)

设置页选厂商 → 存 key(独立槽 `provider_id`)→ 对局页每座位选不同厂商/模型 → B3 per-seat launcher 造各自 `OpenAIProvider(base_url=该厂商)` → 真跑。capabilities per-provider(上一 slice)、凭证门、混局 `[mixed provider output]` source_label **全自动适配**(都读 registry)。

## 测试

- registry:13 家一致性;每家 `model_list_url` / `build_provider` 正确解析 base_url + `OpenAIProvider`;`default_models` 字段存在。
- **base_url 正规化**:带尾斜杠的 base(如 `…/v1beta/openai/`)经 `model_list_url` 与 chat 拼接后**无双斜杠/漏斜杠**(Gemini 尾斜杠 vs registry 无尾斜杠回归)。
- `profile_config`:`ALLOWED_PROVIDERS ⊇ registry`(现有一致性测试自动覆盖新 9 家);`_MODEL_ALLOWLIST_PROVIDERS` 仍只含 fake(live 不卡 allowlist 回归)。
- schema:`build_profile_schema()` 经 server handler 富化后含 `provider_specs`,每条含 5 字段(id/label/default_base_url/requires_base_url/default_models)。
- **artifact honesty**:混局(座位跨 ≥2 新厂商)断言 `resolved-profile` / prompt-manifest / provider-trace / 运行时脊柱里**每座位 `provider_id` + `model` 原样保留**,不被 generic source_label 抹平。
- Qt 静态契约:退「4-硬编码 providerCatalog」断言,改断言 data-driven(从 schema 派生);保持现有 objectName/凭证字段守卫。
- Qt 构建 exit 0 + 截图:设置页 13 行(滚动)、对局页某座位选 Kimi / 另一座位选 Qwen 的下拉。

## 风险

- **Qwen/Moonshot/MiniMax 地区 base_url 分裂** —— 默认取一个,强调 base_url 可覆盖(设置页已有框)。
- **部分厂商 `/models` GET 不存在** —— `default_models` 兜底 + 手填 model;live 信任格式不卡 allowlist。
- **模型 id 时效** —— 仅影响 live 拉取前的下拉建议,非 allowlist,可接受。
- **环境**:localhost / GitHub egress 在 agent shell 不稳 —— live 拉模型与 push 由用户终端验证(参考 `werewolf-env-network-test-limits`)。

## 验收

- 设置页能配 zhipu/moonshot/qwen 等任一新厂商,存 key + 获取模型(或手填 model)。
- 一局 6 座位跨 ≥2 个新厂商(如 座位1=Kimi、座位2=Qwen、座位3=Claude)真实混跑;`provider-turns.json` per-seat `provider`+`model` 诚实记录每家身份;缺某座位凭证启动前 403 点名。
