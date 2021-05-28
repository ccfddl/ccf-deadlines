# CCF-Deadlines
[![LICENSE](https://img.shields.io/github/license/ccfddl/ccf-deadlines)](https://github.com/ccfddl/ccf-deadlines/blob/main/LICENSE)
[![Build Status](https://img.shields.io/github/workflow/status/ccfddl/ccf-deadlines/Deploy)](https://github.com/ccfddl/ccf-deadlines/commits/main)
[![Open PRs](https://img.shields.io/github/issues-pr/ccfddl/ccf-deadlines)](https://github.com/ccfddl/ccf-deadlines/pulls)

English | [简体中文](./README.zh-CN.md)
Help researchers keep track of deadlines of conferences recommended by [China Computer Federation (CCF)](https://www.ccf.org.cn/).

Preview: [Demo](https://ccfddl.github.io/)

[![](.readme_assets/screenshot.png)]()

**No More Finding and Time Conversion on Your Own!**.

## Add/Update a conference
Contributions are welcomed and greatly appreciated! For further contribution and waterblowing, email [chenzh@stu.ecnu.edu.cn](chenzh@stu.ecnu.edu.cn) through your edu email address with wechatid to join the [CCFDDL](https://github.com/ccfddl) organization.

To add or update information:
- Fork the repo
- Add/Update the yml file of conference/conf_type/conf_name.yml
- Send a [pull request](https://github.com/ccfddl/ccf-deadlines/pulls)

Tips: check [conferences recommended](.readme_assets/ccf_recommended.pdf) and review [statistics](https://docs.qq.com/sheet/DR3F1Tm1jcnlzVFJ2)
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
  place: Xi'an, China
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
| `description`\*     | Description, or long name, better to add the session, e.g., The 15th XXX                                                                                           |
| `link`\*            | URL to the conference home page                                                                                       |
| `deadline`\*        | Deadline, in the format of `yyyy-mm-dd hh:mm:ss` or `TBD`                                                                     |
| `abstract_deadline` | Abstract deadline if applicable, optional                                                                                     |
| `timezone`\*        | Timezone of deadline, currently support `UTC-12` ~ `UTC+12` & `AoE`                                                        |
| `date`\*            | When the main conference is happening, e.g., Mar 12-16, 2021                                                                                     |
| `place`\*           | Where the main conference is happening, e.g., `city, country`                                                                                    |
| `sub`\*             | The category that the conference is labeled by CCF. See the matching table below |
| `rank`\*            | The level that the conference is ranked by CCF, e.g., `A`, `B`, `C`              |
| `dblp`\*            | The suffix in dblp url, e.g., `iccv` in https://dblp.uni-trier.de/db/conf/iccv               |
| `note`              | Some comments on the conference, optional                                                                                       |

Fields marked with asterisk (*) are required.

The matching table:

| `sub` | Category name |
| ----------- | --------------------------------------------------------- |
| `DS`        | Computer Architecture/Parallel Programming/Storage Technology                   |
| `NW`        | Network System                                              |
| `SC`        | Network and System Security                                           |
| `SE`        | Software Engineering/Operating System/Programming Language Design                            |
| `DB`        | Database/Data Mining/Information Retrieval                                  |
| `CT`        | Computing Theory                                    |
| `CG`        | Graphics                                      |
| `AI`        | Artificial Intelligence                                                  |
| `HI`        | Computer-Human Interaction                                       |
| `MX`       | Interdiscipline/Mixture/Emerging                                            |

## Contribution
Maintained by [@jacklightChen](https://github.com/jacklightChen), [@0x4f5da2](https://github.com/0x4f5da2), [@kzoacn](https://github.com/kzoacn), [@cubercsl](https://github.com/cubercsl).

Inspired by [ai-deadlines](https://aideadlin.es/).

## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fccfddl%2Fccf-deadlines.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fccfddl%2Fccf-deadlines?ref=badge_large)
