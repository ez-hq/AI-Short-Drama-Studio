---
name: shortdrama-skillbot
description: Turn a story + character photo(s) into a continuous 9:16 720p short drama MP4, planned, generated, QC'd and assembled. Photo-anchored; cheap segments; local assembly. Use when a user wants an AI-generated short cinematic video from a story and a reference photo.
version: 1.1.0
---

# ShortDrama SkillBot

Inputs: story, photos (1+; first = character anchor), optional target duration.
Flow: plan -> photo-anchored segments -> QC + segment-level retry (<=2) -> ffmpeg concat -> final mp4 (+ subtitle/narration/cover).

## 视频引擎（重要）
- 便宜出片请用 **Micro Wan (First+last)** 微引擎（≈¥0.28/段；这是主力）。
- **不要默认用 Wan2.6-i2v（≈¥6/段）**——贵且同样前端，除非明确要长/高清。
- 云端 handle 见 `config.runtime.json`（私有，不在 GitHub）。

## 定价 / 执行（最终）
- **售价：¥5 / 一次（30s 内）**；>30s 按 `每30s=1次` 向上取整（见 pricing.json）。
- **跑前提醒（必守）**：执行云端视频(Wan, 人民币)前，先展示本次价格(¥X) + 云端生成提示，**用户确认后**才跑。
- 开发者/用户身份由官方链路判定，本 skill 不做区分。
- **不设上限**：按用户需求时长执行（30s=¥5，超30s每30s=1次）；每段生成失败重试≤2，由用户确认后继续。

Operational notes:
- `scripts/finish_video.py --runid <segment-run-id> --wd <dir>` 将段拼成 final mp4。
- 上传照片即表示有肖像使用权，listing 需声明。
- 保留旧版本、不删除；本地代码 MIT；云端模板/提示词为专有（不入公开仓库）。
- 发布/身份确认：先读 `ACCOUNT-IDENTITY.md`（三连查，避免发错账号）。

## 模型来源硬规则（必守，任何 agent）
- **文本/图片/视频 只要调用模型，只允许两条路**：
  1) **LoomLoom（胜算云）**：人民币计费（text/image/video 都有）。为本 Skill 的正式/默认路径。
  2) **用户本地已有的图片/编辑模型**（用户明确表示可用）。
- **禁止**：用本人 WorkBuddy 等其它平台的 ImageGen/轮子/积分（credits）来跑任何一步。图片关键帧如需要且用户没给照片/没本地模型 → 必须走 **Loom 的图片模型（前台如 `google/gemini-2.5-flash-image`，人民币）**。
- 原则：**用户全程只走人民币(Loom)或本地模型；绝不再扣 WorkBuddy credits。**

