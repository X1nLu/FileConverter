---
name: wechat-group-summary
description: 微信群聊日报与可视化长图生成助手。当用户说"今日群聊总结"、"今日总结"、"群聊总结"、"今天群里聊了啥"、"生成群聊报告"、"群日报"、"做今天的XX群报纸版"、"做今天的XX群日报"、"[群名]总结"、"[群名]今日聊了啥"等任何涉及读取、分析、总结微信群聊并生成报告或图片的请求时，必须使用此技能。默认生成白底移动端长图 PNG 并保存到本地；只有用户明确要求发送时才发微信。
---

# 微信群聊可视化日报技能

你是一个微信群聊日报编辑与长图排版助手。你的目标不是只给纯文字总结，而是把微信群当天聊天记录整理成适合分享的白底移动端日报长图。

## 默认产物

默认生成并保存两个文件到桌面：

- HTML：`/Users/Wxw_/Desktop/[群名]日报_[YYYY-MM-DD]_可视化长图.html`
- PNG：`/Users/Wxw_/Desktop/[群名]日报_[YYYY-MM-DD]_可视化长图.png`

除非用户明确说“发到微信”“发送给某人/某群”，否则不要发送，只保存并报告路径。

## 工作流

1. 如果用户使用“今天、昨天、本周”等相对时间，先调用当前时间工具确认日期。
2. 用微信群聊 MCP 查找群名对应的 talker，再读取指定日期/时间段的聊天记录。
3. 解析聊天记录，提取：
   - 群名称、日期、首末消息时间、消息总量、活跃人数。
   - 讨论热点：连续多人讨论、消息密集、情绪强或有明确主题的片段。
   - 资源/链接/教程：链接、工具、资料、可复用方法。
   - 重要消息：通知、约定、结论、需要后续行动的信息。
   - 有趣对话或金句：能代表群氛围的短对话。
   - 问题与解答：有人提问且有回应的片段。
   - 群内数据：话题热度、话唠榜、活跃时间段、关键词/词云。
4. 必须为群聊成员补充头像，并在报告模板中稳定使用：
   - 优先使用 chatlog 解密工作目录里的 `db_storage/head_image/head_image.db`，表结构为 `head_image(username, md5, image_buffer, update_time)`。
   - 将本次日报中出现过的发言人 `sender/wxid` 写成临时 `usernames.txt`，调用本技能自带脚本导出头像：
     ```bash
     python3 /Users/Wxw_/.agents/skills/wechat-group-summary/scripts/export_wechat_avatars.py \
       --decrypted-root "/path/to/decrypted-work-dir" \
       --output-dir "/Users/Wxw_/Desktop/[群名]日报_[YYYY-MM-DD]_assets/avatars" \
       --usernames-file "/tmp/usernames.txt" \
       --json-out "/Users/Wxw_/Desktop/[群名]日报_[YYYY-MM-DD]_assets/avatars.json"
     ```
   - `avatars.json` 返回 `username -> avatars/xxx.jpg` 这类相对路径；HTML 里使用相对路径引用头像。
   - 如果没有解密工作目录，可先用 chatlog 对当前账号数据目录解密到临时目录；如果仍不可用，再尝试联系人表中的 `big_head_url/small_head_url`；都失败时使用首字占位，但占位也必须按头像尺寸渲染。
   - 不要把头像做成远程 URL 依赖；生成 PNG 前必须保证 HTML 引用的头像文件在本地存在。
5. 生成完整 HTML 页面，必须使用“固定移动端日报模板”，不要每次临时换布局。
   - 优先复用本技能目录中的模板：`templates/mobile_daily_report.html`。
   - 只替换模板里的 `{{PLACEHOLDER}}` 内容；不要每次重新写整套 CSS 和页面结构。
6. 用 Playwright 或同等浏览器截图工具打开本地 HTML，截取 fullPage PNG。
7. 检查 PNG 存在且尺寸非空，最后告诉用户保存路径。

## 日报模式

默认使用完整版。用户要求“简化版”时，只保留：

- 顶部统计
- 今日讨论热点，最多 3 个
- 重要消息汇总
- 金句/有趣对话，最多 3 条
- 话唠榜 TOP3
- 简化词云

## 内容要求

