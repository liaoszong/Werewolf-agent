#!/usr/bin/env node
/**
 * PreToolUse Hook: Config Protection (Werewolf-agent 字节锁硬墙)
 *
 * 思路源自 affaan-m/ECC 的 config-protection hook，但这是自包含、零依赖、
 * Windows 安全、贴本仓库字节门纪律的实现。与 fact-gate.cjs 同目录同风格。
 *
 * 硬墙：直接 deny 对「字节锁/golden/版本权威」文件的手工 Edit/Write/MultiEdit。
 * 这些文件只能由生成器重写或走 bump 流程，严禁手改——防「为过检查而静默改源/弱化测试」。
 *
 * 只管 Edit/Write/MultiEdit，不碰 Bash —— 合法重生成走
 * `python tools/generate_golden_prompts.py`（Bash），写 hook 永远看不到，所以硬墙不挡正经 regen。
 *
 * 与 fact-gate 不同：**子 agent 也拦**（硬墙对谁都生效，不是首触确认）。
 * 关闭/放行：本会话设 WG_CONFIGGUARD=off（合法 bump / 改 ledger 时一次性放行）。
 * 任何内部异常一律 fail-open（放行），hook 绝不阻断工具链。
 *
 * 契约：exit 0 + stdout `{hookSpecificOutput:{permissionDecision:"deny",...}}` 即拦截。
 */

'use strict';

const OFF = new Set(['0', 'false', 'off', 'no', 'disabled']);
function isDisabled() { return OFF.has(String(process.env.WG_CONFIGGUARD || '').trim().toLowerCase()); }

// 保护清单：{ match: 归一化路径判定, why: 命中时给的正路提示 }
// 路径归一化 = 反斜杠→正斜杠 + 小写；绝对/相对路径都用「结尾匹配 / 段匹配」兜住。
const GOLDEN_REGEN = 'golden 字节锁：只能由生成器重写 → `python tools/generate_golden_prompts.py`，严禁手改。';
const RULES = [
  { id: 'tests/golden_prompts/**',                        kind: 'dir',  why: GOLDEN_REGEN },
  { id: '.gitattributes',                                 kind: 'file', why: '它钉死 golden 的 `eol=lf`；改它=字节锁失效。确需改走 guarding-prompt-bytes 流程。' },
  { id: 'src/werewolf_eval/prompt_version.py',            kind: 'file', why: 'PROMPT_VERSION 权威 + docstring 规则源。版本变更走 guarding-prompt-bytes 的 bump 流程，别直接手改。' },
  { id: 'src/werewolf_eval/prompt_goldens.py',            kind: 'file', why: 'golden 样本集单源；改它=字节锁覆盖面变。走 bump 流程。' },
  { id: 'tests/test_prompt_versioning.py',                kind: 'file', why: '字节门测试本体；严禁为「让测试过」而弱化它。该修的是被测代码。' },
  { id: 'docs/generated-games/prompt-version-ledger.json', kind: 'file', why: '版本化 ledger：按既定流程手动加条目，确认要改时 WG_CONFIGGUARD=off 后重试。' },
];

function normalize(p) { return String(p || '').replace(/\\/g, '/').toLowerCase(); }

function matchRule(filePath) {
  const norm = normalize(filePath);
  if (!norm) return null;
  for (const rule of RULES) {
    const id = rule.id.toLowerCase();
    if (rule.kind === 'dir') {
      const dir = id.replace(/\/\*+$/, '').replace(/\/+$/, ''); // tests/golden_prompts
      if (norm === dir || norm.includes('/' + dir + '/') || norm.startsWith(dir + '/')) return rule;
    } else {
      if (norm === id || norm.endsWith('/' + id)) return rule;
    }
  }
  return null;
}

function denyMsg(filePath, why) {
  return [
    '[Config Protection] 字节锁硬墙',
    '',
    `禁止手工修改 ${filePath}`,
    why,
    '',
    '若这是经过流程的合法变更：本会话设环境变量 WG_CONFIGGUARD=off 后原样重试。',
  ].join('\n');
}

function deny(reason) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: reason },
  }));
  process.exit(0);
}
function allow() { process.exit(0); }

function checkPath(filePath) {
  if (!filePath) return;
  const rule = matchRule(filePath);
  if (rule) deny(denyMsg(String(filePath).replace(/\\/g, '/'), rule.why));
}

function run(raw) {
  let data;
  try { data = JSON.parse(raw); } catch (_) { return allow(); }
  if (isDisabled()) return allow();

  const TOOL = { edit: 'Edit', write: 'Write', multiedit: 'MultiEdit' };
  const tool = TOOL[String(data.tool_name || '').toLowerCase()];
  if (!tool) return allow(); // 只管 Edit/Write/MultiEdit
  const input = data.tool_input || {};

  if (tool === 'MultiEdit') {
    for (const e of (input.edits || [])) checkPath(e.file_path); // 命中即 deny+exit
    return allow();
  }
  checkPath(input.file_path);
  return allow();
}

let buf = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', c => { buf += c; });
process.stdin.on('end', () => { try { run(buf); } catch (_) { allow(); } });
process.stdin.on('error', () => allow());
