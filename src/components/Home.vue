<template>
  <section>
    <Header></Header>
    <el-checkbox-group style="padding-top: 10px" v-model="checkList" @change="handleCheckedChange">
      <el-checkbox class="boxes" size="medium" v-for="item in subList" :label="item.sub" :key="item.sub">{{formatSubName(item)}}</el-checkbox>
    </el-checkbox-group>
    <el-row class="timezone">
      <div style="float: left">
        Deadlines are shown in {{ timeZone }} time.
      </div>
      <div style="float: right">
        <el-checkbox-group v-model="rankGroup" size="mini" @change="handleRankChange">
          <el-checkbox-button v-for="rank in rankoptions" :label="rank" :key="rank">CCF {{rank}}</el-checkbox-button>
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
            <el-row class="conf-title"><a :href="generateDBLP(scope.row.dblp)">{{scope.row.title}}</a> {{scope.row.year}}</el-row>
            <el-row>{{scope.row.date+' '+scope.row.place}}</el-row>
            <el-row class="conf-des">{{scope.row.description}}</el-row>
            <el-row><el-tag size="mini" type="" effect="plain">CCF {{scope.row.rank}}</el-tag> <span style="color: #409eff" v-show="scope.row.note"><b>NOTE:</b> {{scope.row.note}}</span></el-row>
            <el-row><span class="conf-sub">{{scope.row.subname}}</span></el-row>
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
          </div>
        </template>
      </el-table-column>
    </el-table>
    <el-row style="padding-top: 8px">
      <div style="float: left; color: #666666;font-size: 12px;">
        <div>ccf-deadlines is maintained by <a href="https://github.com/jacklightChen">@jacklightChen</a> and <a href="https://github.com/0x4f5da2">@0x4f5da2</a>.</div>
        <div style="padding-top: 3px">If you find it useful, try find <a href="https://github.com/0x4f5da2">him</a> a girlfriend.</div>
      </div>
      <div style="float: right">
        <el-pagination
            background
            small
            layout="prev, pager, next"
            :page-size="5"
            @current-change="handleCurrentChange"
            :total=allconfList.length>
        </el-pagination>
      </div>
    </el-row>

  </section>
</template>

<script>
import Header from './Header'
const yaml = require('js-yaml')
const moment = require('moment-timezone')
const tz = moment.tz.guess()
export default {
  name: "Home",
  components: {
    Header
  },
  data() {
    return {
      publicPath: '/',
      pageSize: 5,
      checkList: [],
      subList: [],
      allconfList: [],
      showList: [],
      typeMap: new Map(),
      timeZone: '',
      utcMap: new Map(),
      rankoptions: ['A', 'B', 'C'],
      rankGroup: ['A', 'B', 'C'],
      typesList: [],
      rankList: ['A','B','C']
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
        this.getAllConf()
      }, () => {
        alert('sorry your network is not stable!')
      })
    },
    getAllConf() {
      // get all conf
      this.$http.get(this.publicPath + 'conference/allconf.yml').then(response => {
        const doc = yaml.load(response.body)
        let curTime = moment.tz(new Date(), tz)
        for (let i = 0; i < doc.length; i++) {
          doc[i].subname = this.typeMap.get(doc[i].sub)
          if (doc[i].deadline === 'TBD') {
            doc[i].remain = 0
            doc[i].status = 'TBD'
          } else {
            if (doc[i].timezone === 'AoE') {
              doc[i].timezone = 'UTC-12'
            }

            let ddlTime = moment(doc[i].deadline + this.utcMap.get(doc[i].timezone))
            doc[i].localDDL = ddlTime.tz(this.timeZone).format('ddd MMM Do YYYY HH:mm:ss z')
            doc[i].originDDL = doc[i].deadline + ' ' + doc[i].timezone
            // alert(ddlTime.tz(this.timeZone).format('ddd MMM Do YYYY HH:mm:ss z'))
            let diffTime = ddlTime.diff(curTime)
            if (diffTime <= 0) {
              doc[i].remain = 0
              doc[i].status = 'FIN'
            } else {
              doc[i].remain = diffTime
              doc[i].status = 'RUN'
            }
          }
          this.allconfList.push(doc[i])
        }
        this.showConf(null, null, 1)
      }, () => {
        alert('sorry your network is not stable!')
      })
    },
    showConf (types, rank, page) {
      let filterList = this.allconfList

      if (types != null){
        filterList = filterList.filter(function (item){return types.indexOf(item.sub.toUpperCase()) >= 0})
      }

      if (rank != null){
        filterList = filterList.filter(function (item){return rank.indexOf(item.rank) >= 0})
      }

      let runList = filterList.filter(function (item){ return item.status === 'RUN'})
      let tbdList = filterList.filter(function (item){ return item.status === 'TBD'})
      let finList = filterList.filter(function (item){ return item.status === 'FIN'})

      runList.sort((a, b) => (b.remain === a.remain ? 0 : a.remain < b.remain ? -1 : 1))
      finList.sort((a, b) => (b.year === a.year ? 0 : a.year > b.year ? -1 : 1))

      this.showList = []
      this.showList.push.apply(this.showList, runList);
      this.showList.push.apply(this.showList, tbdList);
      this.showList.push.apply(this.showList, finList);
      this.showList = this.showList.slice(this.pageSize*(page-1), this.pageSize*page)
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
    },
    handleCheckedChange(types) {
      this.typesList = types
      this.showConf(this.typesList, this.rankList, 1)
    },
    handleRankChange(rank) {
      this.rankList = rank
      this.showConf(this.typesList, this.rankList, 1)
    },
    handleCurrentChange(page) {
      console.log(page)
      this.showConf(this.typesList, this.rankList, page)
    },
    generateDBLP(name){
      return 'https://dblp.uni-trier.de/db/conf/' + name
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
    }
  },
  mounted () {
    this.loadUTCMap()
    this.loadFile()
  }
}
</script>

<style scoped>
/*/deep/ .el-table tbody tr { pointer-events:; }*/
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