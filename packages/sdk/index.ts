/**
 * QCSpec · TypeScript SDK
 * 前端直接调用 Supabase + v:// 协议
 *
 * 安装：npm install @supabase/supabase-js
 * 用法：import { QCSpec } from './qcspec-sdk'
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js'

// ─────────────────────────────────────────
// 类型定义
// ─────────────────────────────────────────

export type DtoRole = 'PUBLIC' | 'MARKET' | 'AI' | 'SUPERVISOR' | 'OWNER' | 'REGULATOR'
export type InspectResult = 'pass' | 'warn' | 'fail'
export type ProjectStatus = 'pending' | 'active' | 'closed'
export type ProofStatus = 'pending' | 'confirmed' | 'sealed'

export interface Enterprise {
  id: string
  v_uri: string
  name: string
  short_name?: string
  credit_code?: string
  domain?: string
  plan: string
  proof_quota: number
  proof_used: number
  created_at: string
}

export interface User {
  id: string
  enterprise_id: string
  v_uri: string
  name: string
  email?: string
  dto_role: DtoRole
  title?: string
  is_active: boolean
}

export interface Project {
  id: string
  enterprise_id: string
  v_uri: string
  name: string
  type: string
  owner_unit: string
  contractor?: string
  supervisor?: string
  contract_no?: string
  start_date?: string
  end_date?: string
  status: ProjectStatus
  record_count: number
  photo_count: number
  proof_count: number
  created_at: string
}

export interface Inspection {
  id: string
  project_id: string
  v_uri: string
  location: string
  type: string
  type_name: string
  value: number
  standard?: number
  unit: string
  result: InspectResult
  person?: string
  remark?: string
  proof_id?: string
  proof_hash?: string
  proof_status: ProofStatus
  seal_status: string
  inspected_at: string
}

export interface Photo {
  id: string
  project_id: string
  inspection_id?: string
  v_uri: string
  file_name: string
  storage_path: string
  storage_url?: string
  location?: string
  gps_lat?: number
  gps_lng?: number
  taken_at?: string
  proof_id?: string
}

export interface Report {
  id: string
  project_id: string
  v_uri: string
  report_no: string
  location?: string
  total_count: number
  pass_count: number
  warn_count: number
  fail_count: number
  pass_rate?: number
  conclusion?: string
  file_url?: string
  proof_id?: string
  seal_status: string
  generated_at: string
}

export interface ProofRecord {
  proof_id: string
  proof_hash: string
  v_uri: string
  object_type: string
  action: string
  summary?: string
  created_at: string
}

export interface ProjectStats {
  total: number
  pass: number
  warn: number
  fail: number
  pass_rate: number
  latest_at?: string
}

// ─────────────────────────────────────────
// QCSpec 客户端
// ─────────────────────────────────────────

export class QCSpecClient {
  private sb: SupabaseClient

  constructor(supabaseUrl: string, supabaseKey: string) {
    this.sb = createClient(supabaseUrl, supabaseKey)
  }

  // ══ 认证 ══

  async login(email: string, password: string) {
    const { data, error } = await this.sb.auth.signInWithPassword({ email, password })
    if (error) throw error
    return data
  }

  async logout() {
    await this.sb.auth.signOut()
  }

  async currentUser(): Promise<User | null> {
    const { data: { user } } = await this.sb.auth.getUser()
    if (!user) return null
    const { data } = await this.sb.from('users').select('*').eq('id', user.id).single()
    return data
  }

  // ══ 企业 ══

  async getEnterprise(): Promise<Enterprise> {
    const { data, error } = await this.sb
      .from('enterprises')
      .select('*')
      .single()
    if (error) throw error
    return data
  }

  // ══ 项目 ══

  async listProjects(filters?: {
    status?: ProjectStatus
    type?: string
    search?: string
  }): Promise<Project[]> {
    let q = this.sb.from('projects').select('*').order('created_at', { ascending: false })
    if (filters?.status) q = q.eq('status', filters.status)
    if (filters?.type)   q = q.eq('type', filters.type)
    if (filters?.search) q = q.ilike('name', `%${filters.search}%`)
    const { data, error } = await q
    if (error) throw error
    return data || []
  }

  async getProject(id: string): Promise<Project> {
    const { data, error } = await this.sb
      .from('projects')
      .select('*')
      .eq('id', id)
      .single()
    if (error) throw error
    return data
  }

  async createProject(params: {
    v_uri: string
    name: string
    type: string
    owner_unit: string
    contractor?: string
    supervisor?: string
    contract_no?: string
    start_date?: string
    end_date?: string
    description?: string
    seg_type?: string
    seg_start?: string
    seg_end?: string
    perm_template?: string
  }): Promise<Project> {
    const user = await this.currentUser()
    if (!user) throw new Error('未登录')
    const { data, error } = await this.sb
      .from('projects')
      .insert({ ...params, enterprise_id: user.enterprise_id, created_by: user.id })
      .select()
      .single()
    if (error) throw error
    return data
  }

  async getProjectStats(projectId: string): Promise<ProjectStats> {
    const { data, error } = await this.sb.rpc('get_project_stats', {
      p_project_id: projectId
    })
    if (error) throw error
    return data
  }

  // ══ 质检记录 ══

  async listInspections(projectId: string, filters?: {
    result?: InspectResult
    type?: string
    location?: string
    dateFrom?: string
    dateTo?: string
  }): Promise<Inspection[]> {
    let q = this.sb
      .from('inspections')
      .select('*')
      .eq('project_id', projectId)
      .order('inspected_at', { ascending: false })

    if (filters?.result)   q = q.eq('result', filters.result)
    if (filters?.type)     q = q.eq('type', filters.type)
    if (filters?.location) q = q.eq('location', filters.location)
    if (filters?.dateFrom) q = q.gte('inspected_at', filters.dateFrom)
    if (filters?.dateTo)   q = q.lte('inspected_at', filters.dateTo + 'T23:59:59Z')

    const { data, error } = await q
    if (error) throw error
    return data || []
  }

  /**
   * 提交质检记录（自动生成 Proof）
   * 返回 { inspection_id, v_uri, proof_id }
   */
  async submitInspection(params: {
    project_id: string
    location: string
    type: string
    type_name: string
    value: number
    standard?: number
    unit?: string
    result: InspectResult
    person?: string
    remark?: string
    inspected_at?: string
  }): Promise<{ inspection_id: string; v_uri: string; proof_id: string }> {
    const { data, error } = await this.sb.rpc('submit_inspection', {
      p_project_id:   params.project_id,
      p_location:     params.location,
      p_type:         params.type,
      p_type_name:    params.type_name,
      p_value:        params.value,
      p_standard:     params.standard,
      p_unit:         params.unit || '',
      p_result:       params.result,
      p_person:       params.person || '',
      p_remark:       params.remark,
      p_inspected_at: params.inspected_at,
    })
    if (error) throw error
    return data
  }

  async deleteInspection(id: string): Promise<void> {
    const { error } = await this.sb
      .from('inspections')
      .delete()
      .eq('id', id)
    if (error) throw error
  }

  // ══ 照片 ══

  /**
   * 上传照片到 Supabase Storage，自动注册 v:// 节点
   */
  async uploadPhoto(params: {
    project_id: string
    file: File
    location?: string
    inspection_id?: string
    gps_lat?: number
    gps_lng?: number
  }): Promise<Photo> {
    const user = await this.currentUser()
    if (!user) throw new Error('未登录')

    // 上传文件
    const timestamp = Date.now()
    const ext = params.file.name.split('.').pop()
    const storagePath = `${user.enterprise_id}/${params.project_id}/${timestamp}.${ext}`

    const { error: uploadError } = await this.sb.storage
      .from('qcspec-photos')
      .upload(storagePath, params.file)
    if (uploadError) throw uploadError

    // 获取URL
    const { data: { publicUrl } } = this.sb.storage
      .from('qcspec-photos')
      .getPublicUrl(storagePath)

    // 注册照片记录
    const { data, error } = await this.sb
      .from('photos')
      .insert({
        project_id:     params.project_id,
        enterprise_id:  user.enterprise_id,
        inspection_id:  params.inspection_id,
        file_name:      params.file.name,
        storage_path:   storagePath,
        storage_url:    publicUrl,
        location:       params.location,
        gps_lat:        params.gps_lat,
        gps_lng:        params.gps_lng,
        file_size:      params.file.size,
        uploaded_by:    user.id,
        taken_at:       new Date().toISOString(),
      })
      .select()
      .single()
    if (error) throw error
    return data
  }

  async listPhotos(projectId: string, inspectionId?: string): Promise<Photo[]> {
    let q = this.sb
      .from('photos')
      .select('*')
      .eq('project_id', projectId)
      .order('created_at', { ascending: false })
    if (inspectionId) q = q.eq('inspection_id', inspectionId)
    const { data, error } = await q
    if (error) throw error
    return data || []
  }

  // ══ 报告 ══

  /**
   * 生成质检报告（调用后端 Python 引擎或 Edge Function）
   */
  async generateReport(params: {
    project_id: string
    location?: string
    date_from?: string
    date_to?: string
  }): Promise<Report> {
    // Step 1：获取汇总数据
    const { data: reportData, error: dataError } = await this.sb.rpc('generate_report_data', {
      p_project_id: params.project_id,
      p_location:   params.location,
      p_date_from:  params.date_from,
      p_date_to:    params.date_to,
    })
    if (dataError) throw dataError

    // Step 2：调用报告生成 Edge Function
    const { data, error } = await this.sb.functions.invoke('generate-qc-report', {
      body: { project_id: params.project_id, report_data: reportData, ...params }
    })
    if (error) throw error
    return data
  }

  async listReports(projectId: string): Promise<Report[]> {
    const { data, error } = await this.sb
      .from('reports')
      .select('*')
      .eq('project_id', projectId)
      .order('generated_at', { ascending: false })
    if (error) throw error
    return data || []
  }

  // ══ Proof 链 ══

  async getProofChain(params: {
    v_uri?: string
    project_id?: string
    limit?: number
  }): Promise<ProofRecord[]> {
    let q = this.sb
      .from('proof_chain')
      .select('proof_id, proof_hash, v_uri, object_type, action, summary, created_at')
      .order('created_at', { ascending: false })
      .limit(params.limit || 50)
    if (params.v_uri)      q = q.eq('v_uri', params.v_uri)
    if (params.project_id) q = q.eq('project_id', params.project_id)
    const { data, error } = await q
    if (error) throw error
    return data || []
  }

  async verifyProof(proofId: string): Promise<{
    valid: boolean
    proof: ProofRecord | null
    chain_length: number
  }> {
    const { data, error } = await this.sb
      .from('proof_chain')
      .select('*')
      .eq('proof_id', proofId)
      .single()
    if (error) return { valid: false, proof: null, chain_length: 0 }

    const { count } = await this.sb
      .from('proof_chain')
      .select('*', { count: 'exact', head: true })
      .eq('v_uri', data.v_uri)

    return { valid: true, proof: data, chain_length: count || 0 }
  }

  // ══ v:// 节点树 ══

  async getNodeTree(rootUri: string) {
    const { data, error } = await this.sb.rpc('get_v_node_tree', {
      p_root_uri: rootUri
    })
    if (error) throw error
    return data || []
  }

  // ══ 实时订阅 ══

  /**
   * 订阅项目质检记录实时更新
   */
  subscribeInspections(
    projectId: string,
    callback: (inspection: Inspection) => void
  ) {
    return this.sb.channel(`inspections:${projectId}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'inspections',
        filter: `project_id=eq.${projectId}`,
      }, payload => callback(payload.new as Inspection))
      .subscribe()
  }

  /**
   * 订阅 Proof 链更新（实时存证通知）
   */
  subscribeProofs(
    projectId: string,
    callback: (proof: ProofRecord) => void
  ) {
    return this.sb.channel(`proofs:${projectId}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'proof_chain',
        filter: `project_id=eq.${projectId}`,
      }, payload => callback(payload.new as ProofRecord))
      .subscribe()
  }

  // ══ 团队管理 ══

  async listMembers(): Promise<User[]> {
    const { data, error } = await this.sb
      .from('users')
      .select('*')
      .eq('is_active', true)
      .order('name')
    if (error) throw error
    return data || []
  }

  async inviteMember(params: {
    name: string
    email: string
    dto_role: DtoRole
    title?: string
  }): Promise<User> {
    const user = await this.currentUser()
    if (!user) throw new Error('未登录')

    // 生成 v:// URI
    const v_uri = `${(await this.getEnterprise()).v_uri}executor/${params.name}/`

    const { data, error } = await this.sb
      .from('users')
      .insert({
        enterprise_id: user.enterprise_id,
        v_uri,
        name:     params.name,
        email:    params.email,
        dto_role: params.dto_role,
        title:    params.title,
      })
      .select()
      .single()
    if (error) throw error
    return data
  }

  async addProjectMember(projectId: string, userId: string, role: DtoRole): Promise<void> {
    const { error } = await this.sb
      .from('project_members')
      .insert({ project_id: projectId, user_id: userId, dto_role: role })
    if (error) throw error
  }

  // ══ 配置 ══

  async getConfig() {
    const { data, error } = await this.sb
      .from('enterprise_configs')
      .select('*')
      .single()
    if (error) throw error
    return data
  }

  async updateConfig(updates: Record<string, unknown>): Promise<void> {
    const user = await this.currentUser()
    if (!user) throw new Error('未登录')
    const { error } = await this.sb
      .from('enterprise_configs')
      .update({ ...updates, updated_at: new Date().toISOString() })
      .eq('enterprise_id', user.enterprise_id)
    if (error) throw error
  }
}

