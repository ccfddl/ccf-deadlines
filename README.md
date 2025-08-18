# CCF-Deadlines

> Helping researchers track worldwide conference ddls through collaboration.

[![LICENSE](https://img.shields.io/github/license/ccfddl/ccf-deadlines)](https://github.com/ccfddl/ccf-deadlines/blob/main/LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/ccfddl/ccf-deadlines/.github/workflows/deploy.yml?branch=main)](https://github.com/ccfddl/ccf-deadlines/commits/main)
[![Open PRs](https://img.shields.io/github/issues-pr/ccfddl/ccf-deadlines)](https://github.com/ccfddl/ccf-deadlines/pulls)

English | [简体中文](https://translate.google.com/translate?sl=auto&tl=zh&u=https://github.com/ccfddl/ccf-deadlines)

<table>
  <tr>
    <td align="center"><b><a href="https://ccfddl.github.io/">🌐 Website Portal<br></a>Main Site</b></td>
    <td align="center"><b><a href="https://github.com/ccfddl/ccf-deadlines/tree/main/.readme_assets/applet_qrcode.jpg">📱 Wechat Applet</a><br>Available Now</b></td>
    <td align="center"><b><a href="https://ccfddl.top/">🌐 Tabular Portal</a><br>No Ladder Required</b></td>
  </tr>
  <tr>
    <td align="center"><img src=".readme_assets/screenshot_website.png" width="280px"/></td>
    <td align="center"><img src=".readme_assets/applet_qrcode.jpg" width="240px"/></td>
    <td align="center"><img src=".readme_assets/screenshot_tabular.png" width="280px"/></td>
  </tr>
</table>

**No More Finding and Time Conversion on Your Own!**

### Add-Ons
<table>
  <tr>
    <td align="center"><b><a href="https://github.com/ccfddl/ccf-deadlines/tree/main/add_ons/cli">PyCli Tool</a><br></b></td>
    <td align="center"><b><a href="https://www.raycast.com/ViGeng/ccfddl?via=ViGeng">Raycast Extension</a><br></b></td>
    <td align="center"><b><a href="https://github.com/superpung/swiftbar-ccfddl/">SwiftBar Plugin</a><br></b></td>
  </tr>
  <tr>
   <td align="center"><img src=".readme_assets/screenshot_pycli.png" width="280px"/></td>
    <td align="center"><img src=".readme_assets/screenshot_raycast.png" width="280px"/></td>
    <td align="center"><img src="https://raw.githubusercontent.com/superpung/swiftbar-ccfddl/refs/heads/main/docs/preview.png" width="280px"/></td>
  </tr>
    <tr>
    <td align="center"><b><a href="https://github.com/ccfddl/ccf-deadlines/tree/main/add_ons/ical">iCal Subscription</a><br></b></td>
  </tr>
  <tr>
     <td align="center"><img src=".readme_assets/screenshot_iCal.jpg" width="280px"/></td>
  </tr>
</table>

## Community Activity
![Alt](https://repobeats.axiom.co/api/embed/98d0169b30fc63bfddcfbf2ac6d73656ef0f9d00.svg "Repobeats analytics image")

## Add/Update a conference

Contributions are welcomed and greatly appreciated!

To add or update information:

- Fork the repo
- Add/Update the yml file of conference/conf_type/conf_name.yml
- Send a [pull request](https://github.com/ccfddl/ccf-deadlines/pulls)

Tips: check [conferences recommended](https://www.ccf.org.cn/Academic_Evaluation/By_category/) or review [pdf](.readme_assets/ccf_recommended_2022.pdf)
## Conference Entry File
Example file: conference/DB/sigmod.yml

```yaml
- title: SIGMOD
  description: ACM Conference on Management of Data
  sub: DB
  rank:
    ccf: A
    core: A*
    thcpl: A
  dblp: sigmod
  confs:
    - year: 2022
      id: sigmod22
      link: http://2022.sigmod.org/
      timeline:
        - deadline: '2021-07-02 17:00:00'
          comment: 'first round'
        - deadline: '2021-09-15 17:00:00'
          comment: 'second round'
      timezone: UTC-8
      date: June 12-17, 2022
      place: Philadelphia, PA, USA
```

Description of the fields:
<table>
   <tr>
      <th colspan="3">Field name</th>
      <th>Description</th>
   </tr>
   <tr>
      <td colspan="3"><code>title</code>*</td>
      <td>Short conference name, without year, uppercase</td>
   </tr>
   <tr>
      <td colspan="3"><code>description</code>*</td>
      <td>Description, or long name, with no session</td>
   </tr>
   <tr>
      <td colspan="3"><code>sub</code>*</td>
      <td>The category that the conference is labeled by CCF. See the matching table below</td>
   </tr>
   <tr>
      <td rowspan="3"><code>rank</code>*</td>
      <td colspan="2"><code>ccf</code>*</td>
      <td>The level that the conference is ranked by CCF, e.g., <code>A</code>, <code>B</code>, <code>C</code>, <code>N</code></td>
   </tr>
   <tr>
   <td colspan="2"><code>core</code></td>
   <td>The level that the conference is ranked by CORE, e.g., <code>A*</code>, <code>A</code>, <code>B</code>, <code>C</code>, <code>N</code></td>
   </tr>
   <tr>
   <td colspan="2"><code>thcpl</code></td>
   <td>The level that the conference is ranked by TH-CPL, e.g., <code>A</code>, <code>B</code>, <code>N</code></td>
   </tr>
   <tr>
      <td colspan="3"><code>dblp</code>*</td>
      <td>The suffix in dblp url, e.g., <code>iccv</code> in https://dblp.uni-trier.de/db/conf/iccv</td>
   </tr>
   <tr>
      <td rowspan="9"><code>confs</code></td>
      <td colspan="2"><code>year</code>*</td>
      <td>Year the conference is happening</td>
   </tr>
   <tr>
      <td colspan="2"><code>id</code>*</td>
      <td>conference name & year, lowercase</td>
   </tr>
   <tr>
      <td colspan="2"><code>link</code>*</td>
      <td>URL to the conference home page</td>
   </tr>
   <tr>
      <td rowspan="3"><code>timeline</code>*</td>
      <td><code>abstract_deadline</code></td>
      <td>Abstract deadline if applicable, optional</td>
   </tr>
   <tr>
      <td><code>deadline</code>*</td>
      <td>Deadline, in the format of <code>yyyy-mm-dd hh:mm:ss</code> or <code>TBD</code></td>
   </tr>
   <tr>
      <td><code>comment</code></td>
      <td>Some comments on the conference, optional</td>
   </tr>
   <tr>
      <td colspan="2"><code>timezone</code>*</td>
      <td>Timezone of deadline, currently support <code>UTC-12</code> ~ <code>UTC+12</code> & <code>AoE</code></td>
   </tr>
   <tr>
      <td colspan="2"><code>date</code>*</td>
      <td>When the main conference is happening, e.g., Mar 12-16, 2021</td>
   </tr>
   <tr>
      <td colspan="2"><code>place</code>*</td>
      <td>Where the main conference is happening, e.g., <code>city, country</code></td>
   </tr>
</table>

Fields marked with asterisk (*) are required.

The matching table:

| `sub` | Category name                                                     |
| ----- | ----------------------------------------------------------------- |
| `DS`  | Computer Architecture/Parallel Programming/Storage Technology     |
| `NW`  | Network System                                                    |
| `SC`  | Network and System Security                                       |
| `SE`  | Software Engineering/Operating System/Programming Language Design |
| `DB`  | Database/Data Mining/Information Retrieval                        |
| `CT`  | Computing Theory                                                  |
| `CG`  | Graphics                                                          |
| `AI`  | Artificial Intelligence                                           |
| `HI`  | Computer-Human Interaction                                        |
| `MX`  | Interdiscipline/Mixture/Emerging                                  |

## Contribution

Maintained by [@ccfddl](https://github.com/ccfddl) collaboration.

## License

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fccfddl%2Fccf-deadlines.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fccfddl%2Fccf-deadlines?ref=badge_large)
