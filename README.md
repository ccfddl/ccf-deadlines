# CCF-Deadlines（添加CAAI目录版）

[原项目](https://github.com/ccfddl/ccf-deadline)

修改conference/XX文件夹下的yml文件，具体操作流程为：

1. 查看 https://www.caai.cn/index.php?s=/home/article/detail/id/4024.html 
   中国人工智能学会（CAAI）推荐国际学术会议图片上的分类（人工智能基础与综合类、人工交叉与应用类……）
2. 根据图片上每一个会议，找到对应 conference/XX/xxxx.yml 文件：
   - 在sub属性下面添加一个同级属性subCAAI，值为该会议**CAAI分类**的字母代号，字母代号在 conference/types_caai.yml 里有对应
   - 在rank属性下面添加一个子属性caai，值为该会议的**CAAI等级**（A类、B类、C类）
   - 若没有该会议的yml文件，则新建一个，搜索该会议的信息，格式仿照其他的

例如：AAAI在CAAI中被分为人工智能基础与综合类-A类会议，那么它的yml文件为


示例文件: conference/AI/CAAI.yml

```yaml
  - title: AAAI
    description: AAAI Conference on Artificial Intelligence
    sub: AI
    subCAAI: AIFC
    rank:
      ccf: A
      caai: A
      core: A*
      thcpl: A
    dblp: aaai
    confs:
      - year: 2022
        id: aaai22
        link: https://aaai.org/Conferences/AAAI-22/
        timeline:
          - abstract_deadline: '2021-08-30 23:59:59'
            deadline: '2021-09-08 23:59:59'
        timezone: UTC-12
        date: February 22 - March 1, 2022
        place: Vancouver, British Columbia, Canada
      - year: 2023
        id: aaai23
        link: https://www.aaai.org/Conferences/AAAI-23/
        timeline:
          - abstract_deadline: '2022-08-08 23:59:59'
            deadline: '2022-08-15 23:59:59'
        timezone: UTC-12
        date: February 7 - February 14, 2023
        place: Washington, DC, USA
      - year: 2024
        id: aaai24
        link: https://www.aaai.org/aaai-conference/
        timeline:
          - abstract_deadline: '2023-08-08 23:59:59'
            deadline: '2023-08-15 23:59:59'
        timezone: UTC-12
        date: February 20 - February 27, 2024
        place: Vancouver, British Columbia, Canada
      - year: 2025
        id: aaai25
        link: https://aaai.org/conference/aaai/aaai-25/
        timeline:
          - abstract_deadline: '2024-08-07 23:59:59'
            deadline: '2024-08-15 23:59:59'
        timezone: UTC-12
        date: February 25 - March 4, 2025
        place: PHILADELPHIA, PENNSYLVANIA, USA
```

字段描述:

<table>
   <tr>
      <th colspan="3">字段名</th>
      <th>描述</th>
   </tr>
   <tr>
      <td colspan="3"><code>title</code>*</td>
      <td>缩写的会议名称, 不需要年份, 大写</td>
   </tr>
   <tr>
      <td colspan="3"><code>description</code>*</td>
      <td>介绍, 或全称, 无需第几届</td>
   </tr>
   <tr>
      <td colspan="3"><code>sub</code>*</td>
      <td>会议在CCF中被标注的类别, 可参考下面的辅助文档</td>
   </tr>
    <tr>
      <td colspan="3"><code>subCAAI</code></td>
      <td>会议在CAAI中被标注的类别, 可参考下面的辅助文档</td>
   </tr>
   <tr>
      <td rowspan="4"><code>rank</code>*</td>
      <td colspan="2"><code>ccf</code>*</td>
      <td>会议在CCF中被标注的等级, 示例, <code>A</code>, <code>B</code>, <code>C</code>, <code>N</code></td>
   </tr>
    <tr>
        <td colspan="2"><code>caai</code></td>
      <td>会议在CAAI中被标注的等级, 示例, <code>A</code>, <code>B</code>, <code>C</code></td>
    </tr>
   <tr>
   <td colspan="2"><code>core</code></td>
   <td>会议在CORE中被标注的等级, 示例, <code>A*</code>,<code>A</code>, <code>B</code>, <code>C</code>, <code>N</code></td>
   </tr>
   <tr>
   <td colspan="2"><code>thcpl</code></td>
   <td>会议在TH-CPL中被标注的等级, 示例, <code>A</code>, <code>B</code>, <code>N</code></td>
   </tr>
   <tr>
      <td colspan="3"><code>dblp</code>*</td>
      <td>会议在dblp的URL的后缀, 示例, <code>iccv</code> in https://dblp.uni-trier.de/db/conf/iccv</td>
   </tr>
   <tr>
      <td rowspan="9"><code>confs</code></td>
      <td colspan="2"><code>year</code>*</td>
      <td>会议的年份</td>
   </tr>
   <tr>
      <td colspan="2"><code>id</code>*</td>
      <td>会议名字和年份, 小写</td>
   </tr>
   <tr>
      <td colspan="2"><code>link</code>*</td>
      <td>会议首页的URL</td>
   </tr>
   <tr>
      <td rowspan="3"><code>timeline</code>*</td>
      <td><code>abstract_deadline</code></td>
      <td>Abstract的截稿日期, 可选填</td>
   </tr>
   <tr>
      <td><code>deadline</code>*</td>
      <td>截稿日期, 格式为 <code>yyyy-mm-dd hh:mm:ss</code> or <code>TBD</code></td>
   </tr>
   <tr>
      <td><code>comment</code></td>
      <td>额外的一些辅助信息, 可选填</td>
   </tr>
   <tr>
      <td colspan="2"><code>timezone</code>*</td>
      <td>截稿日期的时区, 目前支持 <code>UTC-12</code> ~ <code>UTC+12</code> & <code>AoE</code></td>
   </tr>
   <tr>
      <td colspan="2"><code>date</code>*</td>
      <td>会议举办的日期, 示例, Mar 12-16, 2021</td>
   </tr>
   <tr>
      <td colspan="2"><code>place</code>*</td>
      <td>会议举办的地点, 示例, <code>city, country</code></td>
   </tr>
</table>

带星标(*)的字段是必填项。



CAAII类别匹配表:

| `sub`  | 类别名称                 |
| ------ | ------------------------ |
| `AIFC` | 人工智能基础与综合       |
| `AIA`  | 人工智能交叉与应用       |
| `BCI`  | 脑认知与类脑智能         |
| `ML`   | 机器学习                 |
| `PRCV` | 模式识别与计算机视觉     |
| `LSP`  | 语言与语音处理           |
| `KEDM` | 知识工程与数据挖掘       |
| `MII`  | 跨媒体智能与人机交互     |
| `IRS`  | 智能机器人与系统         |
| `ICCS` | 智能芯片与计算系统       |
| AIEG   | 人工智能伦理、安全与治理 |