// ─────────────────────────────────────────
// 默认实例（替换为真实环境变量）
// ─────────────────────────────────────────

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
  || 'https://your-project.supabase.co'
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  || 'your-anon-key'

export const qcspec = new QCSpecClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// ─────────────────────────────────────────
// 使用示例（注释）
// ─────────────────────────────────────────

/*
import { qcspec } from './qcspec-sdk'

// 1. 登录
await qcspec.login('admin@zhongbei.com', 'password')

// 2. 获取项目列表
const projects = await qcspec.listProjects({ status: 'active' })

// 3. 提交质检记录（自动生成Proof）
const result = await qcspec.submitInspection({
  project_id: 'uuid...',
  location:   'K50+200',
  type:       'flatness',
  type_name:  '路面平整度',
  value:       1.8,
  standard:    2.0,
  unit:       'm/km',
  result:     'pass',
  person:     '张工',
})
console.log(result.proof_id) // GP-PROOF-XXXXXXXX

// 4. 上传照片
const photo = await qcspec.uploadPhoto({
  project_id:   'uuid...',
  file:          imageFile,
  location:     'K50+200',
  inspection_id: result.inspection_id,
})

// 5. 实时订阅
qcspec.subscribeInspections('project-uuid', (insp) => {
  console.log('新质检记录:', insp.type_name, insp.result)
})

// 6. 实时订阅Proof链
qcspec.subscribeProofs('project-uuid', (proof) => {
  console.log('新Proof:', proof.proof_id)
})

// 7. 查询项目统计
const stats = await qcspec.getProjectStats('uuid...')
console.log(`合格率：${stats.pass_rate}%`)

// 8. 验证Proof
const verify = await qcspec.verifyProof('GP-PROOF-XXXXXXXX')
console.log(verify.valid) // true

// 9. 查询 v:// 节点树
const tree = await qcspec.getNodeTree('v://cn.中北/')
*/
