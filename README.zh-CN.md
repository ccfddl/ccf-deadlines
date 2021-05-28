# CCF-Deadlines
[![LICENSE](https://img.shields.io/github/license/ccfddl/ccf-deadlines)](https://github.com/ccfddl/ccf-deadlines/blob/main/LICENSE)
[![Build Status](https://img.shields.io/github/workflow/status/ccfddl/ccf-deadlines/Deploy)](https://github.com/ccfddl/ccf-deadlines/commits/main)
[![Open PRs](https://img.shields.io/github/issues-pr/ccfddl/ccf-deadlines)](https://github.com/ccfddl/ccf-deadlines/pulls)

简体中文 | [English](./README.md)

帮助计算机类科研人员追踪[中国计算机学会 (CCF)](https://www.ccf.org.cn/)推荐国际学术会议的截稿日期。

在线预览: [演示页面](https://ccfddl.github.io/)

[![](.readme_assets/screenshot.png)]()

**对麻烦的查找会议和转换时间说拜拜!**

## 增加/更新 会议
欢迎一起帮忙维护会议的相关信息! 如想要进一步做贡献或吹水，可通过发送邮件给[chenzh@stu.ecnu.edu.cn](chenzh@stu.ecnu.edu.cn)，请使用edu邮箱并附上wechatid，加入 [CCFDDL](https://github.com/ccfddl) 组织。

增加或删除会议信息:
- Fork 这个仓库
- 增加/更新yml文件 conference/conf_type/conf_name.yml
- 提交 [pull request](https://github.com/ccfddl/ccf-deadlines/pulls)

提示: 可检查 [会议推荐目录](.readme_assets/ccf_recommended.pdf) 和 [统计表格](https://docs.qq.com/sheet/DR3F1Tm1jcnlzVFJ2)
## 会议录入文件
示例文件: conference/DB/sigmod.yml

```
- title: SIGMOD
  year: 2021
  id: sigmod21
  description: ACM Conference on Management of Data
  link: http://2021.sigmod.org/
  deadline: '2020-09-22 17:00:00'
  timezone: UTC-8
  date: Jun 20-25, 2021
  place: Xi'an, China
  sub: DB
  rank: A
  dblp: sigmod
```
字段描述:

| 字段名         | 描述                                                                                                           |
| ------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `title`\*           | 缩写的会议名称, 不需要年份, 大写                                                                             |
| `year`\*            | 会议的年份                                                                                      |
| `id`\*              | 会议名字和年份, 小写                                                                                          |
| `description`\*     | 介绍, 或全称, 可以的话加上第几届, 示例, The 15th XXX                                                                                           |
| `link`\*            | 会议首页的URL                                                                                       |
| `deadline`\*        | 截稿日期, 格式为 `yyyy-mm-dd hh:mm:ss` or `TBD`                                                                     |
| `abstract_deadline` | Abstract的截稿日期, 可选填                                                                                   |
| `timezone`\*        | 截稿日期的时区, 目前支持 `UTC-12` ~ `UTC+12` & `AoE`                                                        |
| `date`\*            | 会议举办的日期, 示例, Mar 12-16, 2021                                                                                     |
| `place`\*           | 会议举办的地点, 示例, `city, country`                                                                                    |
| `sub`\*             | 会议在CCF中被标注的类别, 可参考下面的辅助文档 |
| `rank`\*            | 会议在CCF中被标注的登记, 示例, `A`, `B`, `C`              |
| `dblp`\*            | 会议在dblp的URL的后缀, 示例, `iccv` in https://dblp.uni-trier.de/db/conf/iccv               |
| `note`              | 额外的一些辅助信息, 可选填                                                                                     |

带星标(*)的字段是必填项。

类别匹配表:

| `sub` | 类别名称 |
| ----------- | --------------------------------------------------------- |
| `DS`        | 计算机体系结构/并行与分布计算/存储系统                    |
| `NW`        | 计算机网络                                                |
| `SC`        | 网络与信息安全                                            |
| `SE`        | 软件工程/系统软件/程序设计语言                            |
| `DB`        | 数据库/数据挖掘/内容检索                                  |
| `CT`        | 计算机科学理论                                            |
| `CG`        | 计算机图形学与多媒体                                      |
| `AI`        | 人工智能                                                  |
| `HI`        | 人机交互与普适计算                                        |
| `MX`       | 交叉/综合/新兴                                            |

## 贡献
本项目由 [@jacklightChen](https://github.com/jacklightChen), [@0x4f5da2](https://github.com/0x4f5da2), [@kzoacn](https://github.com/kzoacn), [@cubercsl](https://github.com/cubercsl) 共同维护。

灵感来自于 [ai-deadlines](https://aideadlin.es/)。

## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fccfddl%2Fccf-deadlines.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fccfddl%2Fccf-deadlines?ref=badge_large)
