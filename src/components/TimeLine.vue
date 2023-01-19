<template>
  <div class="time_con">
      <div class="line_time">
        <div class="all_line">
          <!-- <div class="all_line"> -->
          <div class="line" ref="allLineTime">
            <!-- 可以滑动的线 -->
            <div class="can_line" ref="canLine"></div>
            <!-- 参考点 -->
            <div class="reference" v-for="(dateTip,dt) in dateTips" :key="'tips-'+dt" :style="setLeft(dateTip['timepoint'])">
              <em v-if="!((dt===0&&isSingle)||(_isMobile()&&dateTips.length>6&&(dt%3===1||dt%3===2)))" v-text="formatter(dateTip['timepoint'],1, dt)" ></em>
            </div>
            <!-- 备份点 -->
            <div :class="formatClass(incre['type'])" v-for="(incre,i) in incre_dates" :key="i" :style="setLeft(incre['timepoint'],i)">
              <em v-text="formatType(incre['type']) + ' ' +formatter(incre['timepoint'])" :style="setText(i)"></em>
            </div>
            <!-- 可滑动点 -->
            <div class="dot sel_dot" ref="selDot">
                <em>Now: {{selTime}}</em>
            </div>
          </div>
        </div>
      </div>
    </div>
</template>

<script>
const moment = require('moment-timezone')
const tz = moment.tz.guess()
export default {
  name: "TimeLine",
  props: ['ddls'],
  data() {
    return {
      fullDate: null,//最初时间（最开始有数据的时候）
      binlogDate: null,//binlog 结束时间
      selTime: null,//选中时间
      start_date: null,//开始时间戳
      end_date: null,//结束时间戳
      timeline: null,//选中时间戳
      incre_dates: [],//备份点数组
      allIncre: [],//备份点和binlog
      dateTips: [],//0点，提示时间点数组
      deadlines: [],
      isSingle: false,
      expireIndex: -1
    };
  },
  created(){

  },
  mounted() {
    this.$nextTick(()=>{
      this.getBackupTimeline();
    })
  },
  methods: {
    _isMobile() {
      let flag = navigator.userAgent.match(/(phone|pad|pod|iPhone|iPod|ios|iPad|Android|Mobile|BlackBerry|IEMobile|MQQBrowser|JUC|Fennec|wOSBrowser|BrowserNG|WebOS|Symbian|Windows Phone)/i)
      return flag;
    },
    //时间显示格式
    formatter(value,day,index) {
      if(day) {
        if(this.ddls.length>1&&index>0){
          let cur = this.dateTips[index]
          let pre = this.dateTips[index-1]
          if((cur-this.start_date)/(this.end_date-this.start_date)*100-
              (pre-this.start_date)/(this.end_date-this.start_date)*100
              <8) return ``;
        }
        return `${moment(value*1000).format('MM/DD')}`;
      }
      return `${moment(value*1000).format('YYYY/MM/DD HH:mm:ss')}`;
    },
    formatType(type) {
      if(type === 0){
        return 'Registration:'
      }else if(type === 1) {
        return 'Submission:'
      }else {
        return ''
      }
    },
    formatClass(type){
      if(type === 0){
        return 'square square_all'
      }else if(type === 1) {
        return 'dot dot_all'
      }else {
        return ''
      }
    },
    //获取时间轴数据
    getBackupTimeline(){
      this.fullDate = null
      this.binlogDate =  null
      this.selTime = null
      this.start_date = null
      this.end_date = null
      this.timeline = null
      this.deadlines = []
      this.incre_dates = []
      this.allIncre = []
      this.dateTips = []
      this.isSingle = false
      this.expireIndex = -1

      let nowDate = moment.tz(new Date(), tz).valueOf()

      let orilen = this.ddls.length
      if(orilen===1){
        this.deadlines.push({'timepoint': nowDate/1000, 'type': 1})
        this.isSingle = true
      }
      for(let i=0;i<orilen;i++){
        let tmp = {'timepoint': moment(this.ddls[i]['timepoint']).valueOf()/1000, 'type': this.ddls[i]['type']}
        this.deadlines.push(tmp)
      }

      let len = this.deadlines.length
      for(let i=0;i<len;i++) {
        let tmp = this.deadlines[i]['timepoint']
        if(nowDate>=tmp*1000){
          this.expireIndex = i
        }else {
          break
        }
      }

      if(nowDate<this.deadlines[0]['timepoint']*1000){
        this.start_date = moment(nowDate).subtract(7, 'd').startOf('day').format("X")*1;
      }else{
        this.start_date = moment(this.deadlines[0]['timepoint']*1000).subtract(7, 'd').startOf('day').format("X")*1;
      }
      this.end_date = moment(this.deadlines[len-1]['timepoint']*1000).add(7,'d').endOf('day').format("X")*1;


      this.fullDate = nowDate/1000;
      this.binlogDate = this.deadlines[len-1]['timepoint'];

      //设置binlog
      let canLine = this.$refs.canLine;
      let binlogStart=nowDate/1000;//binlog开始时间
      let binlogNum = (this.binlogDate-binlogStart)/(this.end_date-this.start_date);//binlog占时间轴百分比
      if(binlogNum>0){//如果选择的时间有binlog
        canLine.style.width = binlogNum*100 + '%' ;
        canLine.style.left = (binlogStart-this.start_date)/(this.end_date-this.start_date)*100 + '%';
        canLine.style.maxWidth =100-parseFloat(canLine.style.left) + '%' ;
      }else{
        canLine.style.width = 0 + '%' ;
        // if(dats.incre_dates.length<=0){
        //   this.$message.warning('所选时间区间没有可选择时间点，请修改时间区间~');
        //   this.showLine = false;
        //   this.timeline = null;
        //   this.$parent.showLine = true;
        // }
      }

      //设置备份时间点数组
      let dates = this.deadlines
      this.incre_dates = dates;
      this.allIncre = dates.concat([
        {'timepoint': this.binlogDate, 'type': 1},
        {'timepoint': this.fullDate, 'type': 1}
      ]);//备份时间点加上binlog结束时间点和fullDate

      this.clickDot(this.fullDate);//设置默认选择点

      this.timeline = dates[dates.length-1]['timepoint'];

      //添加提示时间点---0点提示
      this.dateTips=[];
      // let days = Math.abs(this.$moment(this.endValue).endOf('day').diff(this.$moment(this.startValue).startOf('day'), 'days'));
      for(let i=0;i<this.deadlines.length;i++){
        this.dateTips.push(this.deadlines[i])
      }
      // for(let i=0;i<=days;i++){
      //   this.dateTips.push(this.$moment(this.startValue).add(i, 'd').startOf('day').format('X'));
      // }
      // }

      // });
    },
    //点击时间轴---计算百分比
    lineMouseDown(e){
      let allLineTime = this.$refs.allLineTime;
      let percentNum = (e.offsetX-6)/(allLineTime.offsetWidth*1);

      this.setSelTime(percentNum);
    },
    //可选择线的区域点击
    canLineMouseDown(e){
      let canLine = this.$refs.canLine;
      let allLineTime = this.$refs.allLineTime;
      let percentNum = e.offsetX/(allLineTime.offsetWidth*1);
      if(parseFloat(canLine.style.left)>0){
        percentNum = e.offsetX/(allLineTime.offsetWidth*1)+(parseFloat(canLine.style.left)/100);
      }
      this.setSelTime(percentNum);
    },
    //点击备份点---计算百分比
    clickDot(incre){
      let percentNum = (incre-this.start_date)/(this.end_date-this.start_date);
      this.setSelTime(percentNum);
    },
    //设置当前值
    setSelTime(percentNum){
      let selDot = this.$refs.selDot;
      selDot.classList.remove('sel_dot_left');
      selDot.classList.remove('sel_dot_right');

      let percent = percentNum;
      this.timeline= (this.end_date-this.start_date)*percent+this.start_date;
      //如果当前值不在binlog范围内，则不可以滑动，只能选择就近的点
      if(this.timeline>this.binlogDate || this.timeline<this.fullDate){
        this.allIncre.sort((a,b)=>{
          return Math.abs(a-this.timeline)-Math.abs(b-this.timeline);
        });
        this.timeline = this.allIncre[0];
        percent = (this.timeline-this.start_date)/(this.end_date-this.start_date);
      }
      //设置选中点日期时间
      this.selTime = moment(this.timeline*1000).format('YYYY-MM-DD HH:mm:ss');
      selDot.style.left = percent*100 + '%' ;

      //大于90%或者小于10%，提示框位置变化
      if(percent*100<10){
        selDot.classList.add('sel_dot_left');
      }
      if(percent*100>90){
        selDot.classList.add('sel_dot_right');
      }

    },
    //时间轴推拽
    dragDown(e){
      let allLineTimeWidth = this.$refs.allLineTime.offsetWidth*1;
      let selDot = this.$refs.selDot;
      //算出鼠标相对元素的位置
      let disX = e.clientX - selDot.offsetLeft;

      document.onmousemove = (e)=>{//鼠标按下并移动的事件
        //用鼠标的位置减去鼠标相对元素的位置，得到元素的位置
        let left = (e.clientX - disX)/allLineTimeWidth*100;

        //移动当前元素
        if(left>=100){
          left = 100;
        }else if(left<=0){
          left = 0;
        }
        this.setSelTime(left/100);
      };
      document.onmouseup = () => {
        document.onmousemove = null;
        document.onmouseup = null;
      };
    },
    //设置备份点位置
    setLeft(incre, i){
      if(i<=this.expireIndex){
        return  `left:${(incre-this.start_date)/(this.end_date-this.start_date)*100}%;border: 2px solid #ccc;`
      }
      return  `left:${(incre-this.start_date)/(this.end_date-this.start_date)*100}%;`
    },
    setText(i){
      if(i<=this.expireIndex){
        return  `color: #ccc;`
      }
    }
  },
  watch: {
    ddls() {
      this.$nextTick(()=>{
        this.getBackupTimeline();
      })
    }
  },
};
</script>
<style scoped>
.time_con {

}

