/**
 * QCSpec · 共享类型定义
 * packages/types/index.ts
 */

// ── DTORole（对应 Supabase 枚举）──
export type DtoRole =
  | 'PUBLIC'
  | 'MARKET'
  | 'AI'
  | 'SUPERVISOR'
  | 'OWNER'
  | 'REGULATOR'

// ── 质检结果 ──
export type InspectResult = 'pass' | 'warn' | 'fail'

// ── 项目状态 ──
export type ProjectStatus = 'pending' | 'active' | 'closed'

// ── Proof 状态 ──
export type ProofStatus = 'pending' | 'confirmed' | 'sealed'

// ── 检测类型配置 ──
export interface InspectionTypeConfig {
  key:      string
  label:    string
  unit:     string
  standard: number
  better:   'less' | 'more' | 'approx'
  category: '路面' | '结构' | '桥梁' | '市政' | '房建' | '水利'
  normRef?: string   // v://standard/JTG-F80/...
}

export const INSPECTION_TYPES: Record<string, InspectionTypeConfig> = {
  flatness:       { key:'flatness',       label:'路面平整度',   unit:'m/km', standard:2.0,  better:'less',   category:'路面', normRef:'v://standard/JTG-F80/4.2' },
  crack:          { key:'crack',          label:'裂缝宽度',     unit:'mm',   standard:0.2,  better:'less',   category:'路面', normRef:'v://standard/JTG-F80/4.3' },
  rut:            { key:'rut',            label:'车辙深度',     unit:'mm',   standard:20,   better:'less',   category:'路面' },
  slope:          { key:'slope',          label:'横坡坡度',     unit:'%',    standard:2.0,  better:'approx', category:'路面' },
  settlement:     { key:'settlement',     label:'路基沉降',     unit:'mm',   standard:30,   better:'less',   category:'结构' },
  bearing:        { key:'bearing',        label:'路基承载力',   unit:'MPa',  standard:30,   better:'more',   category:'结构' },
  compaction:     { key:'compaction',     label:'压实度',       unit:'%',    standard:96,   better:'more',   category:'结构', normRef:'v://standard/JTG-F80/3.1' },
  bridge_crack:   { key:'bridge_crack',   label:'桥梁裂缝',     unit:'mm',   standard:0.2,  better:'less',   category:'桥梁', normRef:'v://standard/JTG-F80/6.1' },
  bridge_deflect: { key:'bridge_deflect', label:'挠度',         unit:'mm',   standard:5.0,  better:'less',   category:'桥梁' },
  bridge_erosion: { key:'bridge_erosion', label:'混凝土碳化',   unit:'mm',   standard:10,   better:'less',   category:'桥梁' },
  // 市政
  pipe_pressure:  { key:'pipe_pressure',  label:'管道压力',     unit:'MPa',  standard:0.6,  better:'more',   category:'市政' },
  // 房建
  concrete_str:   { key:'concrete_str',   label:'混凝土强度',   unit:'MPa',  standard:30,   better:'more',   category:'房建', normRef:'v://standard/GB50204/7.1' },
  rebar_spacing:  { key:'rebar_spacing',  label:'钢筋间距',     unit:'mm',   standard:200,  better:'approx', category:'房建', normRef:'v://standard/GB50204/5.3' },
}

// ── 核心业务对象 ──
export interface Enterprise {
  id:          string
  v_uri:       string   // v://cn.企业名/
  name:        string
  short_name?: string
  plan:        'basic' | 'pro' | 'enterprise'
  proof_quota: number
  proof_used:  number
}

export interface User {
  id:            string
  enterprise_id: string
  v_uri:         string   // v://cn.企业/executor/姓名/
  name:          string
  email?:        string
  dto_role:      DtoRole
  title?:        string
}

export interface Project {
  id:            string
  enterprise_id: string
  v_uri:         string
  name:          string
  type:          string
  owner_unit:    string
  contractor?:   string
  supervisor?:   string
  contract_no?:  string
  start_date?:   string
  end_date?:     string
  status:        ProjectStatus
  record_count:  number
  photo_count:   number
  proof_count:   number
}

export interface Inspection {
  id:            string
  project_id:    string
  v_uri:         string
  location:      string
  type:          string
  type_name:     string
  value:         number
  standard?:     number
  unit:          string
  result:        InspectResult
  person?:       string
  remark?:       string
  proof_id?:     string
  proof_hash?:   string
  proof_status:  ProofStatus
  seal_status:   string
  inspected_at:  string
}

export interface Photo {
  id:             string
  project_id:     string
  inspection_id?: string
  v_uri:          string
  file_name:      string
  storage_path:   string
  storage_url?:   string
  location?:      string
  gps_lat?:       number
  gps_lng?:       number
  taken_at?:      string
  proof_id?:      string
}

export interface Report {
  id:           string
  project_id:   string
  v_uri:        string
  report_no:    string
  location?:    string
  total_count:  number
  pass_count:   number
  warn_count:   number
  fail_count:   number
  pass_rate?:   number
  conclusion?:  string
  fail_items?:  string
  suggestions?: string
  file_url?:    string
  proof_id?:    string
  seal_status:  string
  generated_at: string
}

export interface ProofRecord {
  proof_id:    string
  proof_hash:  string
  v_uri:       string
  object_type: string
  action:      string
  summary?:    string
  created_at:  string
}

export interface ProjectStats {
  total:     number
  pass:      number
  warn:      number
  fail:      number
  pass_rate: number
  latest_at?: string
}

// ── 报告生成参数 ──
export interface ReportGenerateParams {
  project_id: string
  location?:  string
  date_from?: string
  date_to?:   string
}

// ── v:// 节点 ──
export interface VNode {
  uri:        string
  parent_uri?: string
  node_type:  'Enterprise' | 'Project' | 'Segment' | 'Report' | 'Photo' | 'Device'
  peg_count:  number
  status:     string
  metadata?:  Record<string, unknown>
}

// ── 工具函数类型 ──
export type ResultOk<T>  = { ok: true;  data: T }
export type ResultErr    = { ok: false; error: string }
export type Result<T>    = ResultOk<T> | ResultErr

// ── 常量 ──
export const RESULT_LABELS: Record<InspectResult, string> = {
  pass: '✓ 合格',
  warn: '⚠ 观察',
  fail: '✗ 不合格',
}

export const RESULT_COLORS: Record<InspectResult, string> = {
  pass: '#059669',
  warn: '#D97706',
  fail: '#DC2626',
}

export const PROJECT_TYPE_NAMES: Record<string, string> = {
  highway:       '高速公路',
  road:          '普通公路',
  urban:         '城市道路',
  bridge:        '桥梁新建',
  bridge_repair: '桥梁维修',
  tunnel:        '隧道工程',
  municipal:     '市政工程',
  water:         '水利工程',
  building:      '房屋建筑',
}
