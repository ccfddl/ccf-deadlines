import Vue from 'vue'
import App from './App.vue'
import ElementUI from 'element-ui'
import 'element-ui/lib/theme-chalk/index.css'
Vue.use(ElementUI)
import VueResource from 'vue-resource'
Vue.use(VueResource)
import VueCountdown from '@chenfengyuan/vue-countdown'
Vue.component(VueCountdown.name, VueCountdown)
Vue.config.productionTip = false

new Vue({
  render: h => h(App),
}).$mount('#app')