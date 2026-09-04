import { defineConfig } from 'vitepress'

const repository = 'https://github.com/zh1peng/FSHarvest'
const siteUrl = 'https://zh1peng.github.io/FSHarvest/'

export default defineConfig({
  base: '/FSHarvest/',
  cleanUrls: true,
  lastUpdated: true,
  appearance: true,
  sitemap: { hostname: siteUrl },
  head: [
    ['link', { rel: 'icon', type: 'image/png', href: '/FSHarvest/fsharvest-logo.png' }],
    ['meta', { name: 'theme-color', content: '#061b35' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'FSHarvest' }],
    ['meta', { property: 'og:title', content: 'FSHarvest' }],
    ['meta', { property: 'og:description', content: '从 FreeSurfer 受试者目录批量收获可分析、可审计的脑区特征' }],
    ['meta', { property: 'og:image', content: `${siteUrl}og.png` }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:title', content: 'FSHarvest' }],
    ['meta', { name: 'twitter:description', content: 'Harvest analysis-ready FreeSurfer features' }],
    ['meta', { name: 'twitter:image', content: `${siteUrl}og.png` }],
  ],
  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      title: 'FSHarvest',
      titleTemplate: ':title · FSHarvest',
      description: '从 FreeSurfer 受试者目录批量收获可分析、可审计的脑区特征',
      themeConfig: {
        logo: '/fsharvest-logo.png',
        siteTitle: 'FSHarvest',
        nav: [
          { text: '开始', link: '/guide/introduction' },
          { text: '文档', link: '/guide/outputs' },
          { text: '教程', link: '/tutorials/basic-extraction' },
          { text: 'Atlas', link: '/guide/atlases' },
          { text: '命令行', link: '/reference/cli' },
        ],
        sidebar: [
          {
            text: '从这里开始',
            items: [
              { text: '项目概览', link: '/' },
              { text: 'FSHarvest 做什么', link: '/guide/introduction' },
              { text: '安装', link: '/guide/installation' },
              { text: '五分钟快速开始', link: '/guide/quick-start' },
            ],
          },
          {
            text: '核心文档',
            items: [
              { text: '输出与数据表', link: '/guide/outputs' },
              { text: 'Atlas 与投影路径', link: '/guide/atlases' },
              { text: '表面 QC', link: '/guide/qc' },
              { text: '缓存、审计与复现', link: '/guide/reproducibility' },
            ],
          },
          {
            text: '使用教程',
            items: [
              { text: '基础批量提取', link: '/tutorials/basic-extraction' },
              { text: '多 Atlas 分析', link: '/tutorials/multi-atlas' },
              { text: 'QC 工作流', link: '/tutorials/qc-workflow' },
              { text: '在 Slurm 上运行', link: '/tutorials/slurm' },
            ],
          },
          {
            text: '参考',
            items: [
              { text: '命令行参数', link: '/reference/cli' },
              { text: '验证与兼容性', link: '/reference/validation' },
              { text: '引用与许可证', link: '/reference/citation' },
            ],
          },
        ],
        outline: { level: [2, 3], label: '本页目录' },
        docFooter: { prev: '上一页', next: '下一页' },
        lastUpdated: { text: '最后更新于' },
        editLink: {
          pattern: `${repository}/edit/main/website/:path`,
          text: '在 GitHub 上编辑此页',
        },
        sidebarMenuLabel: '目录',
        returnToTopLabel: '返回顶部',
        langMenuLabel: '切换语言',
        darkModeSwitchLabel: '外观',
        search: { provider: 'local' },
        socialLinks: [{ icon: 'github', link: repository }],
        footer: {
          message: '以 MIT 许可证发布 · 中文文档优先维护，英文版持续完善中',
          copyright: 'Copyright © FSHarvest contributors',
        },
      },
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/',
      title: 'FSHarvest',
      titleTemplate: ':title · FSHarvest',
      description: 'Harvest analysis-ready FreeSurfer features at cohort scale',
      themeConfig: {
        logo: '/fsharvest-logo.png',
        siteTitle: 'FSHarvest',
        nav: [
          { text: 'English home', link: '/en/' },
          { text: '中文文档', link: '/' },
          { text: 'GitHub', link: repository },
        ],
        sidebar: false,
        outline: false,
        search: { provider: 'local' },
        socialLinks: [{ icon: 'github', link: repository }],
        footer: {
          message: 'English documentation is under development.',
          copyright: 'Copyright © FSHarvest contributors',
        },
      },
    },
  },
})
