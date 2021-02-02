# CCF-Deadlines
[![LICENSE](https://img.shields.io/github/license/ccfddl/ccf-deadlines)](https://github.com/ccfddl/ccf-deadlines/blob/main/LICENSE)
[![Build Status](https://img.shields.io/github/workflow/status/ccfddl/ccf-deadlines/Deploy)](https://github.com/ccfddl/ccf-deadlines/commits/main)
[![Open PRs](https://img.shields.io/github/issues-pr/ccfddl/ccf-deadlines)](https://github.com/ccfddl/ccf-deadlines/pulls)

Help researchers keep track of deadlines of conferences recommended by [China Computer Federation (CCF)](https://www.ccf.org.cn/).

Preview: [CCF-Deadlines](https://ccfddl.github.io/) **(No More Time Zone Conversion on Your Own!)**.

Maintained by [@jacklightChen](https://github.com/jacklightChen) and [@0x4f5da2](https://github.com/0x4f5da2).

Inspired by [ai-deadlines](https://aideadlin.es/?sub=ML,RO,CV).
## Add/Update a conference
Contributions are welcomed and greatly appreciated! For further contribution and waterblowing, email [chenzh@stu.ecnu.edu.cn](chenzh@stu.ecnu.edu.cn) through your edu email address with wechatid to join the [CCFDDL](https://github.com/ccfddl) organization.

To add or update information:
- Fork the repo
- Add/Update the yml file of conference/conf_type/conf_name.yml
- Send a [pull request](https://github.com/ccfddl/ccf-deadlines/pulls)

## Conference Entry File
Example file: conference/DB/sigmod.yml

```
- title: SIGMOD
  year: 2021
  id: sigmod21
  description: ACM Conference on Management of Data
  link: http://2021.sigmod.org/
  deadline: '2020-09-22 17:00:00'
  timezone: UTC-8
  date: Jun 20-25, 2021
  place: Xi'an, Shaanxi, China
  sub: DB
  rank: A
  dblp: sigmod
```
Description of the fields:

| Field name          | Description                                                                                                           |
| ------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `title`\*           | Short conference name, without year, uppercase                                                                                 |
| `year`\*            | Year the conference is happening                                                                                      |
| `id`\*              | conference name & year, lowercase                                                                                          |
| `description`\*     | Description, or long name                                                                                             |
| `link`\*            | URL to the conference home page                                                                                       |
| `deadline`\*        | Deadline, in the format of `yyyy-mm-dd hh:mm:ss`                                                                      |
| `abstract_deadline` | Abstract deadline if applicable, optional                                                                                     |
| `timezone`\*        | Timezone of deadline, currently support `UTC-12` ~ `UTC+12` & `AoE`                                                        |
| `date`\*            | When the main conference is happening                                                                                      |
| `place`\*           | Where the main conference is happening                                                                                     |
| `sub`\*             | The category that the conference is labeled by CCF. See the matching table below |
| `rank`\*            | The level that the conference is ranked by CCF, i.e., `A`, `B`, `C`              |
| `dblp`\*            | The suffix in dblp url, i.e., https://dblp.uni-trier.de/db/conf/`dblp`               |
| `note`              | Some comments on the conference, optional                                                                                       |

Fields marked with asterisk (*) are required.

The matching table:

| `sub` | Category name |
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

## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fccfddl%2Fccf-deadlines.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fccfddl%2Fccf-deadlines?ref=badge_large)