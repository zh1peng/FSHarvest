import { defineConfig } from 'vitepress'

const repository = 'https://github.com/zh1peng/FSHarvest'
const siteUrl = 'https://zh1peng.github.io/FSHarvest/'

export default defineConfig({
  base: '/FSHarvest/',
  cleanUrls: true,
  srcExclude: ['README.md'],
  lastUpdated: true,
  appearance: true,
  markdown: {
    codeCopyButtonTitle: '复制代码',
    config(md) {
      const fence = md.renderer.rules.fence!
      md.renderer.rules.fence = (tokens, index, options, env, self) => {
        const html = fence(tokens, index, options, env, self)
        return env.relativePath?.startsWith('en/')
          ? html.replace('<button title="复制代码"', '<button title="Copy code"')
          : html
      }
    },
  },
  sitemap: { hostname: siteUrl },
  head: [
    ['link', { rel: 'icon', type: 'image/png', href: '/FSHarvest/fsharvest-logo.png' }],
    ['meta', { name: 'theme-color', content: '#061b35' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'FSHarvest' }],
    ['meta', { property: 'og:title', content: 'FSHarvest' }],
    ['meta', { property: 'og:description', content: '批量提取和整理 FreeSurfer 脑区指标' }],
    ['meta', { property: 'og:image', content: `${siteUrl}og.png` }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:title', content: 'FSHarvest' }],
    ['meta', { name: 'twitter:description', content: 'Batch extraction of FreeSurfer regional measures' }],
    ['meta', { name: 'twitter:image', content: `${siteUrl}og.png` }],
  ],
  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      title: 'FSHarvest',
      titleTemplate: ':title · FSHarvest',
      description: '批量提取 FreeSurfer 脑区指标，并记录处理状态、软件版本和运行参数',
      themeConfig: {
        i18nRouting: true,
        logo: '/fsharvest-logo.png',
        siteTitle: 'FSHarvest',
        nav: [
          { text: '入门', link: '/guide/introduction' },
          { text: '输出说明', link: '/guide/outputs' },
          { text: '教程', link: '/tutorials/basic-extraction' },
          { text: '脑区分区', link: '/guide/atlases' },
          { text: '参数参考', link: '/reference/cli' },
        ],
        sidebar: [
          {
            text: '入门',
            items: [
              { text: '首页', link: '/' },
              { text: '工具概述', link: '/guide/introduction' },
              { text: '安装', link: '/guide/installation' },
              { text: '五分钟快速开始', link: '/guide/quick-start' },
            ],
          },
          {
            text: '核心文档',
            items: [
              { text: '输出与数据表', link: '/guide/outputs' },
              { text: '脑区分区与处理方式', link: '/guide/atlases' },
              { text: '生成表面 QC 图', link: '/guide/qc' },
              { text: '缓存与运行记录', link: '/guide/reproducibility' },
            ],
          },
          {
            text: '使用教程',
            items: [
              { text: '10 位受试者真实运行示例', link: '/tutorials/ten-subject-example' },
              { text: '批量提取 FreeSurfer 指标', link: '/tutorials/basic-extraction' },
              { text: '同时提取多个脑区分区', link: '/tutorials/multi-atlas' },
              { text: '批量查看 QC 图', link: '/tutorials/qc-workflow' },
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
          message: 'FSHarvest 代码采用 MIT 许可证；随附脑区分区文件遵循各自的上游许可证。',
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
      description: 'Batch extraction of FreeSurfer regional measures',
      themeConfig: {
        i18nRouting: true,
        logo: '/fsharvest-logo.png',
        siteTitle: 'FSHarvest',
        nav: [
          { text: 'Getting started', link: '/en/guide/introduction' },
          { text: 'Outputs', link: '/en/guide/outputs' },
          { text: 'Tutorials', link: '/en/tutorials/basic-extraction' },
          { text: 'Parcellations', link: '/en/guide/atlases' },
          { text: 'CLI reference', link: '/en/reference/cli' },
        ],
        sidebar: [
          {
            text: 'Getting started',
            items: [
              { text: 'Home', link: '/en/' },
              { text: 'Overview', link: '/en/guide/introduction' },
              { text: 'Installation', link: '/en/guide/installation' },
              { text: 'Five-minute quick start', link: '/en/guide/quick-start' },
            ],
          },
          {
            text: 'Core documentation',
            items: [
              { text: 'Outputs and data tables', link: '/en/guide/outputs' },
              { text: 'Parcellations and extraction', link: '/en/guide/atlases' },
              { text: 'Surface QC images', link: '/en/guide/qc' },
              { text: 'Caching and run records', link: '/en/guide/reproducibility' },
            ],
          },
          {
            text: 'Tutorials',
            items: [
              { text: 'Ten-subject worked example', link: '/en/tutorials/ten-subject-example' },
              { text: 'Batch extraction', link: '/en/tutorials/basic-extraction' },
              { text: 'Extracting multiple parcellations', link: '/en/tutorials/multi-atlas' },
              { text: 'Reviewing QC images', link: '/en/tutorials/qc-workflow' },
              { text: 'Running on Slurm', link: '/en/tutorials/slurm' },
            ],
          },
          {
            text: 'Reference',
            items: [
              { text: 'Command-line reference', link: '/en/reference/cli' },
              { text: 'Validation and compatibility', link: '/en/reference/validation' },
              { text: 'Citation and licensing', link: '/en/reference/citation' },
            ],
          },
        ],
        outline: { level: [2, 3], label: 'On this page' },
        docFooter: { prev: 'Previous page', next: 'Next page' },
        lastUpdated: { text: 'Last updated' },
        editLink: {
          pattern: `${repository}/edit/main/website/:path`,
          text: 'Edit this page on GitHub',
        },
        sidebarMenuLabel: 'Menu',
        returnToTopLabel: 'Back to top',
        langMenuLabel: 'Change language',
        darkModeSwitchLabel: 'Appearance',
        search: { provider: 'local' },
        socialLinks: [{ icon: 'github', link: repository }],
        footer: {
          message: 'FSHarvest code is MIT-licensed; bundled parcellations retain their upstream licenses.',
          copyright: 'Copyright © FSHarvest contributors',
        },
      },
    },
  },
})
