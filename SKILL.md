---
name: poem-plate
description: 诗画：用 Codex CLI 生图画出左侧留白的古典人物插画，再用代码按固定版式竖排古诗原文与金色出处（京華老宋体），做成可直接发小红书/X 的 3:4 诗意插画。用户说「画某个古典人物配诗」「诗画」「给这首诗配图」「红楼梦人物插画」「按 poem-plate 画」时使用。
---

# poem-plate：AI 画画面 + 代码排诗

分工一句话：**生图模型只管画，代码只管排字。** 画里不放任何字，画面也不做任何重新配色。

## 0 复述
一句话说清：哪首诗、画什么场景、几张、是否成系列。成系列时所有张共用同一版式（见第 3 步），不要每张单调。

## 1 文字先核实（P0 源头）
- 诗句、诗题、作者、朝代逐字核对可靠全文（搜韵 sou-yun.cn、维基文库等），附来源 URL。用户贴来的 AI 回答也要核，可能是编的。
- 有通行异文时先问用户用哪版（例：《静夜思》教材版和宋本）。
- 选字：版式固定为两列大字，每列两句。绝句四句全上；律诗等长诗挑最有画面感的两联（四句）。

## 2 生图（codex_gen.py，画里不放字）
默认用本机 Codex CLI 内置 `image_gen`，走 ChatGPT 登录额度，不需要 API key。每首**并行出两张候选**，各是一个独立 codex 会话，约 1–2 分钟，用后台方式运行：
```bash
python codex_gen.py --prompt-file work/<诗>/prompt.txt --out work/<诗>/raw-a.png
python codex_gen.py --prompt-file work/<诗>/prompt.txt --out work/<诗>/raw-b.png
```
原件仍留在 `~/.codex/generated_images/<会话id>/`；失败时脚本打印 codex 最后 25 行输出。codex 内置生图不能指定尺寸，出图是 1086×1448（3:4）。

提示词骨架（英文，写进 prompt.txt；尖括号处替换）：
```text
A finished 3:4 portrait illustration, high resolution, in the style of a 1920s American Art Deco fashion magazine illustration, ink line art on cream paper. HARD LAYOUT RULE: imagine a vertical line at 35% of the canvas width. Everything to the left of that line, from the very top to the very bottom, is completely EMPTY plain cream paper reserved for vertical calligraphy added later. No element may cross that line: not the foreground flowers, leaves, grass, rocks, furniture, robe hems, sleeves, clouds or branches. The whole scene sits to the right of the line, and its left edge fades softly into the empty paper rather than ending in a hard vertical cut. Keep the lower-left foreground especially clear.

FIGURE: <人物，朝代服饰，动作与神态，2-4 件道具，背景>. Gold only on <2-3 处小件>.

PALETTE (strict): cream paper #f5f4ed background, near-black #141413 ink, one gold accent #B8893A. Skin and the light parts of clothing are the SAME flat cream as the paper, not beige, not yellow, no paper texture or stains on them. Gold appears only on thin pattern lines, small props and accents, never as large filled areas. Lips are a small, subtle touch of ink, no red. No other colors<: 诗里有红、绿等颜色时写明用墨画，例 the clay stove is drawn in ink, not red>.

LINEWORK: bold confident long lines, solid black masses against large empty space, crisp clean edges. Hands mostly hidden in sleeves or showing only fingertips, correct five-finger anatomy. Dignified and fully clothed.

No text, no letters, no characters, no calligraphy, no seal stamp, no signature, no watermark anywhere in the image.
```
- 朝代服饰写明（Tang round-collar robe、Southern Song zhiduo 等），否则常画成民国或日式。道具也查朝代：唐代没有玻璃灯罩油灯。
- 人物神态贴诗意：每首写一句「诗意 → 姿态/眼神/道具」的翻译放进 FIGURE。
- 手是最大风险：提示里让手少露；选图时逐张放大看手指数。
- 挑图标准：左侧 35% 真的空着（越界会压字）、手、朝代道具、画风统一。两张都越界就加强边界描述重出。

## 3 排字（typeset.py，固定版式）
```bash
pip install numpy pillow
python typeset.py work/<诗>/raw-b.png work/<诗>/<诗>_定稿.png \
    --lines 绿蚁新醅酒 红泥小火炉 晚来天欲雪 能饮一杯无 \
    --title 问刘十九 --dynasty 唐 --author 白居易
```
- 第 1、2 句排右列，第 3、4 句排左列；出处自动拼成「《诗题》朝代·作者」，`--source` 可整串覆盖。
- 固定版式（按 1086 宽实测，其他尺寸按宽度等比缩放）：京華老宋体（`fonts/KingHwaOldSong.ttf`）；大字 62 号、墨迹高 57px、字距 69.6px，笔画描边加粗 0.016；两列中心距 100px；两句之间多空 64px；上边距 96px，左边距约 89px；出处金色 `#B68F44`，35 号，竖向中心对齐左列；不加系列小字、不加署名。
- 画面原样保留，不缩放、不重新配色。脚本会量文字右缘和同高度范围内画面的左缘，不足 30px 就把整幅画右移补够（右边裁掉的是本来就出血到画布外的部分），右移超过 80px 会警告，这时应换图或重出。
- 每次运行都会打印右移量、字号和各列的上下范围，交付前看一眼。
- 改版式只改 `typeset.py` 顶部常量；系列中途不要改。

## 4 检查
- 逐字对照第 1 步的原文核对成品上的每个字，包括书名号方向（竖排应朝上、朝下）。
- 放大看手、朝代道具、文字和画之间的空隙。
- P0：错字漏字、手畸形、服饰或道具朝代错、暴露或性感化、文字压画。P0 不清零不交付。
- 需要更严时，用一个强模型按线条 / 动势 / 留白 / 古典 / 结构 / 神韵六项打分，评审提示词里逐字给原文。

## 5 交付
每首：定稿 PNG（文件名带「定稿」，之后再改不覆盖它）、生图原图、候选对比和最大缺点。系列再拼一张总览。不替用户发帖。

## 备用：旧版合成（compose_lib.py）
原作者的做法：把画缩小推到右侧、重新映射成纸/墨/金三色、再排字加署名（`example_compose.py`，画布 1500×2000）。只适合原本就是纯纸墨金三色的生图结果；GPT 生图的米色皮肤和衣料会被误判成金色，出现大片斑驳金黄，所以默认不用。

## v2 补充：动漫角色判词版
- 判词按红楼判词的格式写：七言或五言四句，押平水韵，逐句标平仄，粘对要合，不出现重字，拗句要救。每句至少藏一个剧情典故（发色、标志道具、关键事件、名台词）。不要写成散文式长短句，也不要直接摘抄台词。
- 画法从 styles/classical-styles.md 里选一种，再定色板：纸色、墨色，加一种强调色。
- 做系列时，后面每张都拿第一张已过审的图当风格参考（`codex_gen.py --ref`），提示词里写明 "only drawing style from reference"。为了在单色里认出角色：发色用强调色或墨线排线表示，标志武器和发饰必须画出来。
- 局部修补：把出问题的那一块裁下来，只让模型重画这一块，再羽化贴回原图。
- 枝条从画面上缘伸进来时，上边要设成出血，否则看起来像被平切。
- 评审时附上手部和道具的特写，同时让评审核对平仄和典故。
