<script setup lang="ts">
import { computed, ref } from 'vue'
import { withBase } from 'vitepress'

const props = defineProps<{ tsv: string; caption: string; download: string }>()
const query = ref('')
const sortColumn = ref(-1)
const descending = ref(false)
const data = computed(() => props.tsv.split(/\r?\n/).filter(line => line.length > 0).map(line => line.split('\t')))
const headers = computed(() => data.value[0])
const rows = computed(() => data.value.slice(1))
const labels: Record<string, string> = {
  folder_id: '受试者目录', status: '处理状态', fs_version: '重建版本',
  cortical_rows: '皮层结果行数', aseg_rows: 'aseg 结果行数', qc_status: 'QC 状态', cache_hit: '复用缓存',
  atlas: '图谱', hemisphere: '半球', region: '脑区名称', numvert: '顶点数',
  surfarea: '表面积（mm²）', grayvol: '灰质体积（mm³）', thickavg: '平均厚度（mm）',
  key: '图谱名称', expected_total: '预期脑区总数', lh_expected_rows: '左半球脑区数',
  rh_expected_rows: '右半球脑区数', kind: '图谱类型', source_subject: '源模板',
  observed_subjects_complete: '结果完整的受试者数',
  dk68__L_bankssts_thickavg: '左 bankssts 厚度（mm）',
  dk68__R_bankssts_thickavg: '右 bankssts 厚度（mm）',
  'aseg__Left-Hippocampus__volume_mm3': '左海马体积（mm³）'
}
const collator = new Intl.Collator('zh-CN', { numeric: true })
const visibleRows = computed(() => {
  const term = query.value.trim().toLowerCase()
  const filtered = rows.value.filter(row => row.some(cell => cell.toLowerCase().includes(term)))
  if (sortColumn.value < 0) return filtered
  return filtered.sort((a, b) => {
    const left = a[sortColumn.value] ?? ''
    const right = b[sortColumn.value] ?? ''
    // Missing values stay last in either direction; they are never treated as zero.
    if (!left || !right) return !left && !right ? 0 : !left ? 1 : -1
    const comparison = Number.isFinite(Number(left)) && Number.isFinite(Number(right))
      ? Number(left) - Number(right) : collator.compare(left, right)
    return descending.value ? -comparison : comparison
  })
})
function sort(index: number) {
  descending.value = sortColumn.value === index ? !descending.value : false
  sortColumn.value = index
}
function reset() {
  query.value = ''
  sortColumn.value = -1
  descending.value = false
}
</script>

<template>
  <section class="example-table" :aria-label="caption">
    <div class="table-controls">
      <label>搜索示例数据
        <input v-model="query" type="search" placeholder="输入受试者、脑区或数值" />
      </label>
      <button type="button" class="reset" @click="reset">重置</button>
      <a :href="withBase(download)" download>下载 TSV</a>
    </div>
    <p class="table-hint" aria-live="polite">显示 {{ visibleRows.length }} / {{ rows.length }} 行示例数据。点击列标题排序；— 表示空值。</p>
    <div class="table-scroll" tabindex="0" role="region" :aria-label="`${caption}，可横向滚动`">
      <table>
        <caption>{{ caption }}</caption>
        <thead><tr>
          <th v-for="(header, index) in headers" :key="header" scope="col"
            :aria-sort="sortColumn === index ? (descending ? 'descending' : 'ascending') : 'none'">
            <button type="button" @click="sort(index)">
              <span>{{ labels[header] || header }} <span aria-hidden="true">{{ sortColumn === index ? (descending ? '↓' : '↑') : '↕' }}</span></span>
              <small v-if="labels[header]">{{ header }}</small>
            </button>
          </th>
        </tr></thead>
        <tbody>
          <tr v-for="(row, index) in visibleRows" :key="index">
            <td v-for="(header, column) in headers" :key="header">
              <span v-if="row[column] === '' || row[column] === undefined" class="empty" title="空值" aria-label="空值">—</span>
              <template v-else>{{ row[column] }}</template>
            </td>
          </tr>
          <tr v-if="visibleRows.length === 0"><td :colspan="headers.length">没有匹配的示例数据，请修改搜索内容或重置。</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.example-table { min-width: 0; margin: 1.5rem 0; }
.table-controls { display: flex; flex-wrap: wrap; align-items: end; gap: 12px; font-size: 14px; }
.table-controls label { display: grid; gap: 4px; flex: 1 1 220px; }
.table-controls input { width: 100%; padding: 7px 10px; border: 1px solid var(--vp-c-divider); border-radius: 6px; background: var(--vp-c-bg); }
.table-controls .reset { padding: 7px 12px; border: 1px solid var(--vp-c-divider); border-radius: 6px; }
.table-controls a { padding: 7px 0; }
.table-hint { margin: 10px 0; font-size: 13px; color: var(--vp-c-text-2); }
.table-scroll { overflow-x: auto; border: 1px solid var(--vp-c-divider); border-radius: 8px; }
.example-table table { display: table; width: 100%; margin: 0; font-size: 14px; white-space: nowrap; font-variant-numeric: tabular-nums; }
caption { padding: 10px 12px; text-align: left; font-weight: 600; }
.example-table th, .example-table td { padding: 10px 12px; border: 0; border-top: 1px solid var(--vp-c-divider); }
.example-table th { background: var(--vp-c-bg-soft); text-align: left; }
th button { display: block; width: 100%; text-align: left; }
th small { display: block; max-width: 240px; white-space: normal; overflow-wrap: anywhere; font-family: var(--vp-font-family-mono); font-size: 11px; font-weight: 400; color: var(--vp-c-text-2); }
button { cursor: pointer; }
button:hover { color: var(--vp-c-brand-1); }
button:focus-visible, input:focus-visible, .table-scroll:focus-visible { outline: 2px solid var(--vp-c-brand-1); outline-offset: 2px; }
.empty { color: var(--vp-c-text-3); }
</style>
