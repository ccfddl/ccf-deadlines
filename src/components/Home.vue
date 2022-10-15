<template>
  <section>
    <Header></Header>
    <el-checkbox style="padding-top: 10px;width: 33%" :indeterminate="isIndeterminate" v-model="checkAll" @change="handleCheckAllChange"><span style="color: #666666">全选</span></el-checkbox>
    <el-checkbox-group v-model="checkList" @change="handleCheckedChange">
      <el-checkbox class="boxes" size="medium" v-for="item in subList" :label="item.sub" :key="item.sub"><span style="color: #666666">{{formatSubName(item)}}</span></el-checkbox>
    </el-checkbox-group>
    <el-row class="timezone">
      <div style="float: left">
        Deadlines are shown in {{ timeZone }} time.
      </div>
      <div style="float: left; width: 155px">
        <el-input prefix-icon="el-icon-search" size="mini"
                  v-model="input" placeholder="search conference"
                  @change="handleInputChange"
                >
        </el-input>
      </div>
      <div style="float: right">
        <el-checkbox-group v-model="rankList" size="mini" @change="handleRankChange" class="rankbox">
          <el-checkbox-button v-for="(rank, index) in rankoptions" :label="index" :key="index">{{rank}}</el-checkbox-button>
        </el-checkbox-group>
      </div>
    </el-row>
    <el-row class="zonedivider"></el-row>
    <el-table
      :data="showList"
      :show-header="false"
      style="width: 100%">
      <el-table-column>
        <template slot-scope="scope">
          <div :class="{ 'conf-fin': scope.row.status === 'FIN' }">
            <el-row class="conf-title">
              <a :href="generateDBLP(scope.row.dblp)">{{scope.row.title}}</a> {{scope.row.year}}
              <i v-if="scope.row.isLike===true" class="el-icon-star-on" style="color: #FBCA04" @click="handleClickIcon(scope.row, true)"/>
              <i v-else class="el-icon-star-off" @click="handleClickIcon(scope.row, false)"/>
            </el-row>
            <el-row>{{scope.row.date+' '+scope.row.place}}</el-row>
            <el-row class="conf-des">{{scope.row.description}}</el-row>
            <el-row><el-tag size="mini" type="" effect="plain">{{scope.row.displayrank}}</el-tag> <span style="color: #409eff" v-show="scope.row.comment"><b>NOTE:</b> {{scope.row.comment}}</span></el-row>
            <el-row style="padding-top: 5px"><span class="conf-sub">{{scope.row.subname}}</span></el-row>
            </div>
        </template>
      </el-table-column>
      <el-table-column>
        <template slot-scope="scope">
          <div :class="{ 'conf-fin': scope.row.status === 'FIN' }">
            <el-row class="conf-timer">
              <div v-if="scope.row.status === 'TBD'" style="color: black">TBD</div>
              <countdown style="color: black" v-else :time="scope.row.remain" :transform="transform">
                <template slot-scope="props">{{ props.days }} {{ props.hours }} {{ props.minutes }} {{ props.seconds }}</template>
              </countdown>
              <el-popover
                  placement="right"
                  trigger="click">
                <el-row>
                  <img src="//ssl.gstatic.com/calendar/images/dynamiclogo_2020q4/calendar_3_2x.png#" srcset="//ssl.gstatic.com/calendar/images/dynamiclogo_2020q4/calendar_3_2x.png 2x ,//ssl.gstatic.com/calendar/images/dynamiclogo_2020q4/calendar_3_2x.png# 1x" alt="" aria-hidden="true" style="width:20px;height:20px;vertical-align: middle">
                  <span  style="padding-left: 5px">
                  <a v-if="scope.row.status === 'TBD'">Not Available</a>
                  <a v-else :href="formatGoogleCalendar(scope.row)"
                       target="_blank" rel="nofollow">Google Calendar</a>
                  </span>
                </el-row>
                <el-row>
                  <img src="https://help.apple.com/assets/61526E8E1494760B754BD308/61526E8F1494760B754BD30F/zh_CN/2162f7d3de310d2b3503c0bbebdc3d56.png" alt="" aria-hidden="true" style="width:20px;height:20px;vertical-align: middle">
                  <span  style="padding-left: 5px">
                  <a v-if="scope.row.status === 'TBD'">Not Available</a>
                  <a v-else :href="formatiCloudCalendar(scope.row)" rel="nofollow">iCloud Calendar</a>
                  </span>
                </el-row>
                <i class="el-icon-date icon" style="padding-left: 5px" slot="reference"></i>
              </el-popover>
            </el-row>
            <el-row>
              <div v-if="scope.row.status === 'TBD'">
                Deadline: <a href="https://github.com/ccfddl/ccf-deadlines/pulls">pull request to update</a>
              </div>
              <div v-else>
                Deadline: {{scope.row.localDDL}} ({{scope.row.originDDL}})
              </div>
            </el-row>
            <el-row>website: <a :href="scope.row.link">{{ scope.row.link }}</a> </el-row>
  <!--          <el-row>subscribe</el-row>-->
            <TimeLine v-if="scope.row.status === 'RUN'" :ddls="scope.row.ddls"></TimeLine>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <el-row style="padding-top: 8px">
      <div style="float: left; color: #666666;font-size: 12px;">
        <div>ccf-deadlines is maintained by <a href="https://github.com/jacklightChen">@jacklightChen</a> and <a href="https://github.com/0x4f5da2">@0x4f5da2</a>.</div>
        <div style="padding-top: 3px">If you find it useful, try find <a href="https://github.com/0x4f5da2">him</a> a girlfriend or follow <a href="https://www.researchgate.net/profile/Zhihao_Chen23">him</a> on ResearchGate.</div>
      </div>
      <div style="float: right">
        <el-pagination
            background
            small
            layout="prev, pager, next"
            :page-size=pageSize
            @current-change="handleCurrentChange"
            :current-page="page"
            :total=showNumber>
        </el-pagination>
      </div>
    </el-row>

  </section>
