// 应用入口:创建 Vue 应用、注册插件、挂载到页面
import { createApp } from 'vue'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn' // Element Plus 中文语言包(按钮/提示等文案)
import * as ElementPlusIconsVue from '@element-plus/icons-vue' // 图标库

const app = createApp(App)

app.use(ElementPlus, {
  locale: zhCn, // 让 Element Plus 组件显示中文
})
// 把全部图标注册为全局组件,模板里可直接用 <el-icon><xxx /></el-icon>
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 挂载到 index.html 里的 <div id="app">
app.mount('#app')
