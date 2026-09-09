import DefaultTheme from 'vitepress/theme'
import './style.css'
import ExampleTable from './components/ExampleTable.vue'
import type { Theme } from 'vitepress'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('ExampleTable', ExampleTable)
  }
} satisfies Theme