</template>

<script>
import Header from './Header'
import TimeLine from "./TimeLine";
const yaml = require('js-yaml')
const moment = require('moment-timezone')
const tz = moment.tz.guess()
export default {
  name: "Home",
  components: {
    Header,
    TimeLine
  },
  data() {
    return {
      publicPath: '/',
      checkAll: true,
      isIndeterminate: false,
      pageSize: 10,
      page: 1,
      checkList: [],
      subList: [],
      allconfList: [],
      showList: [],
      showNumber: 0,
      typeMap: new Map(),
      timeZone: '',
      utcMap: new Map(),
      rankoptions: {'A': 'CCF A', 'B': 'CCF B', 'C': 'CCF C', 'N': 'Non-CCF'},
      typesList: [],
      rankList: [],
      cachedLikes: [],
      cachedRanks: [],
      input: ''
    }
  },
  methods: {
    loadFile () {
      this.timeZone = tz
      this.$http.get(this.publicPath + 'conference/types.yml').then(response => {
        const doc = yaml.load(response.body)
        this.subList = doc
        for (let i = 0; i < this.subList.length; i++) {
          this.checkList.push(this.subList[i].sub)
          this.typesList.push(this.subList[i].sub)
          this.typeMap.set(this.subList[i].sub, this.subList[i].name)
        }
        this.loadCachedTypes()
        this.getAllConf()
      }, () => {
        alert('sorry your network is not stable!')
      })
    },
    getAllConf() {
      // get all conf
      this.$http.get(this.publicPath + 'conference/allconf.yml').then(response => {
        const allconf = yaml.load(response.body)
        // preprocess
        let doc = []
        let tmpTime = moment.tz(new Date(), tz)
        for (let i = 0; i < allconf.length; i++) {
          let curConf = allconf[i]
          for(let j = 0; j < curConf.confs.length; j++){
            let curItem = curConf.confs[j]
            curItem.title = curConf.title
            curItem.description = curConf.description
            curItem.sub = curConf.sub
            curItem.rank = curConf.rank
            curItem.displayrank = this.rankoptions[curItem.rank]
            curItem.dblp = curConf.dblp
            let len = curItem.timeline.length
            curItem.deadline = curItem.timeline[len-1].deadline
            curItem.abstract_deadline = curItem.timeline[len-1].abstract_deadline
            curItem.comment = curItem.timeline[len-1].comment
            curItem.ddls = []
            let flag = false;
            for(let k = 0; k < len; k++) {
              let ddlTime = moment(curItem.timeline[k].deadline + this.utcMap.get(curItem.timezone))
              let diffTime = ddlTime.diff(tmpTime)
              curItem.ddls.push(curItem.timeline[k].deadline + this.utcMap.get(curItem.timezone))
              if (!flag && diffTime >= 0) {
                curItem.deadline = curItem.timeline[k].deadline
                curItem.abstract_deadline = curItem.timeline[k].abstract_deadline
                curItem.comment = curItem.timeline[k].comment
                flag = true;
              }
            }
            doc.push(curItem)
          }
        }

        let curTime = moment.tz(new Date(), tz)
        for (let i = 0; i < doc.length; i++) {
          let curDoc = doc[i]
          curDoc.subname = this.typeMap.get(curDoc.sub)
          if (curDoc.deadline === 'TBD') {
            curDoc.remain = 0
            curDoc.status = 'TBD'
          } else {
            if (curDoc.timezone === 'AoE') {
              curDoc.timezone = 'UTC-12'
            } else if (curDoc.timezone === 'UTC') {
              curDoc.timezone = 'UTC+0'
            }

            let ddlTime = moment(curDoc.deadline + this.utcMap.get(curDoc.timezone))
            curDoc.localDDL = ddlTime.tz(this.timeZone).format('ddd MMM Do YYYY HH:mm:ss z')
            curDoc.originDDL = curDoc.deadline + ' ' + curDoc.timezone
            if(curDoc.abstract_deadline) {
              let absTime = moment(curDoc.abstract_deadline + this.utcMap.get(curDoc.timezone))
              if(!curDoc.comment) {
                curDoc.comment = 'abstract deadline on ' + absTime.tz(this.timeZone).format('MMM D, YYYY')+'.'
              }
            }
            // alert(ddlTime.tz(this.timeZone).format('ddd MMM Do YYYY HH:mm:ss z'))
            let diffTime = ddlTime.diff(curTime)
            if (diffTime <= 0) {
              curDoc.remain = 0
              curDoc.status = 'FIN'
            } else {
              curDoc.remain = diffTime
              curDoc.status = 'RUN'
            }
            // check cachedLikes
            if(this.cachedLikes&&this.cachedLikes.indexOf(curDoc.title + curDoc.id) >= 0) {
              curDoc.isLike = true
            }else {
              curDoc.isLike = false
            }
          }
          this.allconfList.push(curDoc)
        }
        this.showConf(this.typesList, this.rankList, this.input, 1)
      }, () => {
        alert('sorry your network is not stable!')
      })
    },
    showConf (types, rank, input, page) {
      let filterList = this.allconfList

      if (types != null && types.length != 0){
        filterList = filterList.filter(function (item){return types.indexOf(item.sub.toUpperCase()) >= 0})
      }

      if (rank != null && rank.length > 0){
        filterList = filterList.filter(function (item){return rank.indexOf(item.rank) >= 0})
      }

      if (input != null && input.length > 0){
        filterList = filterList.filter(function (item){return item.id.toLowerCase().indexOf(input.toLowerCase()) >= 0})
      }

      let runList = filterList.filter(function (item){ return item.status === 'RUN'})
      let tbdList = filterList.filter(function (item){ return item.status === 'TBD'})
      let finList = filterList.filter(function (item){ return item.status === 'FIN'})

      runList.sort((a, b) => (b.remain === a.remain ? 0 : a.remain < b.remain ? -1 : 1))
      finList.sort((a, b) => (b.year === a.year ? 0 : a.year > b.year ? -1 : 1))

      this.showList = []
      let allList = []
      let likesList = []
      allList.push.apply(allList, runList)
      allList.push.apply(allList, tbdList)
      allList.push.apply(allList, finList)

      for(let i=allList.length-1;i>=0;i--){
        let curDoc = allList[i]
        if(curDoc.isLike===true){
          likesList.push(curDoc)
          allList.splice(i,1)
        }
      }
      likesList.reverse()
      likesList.push.apply(likesList, allList)
      this.showList = likesList
      this.showNumber = this.showList.length
      this.showList = this.showList.slice(this.pageSize*(page-1), this.pageSize*page)
      this.page = page
    },
    transform (props) {
      Object.entries(props).forEach(([key, value]) => {
        // Adds leading zero
        const digits = value < 10 ? `0${value}` : value
        // uses singular form when the value is less than 2
        const word = value < 2 ? key.replace(/s$/, '') : key
        if (word[0] === 'd') {
          props[key] = `${digits} ${word}`
        } else {
          props[key] = `${digits} ${word[0]}`
        }
      })
      return props
    },
    loadUTCMap () {
      for (let i = -12; i <= 12; i++) {
        if (i >= 0) {
          this.utcMap.set('UTC+' + i, '+' + (Array(2).join(0) + i).slice(-2) + '00')
        } else {
          this.utcMap.set('UTC' + i, '-' + (Array(2).join(0) + i * -1).slice(-2) + '00')
        }
      }
      this.utcMap.set('AoE', '-1200')
      this.utcMap.set('UTC', '+0000')
    },
    handleCheckedChange(types) {
      this.typesList = types
      let checkedCount = types.length
      this.checkAll = checkedCount === this.subList.length
      this.isIndeterminate = checkedCount > 0 && checkedCount < this.subList.length
      this.$ls.set('types', Array.from(this.typesList))
      this.showConf(this.typesList, this.rankList, this.input, 1)
    },
    handleInputChange(){
      this.showConf(this.typesList, this.rankList, this.input,1)
    },
    handleRankChange(rank) {
      this.rankList = rank
      this.$ls.set('ranks', Array.from(this.rankList))
      this.showConf(this.typesList, this.rankList, this.input,1)
    },
    handleCurrentChange(page) {
      this.showConf(this.typesList, this.rankList, this.input, page)
    },
    handleCheckAllChange() {
      this.typesList = (this.checkList.length === this.subList.length) ? [] : this.subList.map((obj) => {return obj.sub}).join(",").split(',');
      this.checkList = this.typesList
      this.isIndeterminate = false
      this.$ls.set('types', Array.from(this.typesList))
      this.showConf(this.typesList, this.rankList, this.input,1)
    },
    handleClickIcon(record, judge) {
      if(judge === true) {
        record.isLike = false
        let index = this.cachedLikes.indexOf(record.title + record.id)
        if(index > -1) this.cachedLikes.splice(index,1)
        this.$ls.set('likes', Array.from(new Set(this.cachedLikes)))
      }else {
        record.isLike = true
        this.cachedLikes.push(record.title + record.id)
        this.$ls.set('likes', Array.from(new Set(this.cachedLikes)))
      }
    },
    generateDBLP(name){
      return 'https://dblp.uni-trier.de/db/conf/' + name
    },
    formatGoogleCalendar(row){
      return "https://www.google.com/calendar/render?action=TEMPLATE" +
          "&text="+row.title+"+"+row.year+
          "&dates="+moment(row.deadline + this.utcMap.get(row.timezone)).toISOString().replace(/-|:|\.\d\d\d/g,"")+"/"+ moment(row.deadline + this.utcMap.get(row.timezone)).toISOString().replace(/-|:|\.\d\d\d/g,"") +
          "&details=" + row.comment +
          "&location=Online" +
          "&ctz=" + this.timeZone +
          "&sf=true&output=xml"
    },
    formatiCloudCalendar(row){
      return "data:text/calendar;charset=utf8,BEGIN:VCALENDAR%0AVERSION:2.0%0ABEGIN:VEVENT%0A" +
          "URL:https://ccfddl.github.io/%0A" +
          "DTSTART:" + moment(row.deadline + this.utcMap.get(row.timezone)).toISOString().replace(/-|:|\.\d\d\d/g,"") + "%0A" +
          "DTEND:" + moment(row.deadline + this.utcMap.get(row.timezone)).toISOString().replace(/-|:|\.\d\d\d/g,"") + "%0A" +
          "SUMMARY:" + row.title + " " + row.year + " Deadline %0A" +
          "DESCRIPTION:" + row.comment + "%0A" +
          "LOCATION:%0A" +
          "END:VEVENT%0AEND:VCALENDAR"
      // return "https://www.google.com/calendar/render?action=TEMPLATE" +
      //     "&text="+row.title+"+"+row.year+
      //     "&dates="+moment(row.deadline + this.utcMap.get(row.timezone)).toISOString().replace(/-|:|\.\d\d\d/g,"")+"/"+ moment(row.deadline + this.utcMap.get(row.timezone)).toISOString().replace(/-|:|\.\d\d\d/g,"") +
      //     "&details=" + row.comment +
      //     "&location=Online" +
      //     "&ctz=" + this.timeZone +
      //     "&sf=true&output=xml"
    },
    _isMobile() {
      let flag = navigator.userAgent.match(/(phone|pad|pod|iPhone|iPod|ios|iPad|Android|Mobile|BlackBerry|IEMobile|MQQBrowser|JUC|Fennec|wOSBrowser|BrowserNG|WebOS|Symbian|Windows Phone)/i)
      return flag;
    },
    formatSubName(item){
      if(this._isMobile()) {
        return item.sub
      }else {
        return item.name
      }
    },
    loadCachedTypes() {
      let tmpList = this.$ls.get('types')
      if(tmpList) {
        this.typesList = tmpList
        this.checkList = this.typesList
        let checkedCount = this.checkList.length
        this.checkAll = checkedCount === this.subList.length
        this.isIndeterminate = checkedCount > 0 && checkedCount < this.subList.length
      }
    },
    loadCachedLikes() {
      this.cachedLikes = this.$ls.get('likes')
      if(!this.cachedLikes) this.cachedLikes = []
    },
    loadCachedRanks() {
      this.cachedRanks = this.$ls.get('ranks')
      if(!this.cachedRanks) this.cachedRanks = []
      this.rankList = this.cachedRanks
    },
  },
  mounted () {
    // this.loadCachedTypes()
    this.loadCachedRanks()
    this.loadCachedLikes()
    this.loadUTCMap()
    this.loadFile()
  }
}
</script>

