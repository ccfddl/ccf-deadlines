## iCal Subscription:

- English: `https://ccfddl.com/conference/deadlines_en.ics`
- 简体中文: `https://ccfddl.com/conference/deadlines_zh.ics`

<img src="../../.readme_assets/screenshot_iCal.jpg" width="500px"/>

The filter is mapped to the name of iCal file in the following rules:

- one filter: `deadlines_en.ics` and `deadlines_zh.ics`
- two filters: `deadlines_{lang}_{rank}.ics` and `deadlines_{lang}_{sub}.ics`
- common filters: `deadlines_{lang}_{rank}_{sub}.ics`

For example, given filter: lang=zh, sub=AI,CG, ccf=A,thcpl=A, then it will refer to `deadlines_zh_ccf_A_AI.ics`, `deadlines_zh_ccf_A_CG.ics`, `deadlines_zh_thcpl_A_AI.ics` and `deadlines_zh_thcpl_A_CG.ics`.