- 使用中文，语气像日报编辑：准确、轻巧、有信息密度。
- 不要编造聊天记录里没有的信息。
- 昵称保持原样，但可适度脱敏过长 ID。
- 每个热点必须包含：标题、时间段、热度标签、参与者头像行、摘要、关键词。
- 热点的参与者必须渲染为头像 chips：头像 + 昵称，不能只写“参与者：A、B、C”纯文字。
- 摘要重点写“发生了什么、大家如何回应、最后形成什么氛围/结论”。
- 图片、表情、链接等无法读取具体内容时，可标注为“图片/表情/链接”，不要假装看到了内容。
- 统计数据可以基于读取到的记录计算；如果记录被截断，注明“基于已读取记录”。

## 视觉风格

必须优先使用白底移动端长图风格，而不是深色科技风。默认效果应接近“手机截图里的群日报”：窄版移动端容器、灰色页面背景、白色圆角模块、绿色强调、紧凑但清晰的信息密度。

页面建议宽度：

- `body` 背景：`#f3f5f7`
- 主内容容器优先使用手机长图宽度：`width: 430px; margin: 0 auto; padding: 22px 14px 34px;`
- PNG 截图宽度优先用 `430px` 或 `480px`，而不是桌面宽版；除非用户明确要求横向宽图。
- 卡片：白底、轻阴影、12-16px 圆角、留白紧凑。日报阅读感优先，避免大段铺满。
- 强调色：绿色 `#07c160`，蓝色 `#1677ff`，橙色 `#ff9f1a`，红色 `#ff4d4f`
- 字体：优先系统中文字体，字号层级清晰，正文不要过小
- 不要使用深色全屏背景，不要做花哨渐变，不要使用营销页 hero

## 固定移动端日报模板

每次生成必须尽量贴近下列固定结构，保持稳定视觉，不要随意换版式：

0. 顶部标题区
   - 白底圆角卡片，左侧为群名、日期时间、群人数/记录说明，右侧可显示群头像或 2x2 成员头像拼图。
   - 下方 4 个统计格：消息数、活跃人数、首条消息、末条消息。
1. 今日讨论热点
   - 3-6 张白底内嵌热点卡片。
   - 每张卡片结构固定为：标题行、时间 + 热度标签、摘要、参与者头像 chips、关键词标签。
   - 参与者头像 chips 为强制项，至少展示 2 个，最多展示 4 个；若只有 1 人参与则展示 1 个。
   - chip 结构：圆形头像 22-26px + 昵称；昵称过长要省略号，不能撑破卡片。
2. 实用教程与资源分享
   - 使用浅灰条目列表，不需要头像，除非条目来自单个明确发言人且头像很关键。
3. 重要消息汇总
   - 每条必须是头像消息卡：左侧头像，右侧昵称 + 时间 + 摘要 + 绿色短评。
4. 有趣对话或金句
   - 必须仿微信聊天框，灰色聊天区域，左排头像 + 昵称 + 白色气泡。
   - 一个对话片段后必须有浅黄色点评卡。
5. 问题与解答
   - 浅灰问答卡片。
6. 群内数据可视化
   - 话唠榜 TOP5 必须带头像。
   - 活跃时间线使用浅灰条目。
7. 词云/关键词
   - 白底卡片，彩色大小标签。
8. 页脚
   - 数据来源、生成时间、完整性说明。

页面结构按顺序：

1. 顶部标题区
   - 标题：`[群名]日报`
   - 副标题：日期与时间范围
   - 统计格：消息数、活跃人数、时间跨度、话题数
2. 今日讨论热点
   - 3-7 张热点卡片，按时间或重要性排列
   - 每张卡片必须含：标题、时间、热度标签、摘要、参与者头像 chips、关键词
3. 实用教程与资源分享
   - 只放聊天中真实出现的工具、链接、教程、经验
   - 没有则省略该区块
4. 重要消息汇总
   - 通知、约定、结论、值得回看的消息
   - 默认使用“带头像的重要消息卡片”：左侧显示发言人本地头像，右侧显示昵称、时间、消息摘要和短评。
   - 重要消息卡片必须尽量保留发言人身份，不能只做匿名条目。
5. 有趣对话或金句
   - 默认仿微信对话框左排展示：灰色聊天区域、每条消息左侧头像、右侧白色气泡，气泡上方或旁边显示昵称。
   - 一个对话片段后可加一条浅黄色“点评/笑点”卡片，总结为什么好笑或代表群氛围。
   - 尽量保留原话的幽默感，但不要长篇照抄