<style scoped>
/*/deep/ .el-table tbody tr { pointer-events:; }*/
/deep/ .el-input--mini .el-input__inner {
  height: 20px;
  line-height: 20px;
}

/deep/ .el-input--mini .el-input__icon {
  line-height: 20px;
}

/deep/ .el-checkbox__inner {
  height: 20px;
  width: 20px;
}

/deep/ .el-button {
  height: 20px;
  padding: 0px 5px;
}

/deep/ .el-checkbox-button--mini .el-checkbox-button__inner {
  padding: 3px 10px;
}

/deep/ .el-checkbox__inner::after {
  -webkit-box-sizing: content-box;
  box-sizing: content-box;
  content: "";
  border: 3px solid #FFF;
  border-left: 0;
  border-top: 0;
  height: 11px;
  left: 6px;
  position: absolute;
  top: 1px;
  -webkit-transform: rotate(45deg) scaleY(0);
  transform: rotate(45deg) scaleY(0);
  width: 4px;
  -webkit-transition: -webkit-transform .15s ease-in .05s;
  transition: -webkit-transform .15s ease-in .05s;
  transition: transform .15s ease-in .05s,-webkit-transform .15s ease-in .05s;
  -webkit-transform-origin: center;
  transform-origin: center;
}

/deep/ .el-checkbox__input.is-indeterminate .el-checkbox__inner::before {
  height: 6px;
  top: 6px;
}

.icon:hover{
  color:rgb(64, 158, 255);
}

.rankbox {
  padding-top: 1px;
}

.boxes{
  width: 33%;
  margin-right: 0px;
  padding-top: 10px;
}

.timezone{
  padding-top: 15px;
  color: #666666;
}

.zonedivider{
  margin-top: 8px;
  border-bottom: 1px solid #ebeef5;
}

.conf-title {
  font-size: 20px;
  font-weight: 400;
  color: black;
}

a{
  text-decoration: none;
  border-bottom: 1px solid #ccc;
  color: inherit;
}

.conf-des {
  font-size: 13px;
}

.conf-sub {
  color: rgb(36, 101, 191);
  background: rgba(236, 240, 241, 0.7);
  font-size: 13px;
  padding: 3px 5px;
  cursor: pointer;
  font-weight: 400;
}

.conf-timer {
  font-size: 20px;
  font-weight: 400;
}

.conf-fin{
  opacity: 0.4;
}
</style>
