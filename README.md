# My Cursor Agent Skills

我的 Cursor Agent skills 仓库，放在 `~/.cursor/skills/`。

每个子目录是一个 skill，里面必须有 `SKILL.md`。Cursor IDE / Cursor Agent 启动时会自动扫描这个目录加载所有 skills。

## 当前 skills

- `model-perf-binary-search/` — 对 LLM 推理服务做 p50 e2e 延迟 SLO 下的最大 QPS 二分搜索，支持 Mode A（调参）/ Mode B（开启新 feature 后调优）。

## 在新机器上一键应用

### 一次性准备（任何新机器都要做一次）

如果新机器还没装 `gh` CLI：

```bash
mkdir -p ~/.local/bin && cd /tmp \
  && curl -fsSL -o gh.tgz "https://github.com/cli/cli/releases/download/v2.62.0/gh_2.62.0_linux_amd64.tar.gz" \
  && tar -xzf gh.tgz && cp gh_2.62.0_linux_amd64/bin/gh ~/.local/bin/gh \
  && chmod +x ~/.local/bin/gh && rm -rf gh.tgz gh_2.62.0_linux_amd64 \
  && grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc \
  && export PATH="$HOME/.local/bin:$PATH"
```

然后登录（按提示选 GitHub.com → HTTPS → Yes → Login with a web browser，浏览器输 device code）：

```bash
gh auth login
```

### 同步本仓库到 `~/.cursor/skills/`

```bash
# 如果 ~/.cursor/skills 已经有东西，先备份
[ -d ~/.cursor/skills ] && [ -n "$(ls -A ~/.cursor/skills 2>/dev/null)" ] \
  && mv ~/.cursor/skills ~/.cursor/skills.bak.$(date +%s)

gh repo clone Saddss/cursor-skills ~/.cursor/skills
```

重启 Cursor IDE / Cursor Agent，skills 就被加载了。

## 日常维护

修改 / 新增 skill 后提交到远端：

```bash
cd ~/.cursor/skills
git add -A && git commit -m "describe change" && git push
```

在其他机器拉取最新：

```bash
cd ~/.cursor/skills && git pull
```

## 新建 skill 的最低骨架

```
~/.cursor/skills/<skill-name>/
├── SKILL.md          # 必需。开头是 --- YAML front-matter --- 含 name + description
└── scripts/          # 可选，放 helper 脚本
    └── *.py
```

`SKILL.md` 顶部的 YAML front-matter 是 Cursor Agent 判断"什么时候触发这个 skill"的关键，参考现有 `model-perf-binary-search/SKILL.md` 的写法即可。
