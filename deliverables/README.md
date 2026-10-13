# 完整项目研究报告交付目录

报告基准为已验收的478a320c0a8146cf8dfdcbb8c0d93b16640b8594，编制日期2026-10-13。仅整合已完成研究，不训练、下载或修改科研结果。

正式稿：39页、正文13,540个汉字、451字摘要、11章、附录A-G、9幅图、15张表、21条参考文献。正文统计含标题/表图说明，排除重复图片替代文字、摘要、文献和附录。

- [可编辑完整报告](Encounter_Lab_Full_Report.md)：中文摘要、11章、21条参考文献及附录A-G。
- [证据对应清单](EVIDENCE_MAP.md)：章节、关键实现、报告和验证范围。
- [自动校验记录](REPORT_VERIFICATION.json)：公开输入SHA256、指标对账、计数与最终PDF质量检查。
- Encounter_Lab_Report_Figures/：9幅黑白SVG，仅包含聚合数据或明确标注的结构示意；可在Markdown中显示。
- Encounter_Lab_Full_Report.pdf：正式A4打印版本，仅本地交付，不加入Git。
- [排版生成器](build_report.py)与[校验器](verify_report.py)：只读取公开聚合材料和本报告，不读原始样本或模型，不变更项目依赖。

使用已有的独立文档环境执行下列命令。该环境需要reportlab、pypdf、pdfplumber及Pillow；它们不被加入应用requirements。默认字体取本机标准宋体/黑体TTC，其他环境需提供合法且支持中文的TrueType字体。

```sh
python deliverables/build_report.py
python deliverables/verify_report.py --render-dir /path/to/rendered/pages
```

PDF采用A4纵向、约2.5cm页边距、正文宋体12pt/18pt行距、首行24pt缩进、黑体章节标题、三线表和黑白线型/纹理图。目录按实际页码多轮生成。各章标题有保持规则，较短章节和附录可接续排版，避免人为制造空白页。

图6-1、6-2、6-3及7-1分别来自T17、T22、T30和T31实际公开数据，不混合实验总体；其余图为源码结构归纳，不冒充个体测量。正文汉字数口径含标题、表图说明，不计摘要、参考文献及附录。二进制成品和渲染检查文件保持本地；原安全规则与51份冻结材料不变。