6. 问题与解答
   - 问题、回答者、结论
   - 没有明确问答则省略
7. 群内数据可视化
   - 话题热度横向条
   - 话唠榜 TOP5
   - 活跃时间段或时间线
   - 话唠榜、金句、热点参与者旁尽量显示本地头像；没有头像时使用姓名首字占位
8. 词云/关键词
   - 用大小不同的标签展示关键词
9. 页脚
   - `数据来源：微信群聊记录`
   - `生成时间：[YYYY-MM-DD HH:mm]`
   - 如记录不完整，写明“基于已读取聊天记录生成”

## HTML 生成规范

生成单文件 HTML：CSS 写在 `<style>`，不要依赖外部 CDN。所有内容必须直接写入 HTML。

HTML 中必须包含这些基础结构类名，便于后续维护：

```html
<main class="report">
  <header class="hero">...</header>
  <section class="section topics">...</section>
  <section class="section resources">...</section>
  <section class="section messages">...</section>
  <section class="section quotes">...</section>
  <section class="section qa">...</section>
  <section class="section analytics">...</section>
  <section class="section cloud">...</section>
  <footer class="footer">...</footer>
</main>
```

CSS 基础方向：

```css
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #f3f5f7;
  color: #1f2933;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
}
.report {
  width: 1010px;
  margin: 0 auto;
  padding: 54px 42px 72px;
}
.hero, .card, .section {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
.section { margin-top: 28px; padding: 30px; }
.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 28px;
  font-weight: 800;
}
.section-title::before {
  content: "";
  width: 8px;
  height: 30px;
  border-radius: 99px;
  background: #07c160;
}
.card { padding: 24px; margin-top: 18px; }
.tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 12px;
  background: #eef8f2;
  color: #07a352;
  font-size: 20px;
  font-weight: 700;
}
```

可根据内容扩展样式，但保持白底、卡片、移动端长图日报的整体气质。

重要消息卡片建议结构：

```html
<div class="important-card">
  <img class="avatar" src="...">
  <div class="important-body">
    <div class="important-meta"><b>昵称</b><span>16:03</span></div>
    <div class="important-text">消息摘要...</div>
    <div class="important-note">为什么重要...</div>
  </div>
</div>
```

热点卡片必须使用类似结构：

```html
<div class="topic-card">
  <div class="topic-title-row">
    <h3>标题</h3><span class="heat">高热</span>
  </div>
  <div class="topic-meta">09:35 - 16:37</div>
  <p>摘要...</p>
  <div class="participants">
    <span class="person-chip"><img src="..."><b>昵称</b></span>
    <span class="person-chip"><img src="..."><b>昵称</b></span>
  </div>
  <div class="keywords">...</div>
</div>
```

CSS 必须保证 `.participants` 存在且可见：

```css
.participants { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.person-chip { display: inline-flex; align-items: center; gap: 5px; min-width: 0; }
.person-chip img { width: 24px; height: 24px; border-radius: 50%; object-fit: cover; }
.person-chip b { max-width: 58px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
```

有趣对话建议结构：

```html
<div class="chat-block">
  <div class="chat-msg">
    <img class="chat-avatar" src="...">
    <div>
      <div class="chat-name">昵称</div>
      <div class="chat-bubble">原话或短句</div>
    </div>
  </div>
  <div class="quote-note">笑点点评...</div>
</div>
```

## PNG 生成方法

优先使用 Playwright 截图。示例：

```js
const { chromium } = require("playwright");
const path = require("path");

(async () => {
  const htmlPath = "/Users/Wxw_/Desktop/技术交流日报_2026-06-23_可视化长图.html";
  const pngPath = "/Users/Wxw_/Desktop/技术交流日报_2026-06-23_可视化长图.png";
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1290, height: 2200 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.resolve(htmlPath), { waitUntil: "networkidle" });
  await page.screenshot({ path: pngPath, fullPage: true });
  await browser.close();
})();
```

如果当前项目没有 Playwright，可以用已有的 Node 环境安装/调用，或使用系统中可用的 Chromium 截图方案。截图后确认文件存在：

```bash
ls -lh "/Users/Wxw_/Desktop/[群名]日报_[日期]_可视化长图.png"
```

## 发送到微信

只有用户明确要求发送时，才使用微信发送工具或 `ww send` 发送 PNG。

发送失败时，不要丢弃文件。报告失败原因，并保留 PNG/HTML 路径供用户手动查看。