.line_time {
  position: relative;
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}
.line_time .all_line {
  width: 90%;
  margin: 0 5%;
  padding-top: 25px;
  padding-bottom: 15px;
}
.line_time .line {
  width: 100%;
  height: 3px;
  background: #ccc;
  position: relative;
}
.line_time .can_line {
  background: #1890ff77;
  height: 3px;
  width: 0%;
  position: absolute;
  left: 0;
}
.line_time .can_line span {
  position: absolute;
  right: 0;
  margin-top: 20px;
}
.line_time .reference {
  width: 1px;
  height: 8px;
  border: 0;
  background: #bbb;
  position: absolute;
  top: -3px;
  white-space: nowrap;
}
.line_time .reference em {
  color: #bbb;
  position: absolute;
  transform: translateX(-50%);
  margin-top: 5px;
  font-size: 12px;
}
.line_time .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 2px solid #4a9eff;
  background: white;
  position: absolute;
  top: -3px;
  white-space: nowrap;
  margin-left: -4px;
}
.line_time .dot_all em {
  display: none;
  color: #409eff;
  transform: translateX(-50%);
  position: absolute;
  top: -25px;
}
.line_time .dot_all:hover {
  width: 10px;
  height: 10px;
  border: 2px solid #409eff;
  top: -4px;
}
.line_time .dot_all:hover em {
  display: inline-block;
}
.line_time .square {
  width: 8px;
  height: 8px;
  border-radius: 0%;
  border: 2px solid #4a9eff;
  background: white;
  position: absolute;
  top: -3px;
  white-space: nowrap;
  margin-left: -4px;
}
.line_time .square_all em {
  display: none;
  color: #409eff;
  transform: translateX(-50%);
  position: absolute;
  top: -25px;
}
.line_time .square_all:hover {
  width: 10px;
  height: 10px;
  border: 2px solid #409eff;
  top: -4px;
}
.line_time .square_all:hover em {
  display: inline-block;
}
.line_time .sel_dot {
  width: 10px;
  height: 10px;
  top: -4px;
  border: 2px solid #FFA500;
  box-shadow: 0 0 10px 4px #faa30255;
  z-index: 5;
  position: absolute;
}
.line_time .sel_dot em {
  display: none;
  color: #FFA500;
  transform: translateX(-50%);
  position: absolute;
  top: -25px;
}

.line_time .sel_dot:hover em {
  display: inline-block;
}

.line_time .sel_dot_left em {
  transform: translateX(-20%);
}
.line_time .sel_dot_left i {
  left: 20%;
}
.line_time .sel_dot_right em {
  transform: translateX(-80%);
}
.line_time .sel_dot_right i {
  left: 80%;
}
</style>