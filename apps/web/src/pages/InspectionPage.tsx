
import { useCallback, useEffect, useMemo, useState  } from 'react'
import type { Inspection, Project } from '@qcspec/types'

import InspectionForm from '../components/inspection/InspectionForm'
import InspectionList from '../components/inspection/InspectionList'
import PhotoUpload from '../components/photo/PhotoUpload'
import DocpegContextPanel from '../components/inspection/DocpegContextPanel'
import { readDocpegInspectionContext } from '../components/inspection/docpegContext'
import { Button, Card, EmptyState } from '../components/ui'
import { useProjectStore, useInspectionStore, useAuthStore } from '../store'
import { useInspections } from '../hooks/api/inspections'
import { useQCSpecDocPegApi } from '../hooks/api'

type Tab = 'process' | 'quality' | 'measurement' | 'settlement' | 'audit' | 'photos'

type StatSnapshot = {
  total: number
  pass: number
  warn: number
  fail: number
  pass_rate: number
}

type ClosedLoopSnapshot = {
  contextReady: boolean
  contextHint: string
  currentStep: string
  nextAction: string
  blocker: string
  latestProofHint: string
  settlementReady: boolean
  settlementHint: string
}

const defaultClosedLoopSnapshot: ClosedLoopSnapshot = {
  contextReady: false,
  contextHint: '-',
  currentStep: '-',
  nextAction: '-',
  blocker: '未配置上下文',
  latestProofHint: '-',
  settlementReady: false,
  settlementHint: '等待质量和计量数据',
}

const INSPECTION_TAB_PARAM = 'inspection_tab'
const VALID_TABS: Tab[] = ['process', 'quality', 'measurement', 'settlement', 'audit', 'photos']

function parseTabFromUrl(): Tab | null {
  if (typeof window === 'undefined') return null
  const params = new URLSearchParams(window.location.search || '')
  const tab = String(params.get(INSPECTION_TAB_PARAM) || '').trim() as Tab
  return VALID_TABS.includes(tab) ? tab : null
}

function updateTabToUrl(tab: Tab, mode: 'replace' | 'push' = 'replace'): void {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search || '')
  params.set(INSPECTION_TAB_PARAM, tab)
  const nextUrl = `${window.location.pathname}?${params.toString()}${window.location.hash || ''}`
  if (mode === 'push') {
    window.history.pushState(window.history.state, '', nextUrl)
    return
  }
  window.history.replaceState(window.history.state, '', nextUrl)
}

export default function InspectionPage() {
  const { currentProject, projects, setCurrentProject } = useProjectStore()
  const { setInspections, stats: localStats, inspections } = useInspectionStore()
  const { enterprise } = useAuthStore()
  const { list, stats: getStats } = useInspections()
  const [tab, setTab] = useState<Tab>(() => parseTabFromUrl() || 'quality')
  const [apiStats, setApiStats] = useState<StatSnapshot>(localStats)
  const [docpegContextRevision, setDocpegContextRevision] = useState(0)
  const [showRecordCenter, setShowRecordCenter] = useState(false)

  const changeTab = useCallback((next: Tab, mode: 'replace' | 'push' = 'push') => {
    setTab(next)
    updateTabToUrl(next, mode)
  }, [])

  const latestProofId = useMemo(() => {
    const hit = inspections.find((item) => String(item.proof_id || '').trim())
    return String(hit?.proof_id || '').trim()
  }, [inspections])

  const recentInspections = useMemo(() => {
    return [...inspections]
      .sort((a, b) => new Date(b.inspected_at).getTime() - new Date(a.inspected_at).getTime())
      .slice(0, 3)
  }, [inspections])

  const refreshInspectionData = useCallback(async () => {
    if (!currentProject?.id) return
    const [listRes, statsRes] = await Promise.all([list(currentProject.id), getStats(currentProject.id)])

    const listPayload = listRes as { data?: Parameters<typeof setInspections>[0] } | null
    if (listPayload?.data) setInspections(listPayload.data)

    const statsPayload = statsRes as Partial<StatSnapshot> | null
    if (!statsPayload) return

    setApiStats({
      total: Number(statsPayload.total || 0),
      pass: Number(statsPayload.pass || 0),
      warn: Number(statsPayload.warn || 0),
      fail: Number(statsPayload.fail || 0),
      pass_rate: Number(statsPayload.pass_rate || 0),
    })
  }, [currentProject?.id, getStats, list, setInspections])

  useEffect(() => {
    if (!currentProject?.id) return
    void refreshInspectionData()
  }, [currentProject?.id, refreshInspectionData])

  useEffect(() => {
    if (!currentProject?.id) return
    setApiStats(localStats)
  }, [currentProject?.id, localStats])

  useEffect(() => {
    const routeTab = parseTabFromUrl()
    if (!routeTab) {
      updateTabToUrl(tab, 'replace')
    } else if (routeTab !== tab) {
      setTab(routeTab)
    }

    const onPopState = () => {
      const next = parseTabFromUrl()
      if (next) setTab(next)
    }
    window.addEventListener('popstate', onPopState)
    return () => {
      window.removeEventListener('popstate', onPopState)
    }
  }, [tab])

  if (!currentProject) {
    return (
      <Card title="选择项目开始质检" icon="🎯">
        {!projects.length ? (
          <EmptyState icon="📦" title="暂无项目" sub="请先在上游系统创建并同步项目" />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {projects.map((p) => (
              <ProjectSelectCard key={p.id} project={p} onSelect={() => setCurrentProject(p)} />
            ))}
          </div>
        )}
      </Card>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 420px', gap: 16, alignItems: 'start' }}>
      <div>
        <InspectionProjectHeader
          currentProject={currentProject}
          apiStats={apiStats}
          onSwitchProject={() => setCurrentProject(null)}
        />

        <div
          style={{
            display: 'flex',
            background: '#fff',
            border: '1px solid #E2E8F0',
            borderRadius: 10,
            marginTop: 12,
            marginBottom: 12,
            padding: 4,
            gap: 4,
            flexWrap: 'wrap',
          }}
        >
          {([
            { key: 'process', icon: '🔧', label: '工序推进' },
            { key: 'quality', icon: '📝', label: '质检录入' },
            { key: 'measurement', icon: '🧮', label: '计量守恒' },
            { key: 'settlement', icon: '💰', label: '结算准备' },
            { key: 'audit', icon: '🔍', label: '审计追溯' },
            { key: 'photos', icon: '📷', label: '照片上传' },
          ] as { key: Tab; icon: string; label: string }[]).map((t) => (
            <button
              key={t.key}
              onClick={() => changeTab(t.key)}
              style={{
                flex: 1,
                minWidth: 90,
                padding: '9px 8px',
                borderRadius: 7,
                border: 'none',
                cursor: 'pointer',
                fontFamily: 'var(--sans)',
                fontSize: 13,
                fontWeight: 700,
                background: tab === t.key ? '#1A56DB' : 'transparent',
                color: tab === t.key ? '#fff' : '#6B7280',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <span>{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'process' && (
          <>
            <DocpegContextPanel
              projectId={currentProject.id}
              onSaved={() => setDocpegContextRevision((v) => v + 1)}
            />
            <ProcessPanel projectId={currentProject.id} onGoQuality={() => changeTab('quality')} />
          </>
        )}

        {tab === 'quality' && (
          <InspectionForm
            key={`${currentProject.id}-${docpegContextRevision}`}
            projectId={currentProject.id}
            enterpriseId={enterprise?.id || ''}
            onSuccess={refreshInspectionData}
          />
        )}

        {tab === 'measurement' && <MeasurementPanel projectId={currentProject.id} />}

        {tab === 'settlement' && (
          <SettlementPanel
            projectId={currentProject.id}
            qualityStats={apiStats}
            latestProofId={latestProofId}
          />
        )}

        {tab === 'audit' && <AuditPanel projectId={currentProject.id} latestProofId={latestProofId} />}

        {tab === 'photos' && (
          <PhotoUpload projectId={currentProject.id} enterpriseId={enterprise?.id || ''} location="" />
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <ClosedLoopRail
          projectId={currentProject.id}
          qualityStats={apiStats}
          latestProofId={latestProofId}
          onOpenTab={(next) => changeTab(next)}
          onOpenRecords={() => setShowRecordCenter(true)}
          contextRevision={docpegContextRevision}
        />

        <RecentInspectionPanel
          items={recentInspections}
          onOpenRecords={() => setShowRecordCenter(true)}
          onGoQuality={() => changeTab('quality')}
        />
      </div>

      <div style={{ gridColumn: '1 / -1' }}>
        <Card title="记录中心" icon="🗂️">
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 10 }}>
            默认只展示最近 3 条记录。需要筛选、导出、批量查看时再展开完整记录中心。
          </div>
          <Button variant="secondary" size="sm" onClick={() => setShowRecordCenter((v) => !v)}>
            {showRecordCenter ? '收起完整记录中心' : '展开完整记录中心'}
          </Button>
          {showRecordCenter && (
            <div style={{ marginTop: 12 }}>
              <InspectionList onDataChanged={refreshInspectionData} />
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}

function InspectionProjectHeader({
  currentProject,
  apiStats,
  onSwitchProject,
}: {
  currentProject: Project
  apiStats: StatSnapshot
  onSwitchProject: () => void
}) {
  return (
    <div style={{ background: '#0F172A', borderRadius: 10, padding: '12px 14px', marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, color: '#94A3B8', marginBottom: 2 }}>当前项目</div>
          <div
            style={{
              fontSize: 13,
              color: '#60A5FA',
              fontWeight: 700,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {currentProject.name}
          </div>
        </div>
        <button
          onClick={onSwitchProject}
          style={{
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 6,
            padding: '5px 10px',
            cursor: 'pointer',
            fontSize: 12,
            color: '#CBD5E1',
            fontFamily: 'var(--sans)',
            marginLeft: 10,
          }}
        >
          切换
        </button>
      </div>
      <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#94A3B8', marginTop: 4 }}>
        {currentProject.v_uri}
      </div>

      <div
        style={{
          display: 'flex',
          gap: 12,
          marginTop: 10,
          paddingTop: 10,
          borderTop: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        {[
          { label: '总计', value: apiStats.total, color: '#94A3B8' },
          { label: '合格', value: apiStats.pass, color: '#34D399' },
          { label: '观察', value: apiStats.warn, color: '#F59E0B' },
          { label: '不合格', value: apiStats.fail, color: '#F87171' },
          {
            label: '合格率',
            value: `${apiStats.pass_rate}%`,
            color: apiStats.pass_rate >= 90 ? '#34D399' : '#F59E0B',
          },
        ].map((s) => (
          <div key={s.label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 14, fontWeight: 900, color: s.color, lineHeight: 1 }}>{s.value}</div>
            <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 2 }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
function ClosedLoopRail({
  projectId,
  qualityStats,
  latestProofId,
  contextRevision,
  onOpenTab,
  onOpenRecords,
}: {
  projectId: string
  qualityStats: StatSnapshot
  latestProofId: string
  contextRevision: number
  onOpenTab: (tab: Tab) => void
  onOpenRecords: () => void
}) {
  const {
    getBindingByEntity,
    getProcessChainStatus,
    getProcessChainRecommend,
    getBoqItems,
    getBoqUtxos,
    listTripRoleTrips,
    getSignStatus,
    loading,
    error,
  } = useQCSpecDocPegApi()

  const [snapshot, setSnapshot] = useState<ClosedLoopSnapshot>(defaultClosedLoopSnapshot)

  const refresh = useCallback(async () => {
    const context = readDocpegInspectionContext(projectId)
    const docpegProjectId = context.docpegProjectId.trim() || projectId
    const componentUri = context.docpegComponentUri.trim()
    const pileId = context.docpegPileId.trim()
    let chainId = context.docpegChainId.trim()

    let resolvedContextHint = `project=${docpegProjectId}`
    if (componentUri) resolvedContextHint += ` | component=${componentUri}`
    if (pileId) resolvedContextHint += ` | pile=${pileId}`

    if (!chainId && componentUri) {
      const bindingRes = await getBindingByEntity(docpegProjectId, componentUri)
      chainId = pickStringDeep(bindingRes, ['chain_id', 'chainId'])
    }

    let currentStep = '-'
    let nextAction = '请先完成工序上下文配置'
    let blocker = '-'
    let signBlocked = '-'

    if (chainId) {
      const [statusRes, recommendRes] = await Promise.all([
        getProcessChainStatus(docpegProjectId, {
          chain_id: chainId,
          component_uri: componentUri || undefined,
          pile_id: pileId || undefined,
        }),
        getProcessChainRecommend(docpegProjectId, {
          chain_id: chainId,
          component_uri: componentUri || undefined,
          pile_id: pileId || undefined,
        }),
      ])

      currentStep = pickStringDeep(statusRes, ['current_step_name', 'current_step', 'step']) || '-'
      nextAction = pickStringDeep(recommendRes, ['next_action', 'action', 'label']) || '-'
      resolvedContextHint += ` | chain=${chainId}`
    } else {
      blocker = componentUri || pileId ? '未绑定工序链，请先在工序页完成绑定' : '未选择构件或桩位'
    }

    const [boqItemsRes, utxosRes, tripsRes] = await Promise.all([
      getBoqItems(docpegProjectId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      getBoqUtxos(docpegProjectId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      listTripRoleTrips(docpegProjectId, {
        chain_id: chainId || undefined,
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
        limit: 20,
      }),
    ])

    const boqCount = pickArrayDeep(boqItemsRes, ['items', 'list', 'data', 'result']).length
    const utxoCount = pickArrayDeep(utxosRes, ['items', 'list', 'data', 'result']).length
    const tripItems = pickArrayDeep(tripsRes, ['items', 'list', 'data', 'result'])

    const proofHint = latestProofId || pickStringDeep(tripItems[0], ['proof_id', 'trip_proof_id']) || '-'

    const docId = pickStringDeep(tripItems[0], ['doc_id', 'docId'])
    if (docId) {
      const signRes = await getSignStatus(docId)
      signBlocked = pickStringDeep(signRes, ['blocked_reason']) || '-'
    }

    const qualityReady = qualityStats.pass > 0
    const measurementReady = boqCount > 0 && utxoCount >= 0
    const auditBlocked = signBlocked !== '-' && signBlocked !== ''

    const settlementReady = qualityReady && measurementReady && !auditBlocked

    if (blocker === '-' && auditBlocked) blocker = signBlocked
    if (blocker === '-' && !qualityReady) blocker = '暂无质检通过记录'
    if (blocker === '-' && !measurementReady) blocker = '暂无计量守恒数据'

    const settlementHint = settlementReady
      ? '满足结算前置条件'
      : qualityReady
        ? '计量或签章未完成'
        : '等待质检通过记录'

    setSnapshot({
      contextReady: Boolean(docpegProjectId && (componentUri || pileId)),
      contextHint: resolvedContextHint,
      currentStep,
      nextAction,
      blocker,
      latestProofHint: proofHint,
      settlementReady,
      settlementHint,
    })
  }, [
    getBindingByEntity,
    getBoqItems,
    getBoqUtxos,
    getProcessChainRecommend,
    getProcessChainStatus,
    getSignStatus,
    latestProofId,
    listTripRoleTrips,
    projectId,
    qualityStats.pass,
  ])

  useEffect(() => {
    void refresh()
  }, [contextRevision, refresh])

  const suggestedTab: Tab = !snapshot.contextReady
    ? 'process'
    : qualityStats.pass === 0
      ? 'quality'
      : snapshot.settlementReady
        ? 'settlement'
        : 'measurement'

  return (
    <Card title="当前任务焦点" icon="🎯">
      <div style={{ fontSize: 12, color: '#475569', marginBottom: 10, lineHeight: 1.6 }}>
        把当前页面聚焦为“下一步动作 + 阻塞原因 + 关键证据”。这三项是一线用户最需要的。
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 10, marginBottom: 10 }}>
        <MetricCard label="下一步动作" value={snapshot.nextAction || '-'} color="#1D4ED8" />
        <MetricCard label="当前步骤" value={snapshot.currentStep || '-'} color="#0F766E" />
        <MetricCard
          label="当前阻塞"
          value={snapshot.blocker === '-' ? '无阻塞' : snapshot.blocker}
          color={snapshot.blocker === '-' ? '#15803D' : '#B45309'}
        />
        <MetricCard label="关键证据" value={snapshot.latestProofHint || '-'} color="#7C3AED" />
        <MetricCard
          label="结算准备"
          value={snapshot.settlementReady ? 'READY' : 'PENDING'}
          color={snapshot.settlementReady ? '#15803D' : '#B45309'}
        />
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <Button size="sm" onClick={() => onOpenTab(suggestedTab)}>
          执行下一步
        </Button>
        <Button variant="secondary" size="sm" onClick={() => onOpenTab('process')}>
          查看工序
        </Button>
        <Button variant="secondary" size="sm" onClick={onOpenRecords}>
          查看全部记录
        </Button>
        <Button variant="secondary" size="sm" onClick={() => { void refresh() }} disabled={loading}>
          {loading ? '刷新中...' : '刷新焦点状态'}
        </Button>
        {error && <span style={{ fontSize: 12, color: '#DC2626' }}>{error}</span>}
      </div>
    </Card>
  )
}

function RecentInspectionPanel({
  items,
  onOpenRecords,
  onGoQuality,
}: {
  items: Inspection[]
  onOpenRecords: () => void
  onGoQuality: () => void
}) {
  return (
    <Card title="最近记录（3条）" icon="🧾">
      {items.length === 0 ? (
        <div style={{ fontSize: 12, color: '#94A3B8' }}>暂无记录，先去质检录入。</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map((item) => (
            <div key={item.id} style={{ border: '1px solid #E2E8F0', borderRadius: 8, padding: '8px 10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <strong style={{ fontSize: 12, color: '#0F172A' }}>{item.type_name || item.type || '-'}</strong>
                <span style={{ fontSize: 12, color: item.result === 'pass' ? '#15803D' : item.result === 'fail' ? '#B91C1C' : '#B45309' }}>
                  {item.result || '-'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>
                {item.location || '-'} | {formatShortDateTime(item.inspected_at)}
              </div>
            </div>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <Button size="sm" onClick={onGoQuality}>去录入质检</Button>
        <Button variant="secondary" size="sm" onClick={onOpenRecords}>展开完整记录</Button>
      </div>
    </Card>
  )
}

function ProcessPanel({ projectId, onGoQuality }: { projectId: string; onGoQuality: () => void }) {
  const {
    getBindingByEntity,
    getProcessChainStatus,
    getProcessChainSummary,
    getProcessChainRecommend,
    getProcessChainDependencies,
    listTripRoleTrips,
    previewTrip,
    submitTrip,
    executeExecpeg,
    getExecpegStatus,
    getExecpegCallbacks,
    patchExecpegManualInput,
    registerExecpegTemplate,
    listExecpegHighwaySpus,
    getExecpegHighwaySpu,
    getProof,
    addProofAttachment,
    listProjectEntities,
    createProjectEntity,
    patchProjectEntity,
    createProjectDocument,
    createProjectDocumentVersion,
    checkDtoPermission,
    loading,
    error,
  } = useQCSpecDocPegApi()

  const [resolvedProjectId, setResolvedProjectId] = useState(projectId)
  const [resolvedChainId, setResolvedChainId] = useState('')
  const [currentStep, setCurrentStep] = useState('-')
  const [nextAction, setNextAction] = useState('-')
  const [chainState, setChainState] = useState('-')
  const [steps, setSteps] = useState<unknown[]>([])
  const [dependencies, setDependencies] = useState<unknown[]>([])
  const [trips, setTrips] = useState<unknown[]>([])
  const [hint, setHint] = useState('')
  const [permissionHint, setPermissionHint] = useState('')
  const [previewHint, setPreviewHint] = useState('')
  const [submitHint, setSubmitHint] = useState('')
  const [lastExecId, setLastExecId] = useState('')
  const [execHint, setExecHint] = useState('')
  const [callbackHint, setCallbackHint] = useState('')
  const [manualInputHint, setManualInputHint] = useState('')
  const [templateHint, setTemplateHint] = useState('')
  const [spuHint, setSpuHint] = useState('')
  const [entityHint, setEntityHint] = useState('')
  const [documentHint, setDocumentHint] = useState('')
  const [proofAttachmentHint, setProofAttachmentHint] = useState('')
  const [lastSpuRef, setLastSpuRef] = useState('')
  const [lastProofRef, setLastProofRef] = useState('')
  const [lastEntityId, setLastEntityId] = useState('')
  const [lastDocumentId, setLastDocumentId] = useState('')
  const [entityRows, setEntityRows] = useState<unknown[]>([])

  const resolveContext = useCallback(async () => {
    const context = readDocpegInspectionContext(projectId)
    const docpegProjectId = context.docpegProjectId.trim() || projectId
    const componentUri = context.docpegComponentUri.trim()
    const pileId = context.docpegPileId.trim()
    const action = String(context.docpegAction || '').trim() || 'qcspec_inspection_submit'
    const formCode = String(context.docpegFormCode || '').trim()
    let chainId = context.docpegChainId.trim()

    setResolvedProjectId(docpegProjectId)
    if (!chainId && componentUri) {
      const bindingRes = await getBindingByEntity(docpegProjectId, componentUri)
      chainId = pickStringDeep(bindingRes, ['chain_id', 'chainId'])
    }
    setResolvedChainId(chainId || '')

    return { docpegProjectId, componentUri, pileId, chainId, action, formCode }
  }, [getBindingByEntity, projectId])

  const buildTripPayload = useCallback((ctx: {
    docpegProjectId: string
    componentUri: string
    pileId: string
    chainId: string
    action: string
    formCode: string
  }) => {
    return {
      request_id: `qcspec-process-${Date.now()}`,
      project_id: ctx.docpegProjectId,
      chain_id: ctx.chainId,
      component_uri: ctx.componentUri || undefined,
      pile_id: ctx.pileId || undefined,
      inspection_location: ctx.pileId || undefined,
      action: ctx.action,
      payload: {
        source: 'qcspec_web_process_panel',
        form_code: ctx.formCode || undefined,
      },
    }
  }, [])

  const inferExecTripRole = useCallback((action: string): string => {
    const text = String(action || '').trim().toLowerCase()
    if (text.includes('participant') || text.includes('register')) return 'register_project_participants@v1.0'
    if (text.includes('spu') || text.includes('highway')) return 'highway_spu_creation@v1.0'
    return 'create_section@v1.0'
  }, [])

  const refresh = useCallback(async () => {
    const { docpegProjectId, componentUri, pileId, chainId } = await resolveContext()

    const tripsRes = await listTripRoleTrips(docpegProjectId, {
      chain_id: chainId || undefined,
      component_uri: componentUri || undefined,
      pile_id: pileId || undefined,
      limit: 20,
    })
    setTrips(pickArrayDeep(tripsRes, ['items', 'list', 'data', 'result']))

    if (!chainId) {
      setHint('未解析出 chainId。请在工序上下文中补充 chainId 或 component_uri 后重试。')
      setCurrentStep('-')
      setNextAction('-')
      setChainState('-')
      setSteps([])
      setDependencies([])
      return
    }

    const [statusRes, summaryRes, recommendRes, dependenciesRes] = await Promise.all([
      getProcessChainStatus(docpegProjectId, {
        chain_id: chainId,
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      getProcessChainSummary(docpegProjectId, chainId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      getProcessChainRecommend(docpegProjectId, {
        chain_id: chainId,
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      getProcessChainDependencies(docpegProjectId, { chain_id: chainId }),
    ])

    const statusSteps = pickArrayDeep(statusRes, ['steps', 'items', 'list'])
    const deps = pickArrayDeep(dependenciesRes, ['dependencies', 'items', 'list', 'data', 'result'])

    setCurrentStep(pickStringDeep(statusRes, ['current_step_name', 'current_step', 'step_id', 'step']) || '-')
    setChainState(pickStringDeep(statusRes, ['chain_state', 'status']) || '-')
    setNextAction(
      pickStringDeep(recommendRes, ['next_action', 'action', 'label']) ||
      pickStringDeep(summaryRes, ['next_action', 'action']) ||
      '-'
    )
    setSteps(statusSteps)
    setDependencies(deps)
    setHint('')
  }, [
    getBindingByEntity,
    getProcessChainDependencies,
    getProcessChainRecommend,
    getProcessChainStatus,
    getProcessChainSummary,
    listTripRoleTrips,
    resolveContext,
  ])

  const runPermissionCheck = useCallback(async () => {
    const { docpegProjectId } = await resolveContext()
    if (!docpegProjectId) {
      setPermissionHint('projectId 为空，无法判权')
      return
    }
    const res = await checkDtoPermission({
      permission: 'trip.execute',
      project_id: docpegProjectId,
    })
    const allowed = pickBooleanDeep(res, ['allowed', 'granted', 'permit'])
    const reason = pickStringDeep(res, ['reason', 'message', 'detail'])
    setPermissionHint(
      `${allowed === false ? 'DENY' : 'ALLOW'}${reason ? ` · ${reason}` : ''}`
    )
  }, [checkDtoPermission, resolveContext])

  const runTripPreview = useCallback(async () => {
    const ctx = await resolveContext()
    if (!ctx.chainId) {
      setPreviewHint('chainId 缺失，无法预演')
      return
    }
    const payload = buildTripPayload(ctx)
    const res = await previewTrip(payload)
    if (!res) {
      setPreviewHint('预演失败')
      return
    }
    const status = pickStringDeep(res, ['status', 'state']) || 'ok'
    const next = pickStringDeep(res, ['next_action', 'action', 'label'])
    setPreviewHint(`status=${status}${next ? ` | next=${next}` : ''}`)
  }, [buildTripPayload, previewTrip, resolveContext])

  const runTripSubmit = useCallback(async () => {
    const ctx = await resolveContext()
    if (!ctx.chainId) {
      setSubmitHint('chainId 缺失，无法提交')
      return
    }
    const payload = buildTripPayload(ctx)
    const res = await submitTrip(payload)
    if (!res) {
      setSubmitHint('提交失败')
      return
    }
    const status = pickStringDeep(res, ['status', 'state']) || 'ok'
    const tripId = pickStringDeep(res, ['trip_id', 'id']) || '-'
    const proofId = pickStringDeep(res, ['proof_id', 'trip_proof_id']) || '-'
    setSubmitHint(`status=${status} | trip=${tripId} | proof=${proofId}`)
    await refresh()
  }, [buildTripPayload, refresh, resolveContext, submitTrip])

  const runExecExecute = useCallback(async () => {
    const ctx = await resolveContext()
    const tripRoleId = inferExecTripRole(ctx.action)
    const projectRef = `v://cn.project/${ctx.docpegProjectId}`
    const componentRef = ctx.componentUri || `v://cn.project/${ctx.docpegProjectId}/component/${ctx.pileId || 'default'}`

    const res = await executeExecpeg({
      tripRoleId,
      projectRef,
      componentRef,
      context: {
        autoData: {},
        manualInput: {
          source: 'qcspec_web_process_panel',
          chain_id: ctx.chainId || undefined,
          pile_id: ctx.pileId || undefined,
          form_code: ctx.formCode || undefined,
          action: ctx.action,
        },
      },
    })
    if (!res) {
      setExecHint('ExecPeg 执行失败')
      return
    }
    const execId = pickStringDeep(res, ['execId', 'exec_id'])
    const status = pickStringDeep(res, ['status', 'state']) || '-'
    const proof = pickStringDeep(res, ['proofId', 'proof_id'])
    setLastExecId(execId)
    setExecHint(`status=${status} | exec=${execId || '-'} | proof=${proof || '-'}`)
  }, [executeExecpeg, inferExecTripRole, resolveContext])

  const runExecStatus = useCallback(async () => {
    if (!lastExecId) {
      setExecHint('请先执行 ExecPeg，拿到 execId')
      return
    }
    const res = await getExecpegStatus(lastExecId)
    if (!res) {
      setExecHint('状态查询失败')
      return
    }
    const root = asRecord(res)
    const execution = asRecord(root.execution || root.exec)
    const status = pickStringDeep(execution, ['status', 'state']) || pickStringDeep(res, ['status', 'state']) || '-'
    const proof = (
      pickStringDeep(execution, ['proofId', 'proof_id']) ||
      pickStringDeep(asRecord(execution.proof), ['proofId', 'proof_id']) ||
      pickStringDeep(res, ['proofId', 'proof_id'])
    )
    setExecHint(`status=${status} | exec=${lastExecId} | proof=${proof || '-'}`)
  }, [getExecpegStatus, lastExecId])

  const runExecCallbacks = useCallback(async () => {
    if (!lastExecId) {
      setCallbackHint('请先执行 ExecPeg，拿到 execId')
      return
    }
    const res = await getExecpegCallbacks(lastExecId, { limit: 20, offset: 0 })
    const total = Number(pickNumberDeep(res, ['total']) || 0)
    const first = pickArrayDeep(res, ['items', 'list', 'data', 'result'])[0]
    const firstStatus = pickStringDeep(first, ['status']) || '-'
    const firstCode = String(pickNumberDeep(first, ['responseStatus', 'httpStatus']) ?? '-')
    setCallbackHint(`callbacks=${total} | latest=${firstStatus} | http=${firstCode}`)
  }, [getExecpegCallbacks, lastExecId])

  const runExecManualInput = useCallback(async () => {
    if (!lastExecId) {
      setManualInputHint('请先执行 ExecPeg，拿到 execId')
      return
    }
    const res = await patchExecpegManualInput({
      execId: lastExecId,
      manualInput: {
        remarks: 'qcspec web process panel manual patch',
      },
    })
    if (!res) {
      setManualInputHint('手工补录失败')
      return
    }
    const updated = pickStringDeep(res, ['updatedAt', 'updated_at']) || '-'
    setManualInputHint(`exec=${lastExecId} | updated=${updated}`)
  }, [lastExecId, patchExecpegManualInput])

  const runRegisterTemplate = useCallback(async () => {
    const ctx = await resolveContext()
    const tripRoleId = inferExecTripRole(ctx.action)
    const res = await registerExecpegTemplate({
      tripRoleId,
      displayName: 'QCSpec 工序联调模板',
      schema: {},
      gate: {},
      actions: [],
    })
    if (!res) {
      setTemplateHint('模板注册失败')
      return
    }
    const outId = pickStringDeep(res, ['tripRoleId', 'trip_role_id']) || tripRoleId
    const version = pickStringDeep(res, ['version']) || '-'
    setTemplateHint(`tripRole=${outId} | version=${version}`)
  }, [inferExecTripRole, registerExecpegTemplate, resolveContext])

  const runListSpus = useCallback(async () => {
    const res = await listExecpegHighwaySpus({ q: resolvedProjectId, limit: 20, offset: 0 })
    const items = pickArrayDeep(res, ['items', 'list', 'data', 'result'])
    const first = items[0]
    const spuRef = pickStringDeep(first, ['spu_ref', 'spuRef'])
    const total = Number(pickNumberDeep(res, ['total']) || items.length)
    if (spuRef) setLastSpuRef(spuRef)
    setSpuHint(`SPU total=${total} | first=${spuRef || '-'}`)
  }, [listExecpegHighwaySpus, resolvedProjectId])

  const runGetSpu = useCallback(async () => {
    if (!lastSpuRef) {
      setSpuHint('请先查询 SPU 列表')
      return
    }
    const res = await getExecpegHighwaySpu(lastSpuRef)
    if (!res) {
      setSpuHint(`SPU 详情失败：${lastSpuRef}`)
      return
    }
    const root = asRecord(res)
    const spu = asRecord(root.spu)
    const name = pickStringDeep(spu, ['highway_name']) || pickStringDeep(res, ['highway_name']) || '-'
    const code = pickStringDeep(spu, ['highway_code']) || pickStringDeep(res, ['highway_code']) || '-'
    setSpuHint(`SPU detail: ${code} / ${name} / ${lastSpuRef}`)
  }, [getExecpegHighwaySpu, lastSpuRef])

  const runListEntities = useCallback(async () => {
    const ctx = await resolveContext()
    const res = await listProjectEntities(ctx.docpegProjectId, {
      search: ctx.pileId || undefined,
    })
    const items = pickArrayDeep(res, ['items', 'list', 'data', 'result'])
    setEntityRows(items)
    const first = items[0]
    const entityId = pickStringDeep(first, ['id', 'entity_id'])
    if (entityId) setLastEntityId(entityId)
    setEntityHint(`entities=${items.length} | first=${entityId || '-'}`)
  }, [listProjectEntities, resolveContext])

  const runCreateEntity = useCallback(async () => {
    const ctx = await resolveContext()
    const codeSeed = (ctx.pileId || 'AUTO').replace(/[^a-zA-Z0-9-]/g, '').slice(0, 20) || 'AUTO'
    const payload = {
      entity_code: `QCS-${codeSeed}-${Date.now().toString().slice(-4)}`,
      entity_name: `联调实体-${codeSeed}`,
      entity_type: 'subitem',
      parent_uri: undefined,
      location_chain: ctx.pileId || undefined,
      chain_id: ctx.chainId || undefined,
    }
    const res = await createProjectEntity(ctx.docpegProjectId, payload)
    if (!res) {
      setEntityHint('创建实体失败')
      return
    }
    const entity = asRecord(asRecord(res).entity)
    const entityId = pickStringDeep(entity, ['id', 'entity_id']) || pickStringDeep(res, ['id', 'entity_id'])
    const entityCode = pickStringDeep(entity, ['entity_code', 'code']) || payload.entity_code
    if (entityId) setLastEntityId(entityId)
    setEntityHint(`create entity: id=${entityId || '-'} | code=${entityCode}`)
    await runListEntities()
  }, [createProjectEntity, resolveContext, runListEntities])

  const runPatchEntity = useCallback(async () => {
    const ctx = await resolveContext()
    const entityId = lastEntityId || pickStringDeep(entityRows[0], ['id', 'entity_id'])
    if (!entityId) {
      setEntityHint('请先查询或创建实体')
      return
    }
    const res = await patchProjectEntity(ctx.docpegProjectId, entityId, {
      entity_name: `联调实体-更新-${Date.now().toString().slice(-4)}`,
      chain_id: ctx.chainId || undefined,
    })
    if (!res) {
      setEntityHint(`更新实体失败：${entityId}`)
      return
    }
    const updated = pickStringDeep(asRecord(asRecord(res).entity), ['updated_at']) || pickStringDeep(res, ['updated_at']) || '-'
    setEntityHint(`patch entity: id=${entityId} | updated=${updated}`)
    await runListEntities()
  }, [entityRows, lastEntityId, patchProjectEntity, resolveContext, runListEntities])

  const runGetProof = useCallback(async () => {
    const proofId =
      lastProofRef ||
      pickStringDeep(trips[0], ['proof_id', 'trip_proof_id'])
    if (!proofId) {
      setProofAttachmentHint('暂无可查询的 proof_id，请先提交 Trip')
      return
    }
    const res = await getProof(proofId)
    if (!res) {
      setProofAttachmentHint(`proof 查询失败：${proofId}`)
      return
    }
    const root = asRecord(res)
    const proof = asRecord(root.proof)
    const hash = pickStringDeep(proof, ['hash']) || pickStringDeep(res, ['hash']) || '-'
    const signatures = Array.isArray(proof.signatures)
      ? proof.signatures.length
      : Number(pickNumberDeep(res, ['signatures']) || 0)
    setLastProofRef(proofId)
    setProofAttachmentHint(`proof=${proofId} | hash=${hash} | signatures=${signatures}`)
  }, [getProof, lastProofRef, trips])

  const runAttachProof = useCallback(async () => {
    const proofId =
      lastProofRef ||
      pickStringDeep(trips[0], ['proof_id', 'trip_proof_id'])
    if (!proofId) {
      setProofAttachmentHint('暂无可绑定的 proof_id，请先提交 Trip')
      return
    }
    const res = await addProofAttachment(proofId, {
      file_ids: ['FILE-DEMO-001'],
    })
    if (!res) {
      setProofAttachmentHint(`proof 附件绑定失败：${proofId}`)
      return
    }
    const attached = pickArrayDeep(res, ['attached', 'items'])
    setLastProofRef(proofId)
    setProofAttachmentHint(`attach proof: ${proofId} | attached=${attached.length}`)
  }, [addProofAttachment, lastProofRef, trips])

  const runCreateDocument = useCallback(async () => {
    const ctx = await resolveContext()
    const res = await createProjectDocument(ctx.docpegProjectId, {
      name: `项目合同（联调）-${Date.now().toString().slice(-4)}`,
      category: 'contract',
      doc_type: 'project_contract',
      meta: {
        source: 'qcspec_web_process_panel',
      },
    })
    if (!res) {
      setDocumentHint('创建文档失败')
      return
    }
    const doc = asRecord(asRecord(res).document)
    const documentId = pickStringDeep(doc, ['id', 'document_id']) || pickStringDeep(res, ['id', 'document_id'])
    const status = pickStringDeep(doc, ['status']) || '-'
    if (documentId) setLastDocumentId(documentId)
    setDocumentHint(`create document: id=${documentId || '-'} | status=${status}`)
  }, [createProjectDocument, resolveContext])

  const runCreateDocumentVersion = useCallback(async () => {
    const ctx = await resolveContext()
    if (!lastDocumentId) {
      setDocumentHint('请先创建 document')
      return
    }
    const res = await createProjectDocumentVersion(ctx.docpegProjectId, lastDocumentId, {
      version_no: 'v1.0',
      note: 'qcspec web debug version',
      file_ids: ['FILE-DEMO-001'],
    })
    if (!res) {
      setDocumentHint(`创建版本失败：${lastDocumentId}`)
      return
    }
    const ver = asRecord(asRecord(res).version)
    const versionId = pickStringDeep(ver, ['id']) || '-'
    const versionNo = pickStringDeep(ver, ['version_no']) || '-'
    setDocumentHint(`create version: document=${lastDocumentId} | id=${versionId} | no=${versionNo}`)
  }, [createProjectDocumentVersion, lastDocumentId, resolveContext])

  const runAdvance = useCallback(async () => {
    await runPermissionCheck()
    await runTripPreview()
    await runTripSubmit()
  }, [runPermissionCheck, runTripPreview, runTripSubmit])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <Card title="工序推进（Process）" icon="🔧">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
        <MetricCard label="projectId" value={resolvedProjectId} color="#1E3A8A" />
        <MetricCard label="chainId" value={resolvedChainId || '未绑定'} color="#0F766E" />
        <MetricCard label="chainState" value={chainState} color="#7C3AED" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <MetricCard label="currentStep" value={currentStep} color="#1D4ED8" />
        <MetricCard label="nextAction" value={nextAction} color="#047857" />
      </div>

      {hint && (
        <div
          style={{
            fontSize: 12,
            color: '#92400E',
            background: '#FFFBEB',
            border: '1px solid #FDE68A',
            borderRadius: 8,
            padding: '8px 10px',
            marginBottom: 10,
          }}
        >
          {hint}
        </div>
      )}

      <div
        style={{
          marginBottom: 10,
          padding: 10,
          borderRadius: 8,
          border: '1px solid #DBEAFE',
          background: '#F8FBFF',
        }}
      >
        <SectionTitle text="联调工具（工序页）" />
        <div style={{ fontSize: 12, color: '#334155', marginBottom: 8 }}>
          质检页已不再承载联调操作。联调动作统一收敛到工序页执行。
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button size="sm" variant="secondary" onClick={() => { void runPermissionCheck() }} disabled={loading}>
            判权检查
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runTripPreview() }} disabled={loading}>
            Trip 预演
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runTripSubmit() }} disabled={loading}>
            Trip 提交
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runExecExecute() }} disabled={loading}>
            Exec 执行
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runExecStatus() }} disabled={loading || !lastExecId}>
            Exec 状态
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runExecCallbacks() }} disabled={loading || !lastExecId}>
            回调日志
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runExecManualInput() }} disabled={loading || !lastExecId}>
            手工补录
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runRegisterTemplate() }} disabled={loading}>
            注册模板
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runListSpus() }} disabled={loading}>
            SPU 列表
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runGetSpu() }} disabled={loading || !lastSpuRef}>
            SPU 详情
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runListEntities() }} disabled={loading}>
            实体列表
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runCreateEntity() }} disabled={loading}>
            创建实体
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runPatchEntity() }} disabled={loading}>
            更新实体
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runGetProof() }} disabled={loading}>
            Proof 查询
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runAttachProof() }} disabled={loading}>
            Proof 附件
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runCreateDocument() }} disabled={loading}>
            创建文档
          </Button>
          <Button size="sm" variant="secondary" onClick={() => { void runCreateDocumentVersion() }} disabled={loading || !lastDocumentId}>
            创建版本
          </Button>
          <Button size="sm" onClick={() => { void runAdvance() }} disabled={loading}>
            一键推进
          </Button>
        </div>
        {(permissionHint || previewHint || submitHint || execHint || callbackHint || manualInputHint || templateHint || spuHint || entityHint || documentHint || proofAttachmentHint) && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#0F766E', lineHeight: 1.6 }}>
            {permissionHint && <div>判权：{permissionHint}</div>}
            {previewHint && <div>预演：{previewHint}</div>}
            {submitHint && <div>提交：{submitHint}</div>}
            {execHint && <div>执行体：{execHint}</div>}
            {callbackHint && <div>回调：{callbackHint}</div>}
            {manualInputHint && <div>补录：{manualInputHint}</div>}
            {templateHint && <div>模板：{templateHint}</div>}
            {spuHint && <div>SPU：{spuHint}</div>}
            {entityHint && <div>实体：{entityHint}</div>}
            {documentHint && <div>文档：{documentHint}</div>}
            {proofAttachmentHint && <div>Proof：{proofAttachmentHint}</div>}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 10 }}>
        <SectionTitle text={`步骤列表（${steps.length}）`} />
        {steps.length === 0 ? (
          <EmptyText text="暂无步骤数据" />
        ) : (
          <SimpleTable
            headers={['step', 'name', 'status', 'latest_instance']}
            rows={steps.slice(0, 10).map((item) => {
              const row = asRecord(item)
              const latest = asRecord(row.latest_instance)
              return [
                pickStringDeep(row, ['step_id', 'id', 'step']) || '-',
                pickStringDeep(row, ['name', 'label']) || '-',
                pickStringDeep(row, ['status', 'state']) || '-',
                pickStringDeep(latest, ['instance_id', 'id']) || '-',
              ]
            })}
          />
        )}
      </div>

      <div style={{ marginBottom: 10 }}>
        <SectionTitle text={`依赖关系（${dependencies.length}）`} />
        {dependencies.length === 0 ? (
          <EmptyText text="暂无依赖数据" />
        ) : (
          <SimpleTable
            headers={['from', 'to', 'status']}
            rows={dependencies.slice(0, 10).map((item) => {
              const row = asRecord(item)
              return [
                pickStringDeep(row, ['from_step', 'from', 'source', 'step_id']) || '-',
                pickStringDeep(row, ['to_step', 'to', 'target']) || '-',
                pickStringDeep(row, ['status', 'state']) || '-',
              ]
            })}
          />
        )}
      </div>

      <div style={{ marginBottom: 10 }}>
        <SectionTitle text={`Trip 记录（${trips.length}）`} />
        {trips.length === 0 ? (
          <EmptyText text="暂无 Trip 记录" />
        ) : (
          <SimpleTable
            headers={['trip_id', 'action', 'status', 'proof']}
            rows={trips.slice(0, 10).map((item) => {
              const row = asRecord(item)
              return [
                pickStringDeep(row, ['trip_id', 'id']) || '-',
                pickStringDeep(row, ['action', 'trip_type']) || '-',
                pickStringDeep(row, ['status', 'state']) || '-',
                pickStringDeep(row, ['proof_id', 'trip_proof_id']) || '-',
              ]
            })}
          />
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Button onClick={() => { void refresh() }} disabled={loading}>
          {loading ? '刷新中...' : '刷新工序状态'}
        </Button>
        <Button variant="secondary" onClick={onGoQuality}>去质检录入</Button>
        {error && <span style={{ fontSize: 12, color: '#DC2626' }}>{error}</span>}
      </div>
    </Card>
  )
}

function MeasurementPanel({ projectId }: { projectId: string }) {
  const {
    getBoqItems,
    getBoqUtxos,
    getLayerpegChainStatus,
    listTripRoleTrips,
    loading,
    error,
  } = useQCSpecDocPegApi()

  const [boqItems, setBoqItems] = useState<unknown[]>([])
  const [utxos, setUtxos] = useState<unknown[]>([])
  const [tripCount, setTripCount] = useState(0)
  const [chainHint, setChainHint] = useState('-')

  const refresh = useCallback(async () => {
    const context = readDocpegInspectionContext(projectId)
    const docpegProjectId = context.docpegProjectId.trim() || projectId
    const componentUri = context.docpegComponentUri.trim()
    const pileId = context.docpegPileId.trim()

    const [itemsRes, utxosRes, tripsRes, chainRes] = await Promise.all([
      getBoqItems(docpegProjectId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      getBoqUtxos(docpegProjectId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      listTripRoleTrips(docpegProjectId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
        limit: 20,
      }),
      getLayerpegChainStatus(docpegProjectId),
    ])

    const mode = pickStringDeep(chainRes, ['mode'])
    const reason = pickStringDeep(chainRes, ['reason'])
    setChainHint([mode, reason].filter(Boolean).join(' / ') || '-')
    setBoqItems(pickArrayDeep(itemsRes, ['items', 'list', 'data', 'result']))
    setUtxos(pickArrayDeep(utxosRes, ['items', 'list', 'data', 'result']))
    setTripCount(pickArrayDeep(tripsRes, ['items', 'list', 'data', 'result']).length)
  }, [getBoqItems, getBoqUtxos, getLayerpegChainStatus, listTripRoleTrips, projectId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <Card title="计量守恒（Measurement）" icon="🧮">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
        <MetricCard label="BOQ Items" value={String(boqItems.length)} color="#1E3A8A" />
        <MetricCard label="UTXO" value={String(utxos.length)} color="#0F766E" />
        <MetricCard label="Trip Records" value={String(tripCount)} color="#7C3AED" />
      </div>
      <div style={{ marginBottom: 10 }}>
        <MetricCard label="Chain Status" value={chainHint} color="#334155" />
      </div>

      <div style={{ marginBottom: 10 }}>
        <SectionTitle text={`BOQ 明细（${boqItems.length}）`} />
        {boqItems.length === 0 ? (
          <EmptyText text="暂无 BOQ 数据" />
        ) : (
          <SimpleTable
            headers={['item_code', 'name', 'design_qty', 'remaining', 'status']}
            rows={boqItems.slice(0, 10).map((item) => {
              const row = asRecord(item)
              return [
                pickStringDeep(row, ['item_code', 'code', 'id']) || '-',
                pickStringDeep(row, ['material_name', 'name', 'description']) || '-',
                String(pickNumberDeep(row, ['design_qty', 'qty', 'planned']) ?? '-'),
                String(pickNumberDeep(row, ['remaining', 'remaining_qty', 'balance']) ?? '-'),
                pickStringDeep(row, ['status', 'conservation_status']) || '-',
              ]
            })}
          />
        )}
      </div>

      <div style={{ marginBottom: 10 }}>
        <SectionTitle text={`UTXO 明细（${utxos.length}）`} />
        {utxos.length === 0 ? (
          <EmptyText text="暂无 UTXO 数据" />
        ) : (
          <SimpleTable
            headers={['utxo_id', 'code', 'qty', 'status', 'linked_v']}
            rows={utxos.slice(0, 10).map((item) => {
              const row = asRecord(item)
              return [
                pickStringDeep(row, ['utxo_id', 'id']) || '-',
                pickStringDeep(row, ['code', 'item_code']) || '-',
                String(pickNumberDeep(row, ['qty', 'quantity', 'amount']) ?? '-'),
                pickStringDeep(row, ['status', 'state']) || '-',
                pickStringDeep(row, ['linked_v', 'linked_uri', 'entity_uri']) || '-',
              ]
            })}
          />
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Button onClick={() => { void refresh() }} disabled={loading}>
          {loading ? '刷新中...' : '刷新守恒数据'}
        </Button>
        {error && <span style={{ fontSize: 12, color: '#DC2626' }}>{error}</span>}
      </div>
    </Card>
  )
}

function SettlementPanel({
  projectId,
  qualityStats,
  latestProofId,
}: {
  projectId: string
  qualityStats: StatSnapshot
  latestProofId: string
}) {
  const {
    getBoqItems,
    getBoqUtxos,
    listTripRoleTrips,
    getSignStatus,
    previewTripRole,
    submitTripRole,
    consumeBoqItem,
    settleBoqItem,
    loading,
    error,
  } = useQCSpecDocPegApi()

  const [boqItems, setBoqItems] = useState<unknown[]>([])
  const [utxos, setUtxos] = useState<unknown[]>([])
  const [proofHint, setProofHint] = useState('-')
  const [signNext, setSignNext] = useState('-')
  const [signBlocked, setSignBlocked] = useState('-')
  const [previewHint, setPreviewHint] = useState('')
  const [submitHint, setSubmitHint] = useState('')
  const [boqTxHint, setBoqTxHint] = useState('')

  const buildSettlementPayload = useCallback(() => {
    const context = readDocpegInspectionContext(projectId)
    const docpegProjectId = context.docpegProjectId.trim() || projectId
    const componentUri = context.docpegComponentUri.trim()
    const pileId = context.docpegPileId.trim()
    const chainId = context.docpegChainId.trim()
    return {
      project_id: docpegProjectId,
      chain_id: chainId || undefined,
      component_uri: componentUri || undefined,
      pile_id: pileId || undefined,
      trip_type: 'settlement_apply',
      action: 'settlement_apply',
      payload: {
        source: 'qcspec_web_settlement_panel',
        quality_pass_count: qualityStats.pass,
        quality_fail_count: qualityStats.fail,
        boq_count: boqItems.length,
        utxo_count: utxos.length,
        latest_proof_id: proofHint !== '-' ? proofHint : undefined,
        applied_at: new Date().toISOString(),
      },
    }
  }, [boqItems.length, proofHint, projectId, qualityStats.fail, qualityStats.pass, utxos.length])

  const refresh = useCallback(async () => {
    const context = readDocpegInspectionContext(projectId)
    const docpegProjectId = context.docpegProjectId.trim() || projectId
    const componentUri = context.docpegComponentUri.trim()
    const pileId = context.docpegPileId.trim()
    const chainId = context.docpegChainId.trim()

    const [itemsRes, utxosRes, tripsRes] = await Promise.all([
      getBoqItems(docpegProjectId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      getBoqUtxos(docpegProjectId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
      }),
      listTripRoleTrips(docpegProjectId, {
        chain_id: chainId || undefined,
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
        limit: 20,
      }),
    ])

    const itemList = pickArrayDeep(itemsRes, ['items', 'list', 'data', 'result'])
    const utxoList = pickArrayDeep(utxosRes, ['items', 'list', 'data', 'result'])
    const tripList = pickArrayDeep(tripsRes, ['items', 'list', 'data', 'result'])

    setBoqItems(itemList)
    setUtxos(utxoList)

    const nextProof = latestProofId || pickStringDeep(tripList[0], ['proof_id', 'trip_proof_id']) || '-'
    setProofHint(nextProof)

    const docId = pickStringDeep(tripList[0], ['doc_id', 'docId'])
    if (!docId) {
      setSignNext('-')
      setSignBlocked('-')
      return
    }
    const signRes = await getSignStatus(docId)
    setSignNext(pickStringDeep(signRes, ['next_required']) || '-')
    setSignBlocked(pickStringDeep(signRes, ['blocked_reason']) || '-')
  }, [getBoqItems, getBoqUtxos, getSignStatus, latestProofId, listTripRoleTrips, projectId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const totalRemaining = useMemo(() => {
    return boqItems.reduce<number>(
      (sum, item) => sum + (pickNumberDeep(item, ['remaining', 'remaining_qty', 'balance']) || 0),
      0
    )
  }, [boqItems])

  const totalDesign = useMemo(() => {
    return boqItems.reduce<number>(
      (sum, item) => sum + (pickNumberDeep(item, ['design_qty', 'qty', 'planned']) || 0),
      0
    )
  }, [boqItems])

  const qualityReady = qualityStats.pass > 0
  const measurementReady = boqItems.length > 0
  const auditReady = proofHint !== '-' && (signBlocked === '-' || !signBlocked)
  const settlementReady = qualityReady && measurementReady && auditReady

  const previewSettlement = async () => {
    const res = await previewTripRole(buildSettlementPayload())
    const status = pickStringDeep(res, ['status', 'decision', 'result']) || 'preview done'
    const msg = pickStringDeep(res, ['message', 'detail']) || '-'
    setPreviewHint(`${status}${msg !== '-' ? ` | ${msg}` : ''}`)
  }

  const submitSettlement = async () => {
    if (!settlementReady) {
      setSubmitHint('当前未满足结算前置条件，暂不能提交结算申请。')
      return
    }
    const res = await submitTripRole(buildSettlementPayload())
    const tripId = pickStringDeep(res, ['trip_id', 'id'])
    const proofId = pickStringDeep(res, ['proof_id', 'trip_proof_id'])
    const status = pickStringDeep(res, ['status', 'state']) || 'submitted'
    setSubmitHint(`status=${status} | trip=${tripId || '-'} | proof=${proofId || '-'}`)
    void refresh()
  }

  const submitBoqConsume = async () => {
    const context = readDocpegInspectionContext(projectId)
    const docpegProjectId = context.docpegProjectId.trim() || projectId
    const firstItem = boqItems.find((item) => Boolean(pickStringDeep(item, ['boq_item_ref', 'item_ref', 'code'])))
    const boqRef = pickStringDeep(firstItem, ['boq_item_ref', 'item_ref', 'code'])
    if (!boqRef) {
      setBoqTxHint('consume: 未找到可用 boq_item_ref')
      return
    }
    const qtyRemaining = pickNumberDeep(firstItem, ['qty_remaining', 'remaining_qty', 'remaining'])
    const qty = qtyRemaining && qtyRemaining > 0 ? Math.min(qtyRemaining, 1) : 1
    const res = await consumeBoqItem(docpegProjectId, {
      boq_item_ref: boqRef,
      trip_id: `TRIP-QCSPEC-${Date.now()}`,
      qty,
    })
    if (!res) {
      setBoqTxHint(`consume: 调用失败 (${boqRef})`)
      return
    }
    const actual = pickNumberDeep(res, ['qty_actual'])
    const remain = pickNumberDeep(res, ['qty_remaining'])
    setBoqTxHint(`consume: ref=${boqRef} | actual=${actual ?? '-'} | remain=${remain ?? '-'}`)
    void refresh()
  }

  const submitBoqSettle = async () => {
    const context = readDocpegInspectionContext(projectId)
    const docpegProjectId = context.docpegProjectId.trim() || projectId
    const firstItem = boqItems.find((item) => Boolean(pickStringDeep(item, ['boq_item_ref', 'item_ref', 'code'])))
    const boqRef = pickStringDeep(firstItem, ['boq_item_ref', 'item_ref', 'code'])
    if (!boqRef) {
      setBoqTxHint('settle: 未找到可用 boq_item_ref')
      return
    }
    const proofId = latestProofId || (proofHint !== '-' ? proofHint : '')
    const amount = pickNumberDeep(firstItem, ['qty_actual', 'qty_design', 'qty']) || 1
    const res = await settleBoqItem(docpegProjectId, {
      boq_item_ref: boqRef,
      amount,
      proof_id: proofId || undefined,
    })
    if (!res) {
      setBoqTxHint(`settle: 调用失败 (${boqRef})`)
      return
    }
    const settlementId = pickStringDeep(res, ['settlement_id', 'id']) || '-'
    const status = pickStringDeep(res, ['status', 'state']) || '-'
    setBoqTxHint(`settle: ref=${boqRef} | settlement=${settlementId} | status=${status}`)
    void refresh()
  }

  return (
    <Card title="结算准备（Settlement）" icon="💰">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
        <MetricCard label="质检合格数" value={String(qualityStats.pass)} color={qualityReady ? '#15803D' : '#B45309'} />
        <MetricCard label="BOQ 条目" value={String(boqItems.length)} color={measurementReady ? '#1D4ED8' : '#64748B'} />
        <MetricCard label="可结算状态" value={settlementReady ? 'READY' : 'PENDING'} color={settlementReady ? '#15803D' : '#B45309'} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <MetricCard label="设计总量" value={String(Number(totalDesign.toFixed(3)))} color="#0F766E" />
        <MetricCard label="剩余总量" value={String(Number(totalRemaining.toFixed(3)))} color="#7C3AED" />
      </div>

      <div style={{ marginBottom: 10 }}>
        <SectionTitle text="结算前置条件" />
        <SimpleTable
          headers={['条件', '状态', '说明']}
          rows={[
            ['质检通过', qualityReady ? '✅ 已满足' : '⏳ 未满足', `合格 ${qualityStats.pass} / 不合格 ${qualityStats.fail}`],
            ['计量守恒可读', measurementReady ? '✅ 已满足' : '⏳ 未满足', `BOQ ${boqItems.length} / UTXO ${utxos.length}`],
            ['审计签章无阻塞', auditReady ? '✅ 已满足' : '⚠ 待处理', `proof=${proofHint} / next=${signNext} / blocked=${signBlocked}`],
          ]}
        />
      </div>

      <div style={{ marginBottom: 10 }}>
        <SectionTitle text={`UTXO 快照（${Math.min(utxos.length, 10)}）`} />
        {utxos.length === 0 ? (
          <EmptyText text="暂无可用于结算参考的 UTXO 数据" />
        ) : (
          <SimpleTable
            headers={['utxo_id', 'code', 'qty', 'status']}
            rows={utxos.slice(0, 10).map((item) => {
              const row = asRecord(item)
              return [
                pickStringDeep(row, ['utxo_id', 'id']) || '-',
                pickStringDeep(row, ['code', 'item_code']) || '-',
                String(pickNumberDeep(row, ['qty', 'quantity', 'amount']) ?? '-'),
                pickStringDeep(row, ['status', 'state']) || '-',
              ]
            })}
          />
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Button onClick={() => { void refresh() }} disabled={loading}>
          {loading ? '刷新中...' : '刷新结算准备'}
        </Button>
        <Button variant="secondary" onClick={previewSettlement} disabled={loading}>
          预演结算申请
        </Button>
        <Button onClick={submitSettlement} disabled={loading || !settlementReady}>
          提交结算申请
        </Button>
        <Button variant="secondary" onClick={submitBoqConsume} disabled={loading || boqItems.length === 0}>
          BOQ Consume
        </Button>
        <Button variant="secondary" onClick={submitBoqSettle} disabled={loading || boqItems.length === 0}>
          BOQ Settle
        </Button>
        {error && <span style={{ fontSize: 12, color: '#DC2626' }}>{error}</span>}
      </div>

      {(previewHint || submitHint || boqTxHint) && (
        <div style={{ marginTop: 10, fontSize: 12, color: '#475569', lineHeight: 1.7 }}>
          {previewHint ? <div>Preview: {previewHint}</div> : null}
          {submitHint ? <div>Submit: {submitHint}</div> : null}
          {boqTxHint ? <div>BOQ: {boqTxHint}</div> : null}
        </div>
      )}
    </Card>
  )
}

function AuditPanel({ projectId, latestProofId }: { projectId: string; latestProofId: string }) {
  const {
    getLayerpegAnchor,
    listTripRoleTrips,
    getSignStatus,
    loading,
    error,
  } = useQCSpecDocPegApi()

  const [anchors, setAnchors] = useState<unknown[]>([])
  const [trips, setTrips] = useState<unknown[]>([])
  const [signDocId, setSignDocId] = useState('')
  const [signNext, setSignNext] = useState('-')
  const [signBlocked, setSignBlocked] = useState('-')

  const refresh = useCallback(async () => {
    const context = readDocpegInspectionContext(projectId)
    const docpegProjectId = context.docpegProjectId.trim() || projectId
    const componentUri = context.docpegComponentUri.trim()
    const pileId = context.docpegPileId.trim()

    const [anchorsRes, tripsRes] = await Promise.all([
      componentUri ? getLayerpegAnchor(docpegProjectId, componentUri) : Promise.resolve(null),
      listTripRoleTrips(docpegProjectId, {
        component_uri: componentUri || undefined,
        pile_id: pileId || undefined,
        limit: 20,
      }),
    ])

    const anchorItems = pickArrayDeep(anchorsRes, ['items', 'list', 'data', 'result'])
    const tripItems = pickArrayDeep(tripsRes, ['items', 'list', 'data', 'result'])
    setAnchors(anchorItems)
    setTrips(tripItems)

    const firstTripDocId = tripItems
      .map((item) => pickStringDeep(item, ['doc_id', 'docId']))
      .find((text) => text) || ''

    if (!firstTripDocId) {
      setSignDocId('')
      setSignNext('-')
      setSignBlocked('-')
      return
    }

    setSignDocId(firstTripDocId)
    const signRes = await getSignStatus(firstTripDocId)
    setSignNext(pickStringDeep(signRes, ['next_required']) || '-')
    setSignBlocked(pickStringDeep(signRes, ['blocked_reason']) || '-')
  }, [getLayerpegAnchor, getSignStatus, listTripRoleTrips, projectId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <Card title="审计追溯（Audit）" icon="🔍">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
        <MetricCard label="Latest Proof" value={latestProofId || '-'} color="#1E3A8A" />
        <MetricCard label="Anchors" value={String(anchors.length)} color="#0F766E" />
        <MetricCard label="Trips" value={String(trips.length)} color="#7C3AED" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
        <MetricCard label="Sign docId" value={signDocId || '-'} color="#334155" />
        <MetricCard label="next_required" value={signNext} color="#1D4ED8" />
        <MetricCard label="blocked_reason" value={signBlocked} color="#B45309" />
      </div>
      <div style={{ marginBottom: 10 }}>
        <SectionTitle text={`Anchor 明细（${anchors.length}）`} />
        {anchors.length === 0 ? (
          <EmptyText text="暂无 Anchor 数据" />
        ) : (
          <SimpleTable
            headers={['anchor_id', 'entity_uri', 'hash', 'created_at']}
            rows={anchors.slice(0, 10).map((item) => {
              const row = asRecord(item)
              return [
                pickStringDeep(row, ['id', 'anchor_id']) || '-',
                pickStringDeep(row, ['entity_uri']) || '-',
                pickStringDeep(row, ['hash']) || '-',
                pickStringDeep(row, ['created_at', 'updated_at']) || '-',
              ]
            })}
          />
        )}
      </div>

      <div style={{ marginBottom: 10 }}>
        <SectionTitle text={`Trip 审计（${trips.length}）`} />
        {trips.length === 0 ? (
          <EmptyText text="暂无 Trip 审计记录" />
        ) : (
          <SimpleTable
            headers={['trip_id', 'doc_id', 'proof_id', 'status']}
            rows={trips.slice(0, 10).map((item) => {
              const row = asRecord(item)
              return [
                pickStringDeep(row, ['trip_id', 'id']) || '-',
                pickStringDeep(row, ['doc_id', 'docId']) || '-',
                pickStringDeep(row, ['proof_id', 'trip_proof_id']) || '-',
                pickStringDeep(row, ['status', 'state']) || '-',
              ]
            })}
          />
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Button onClick={() => { void refresh() }} disabled={loading}>
          {loading ? '刷新中...' : '刷新审计数据'}
        </Button>
        {error && <span style={{ fontSize: 12, color: '#DC2626' }}>{error}</span>}
      </div>
    </Card>
  )
}

function SectionTitle({ text }: { text: string }) {
  return (
    <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 6 }}>
      {text}
    </div>
  )
}

function EmptyText({ text }: { text: string }) {
  return (
    <div style={{ fontSize: 12, color: '#94A3B8', padding: '8px 0' }}>
      {text}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ border: '1px solid #E2E8F0', borderRadius: 10, padding: '10px 12px', background: '#fff' }}>
      <div style={{ fontSize: 12, color: '#64748B' }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 800, color, marginTop: 4, wordBreak: 'break-word' }}>{value}</div>
    </div>
  )
}

function SimpleTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div style={{ overflowX: 'auto', border: '1px solid #E2E8F0', borderRadius: 8 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: '#F8FAFC' }}>
            {headers.map((header) => (
              <th
                key={header}
                style={{
                  textAlign: 'left',
                  padding: '8px 10px',
                  borderBottom: '1px solid #E2E8F0',
                  color: '#475569',
                  fontWeight: 700,
                  whiteSpace: 'nowrap',
                }}
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${idx}-${row[0] || 'row'}`} style={{ background: idx % 2 === 0 ? '#fff' : '#FCFCFD' }}>
              {row.map((cell, cellIdx) => (
                <td
                  key={`${idx}-${cellIdx}`}
                  style={{
                    padding: '8px 10px',
                    borderBottom: '1px solid #F1F5F9',
                    color: '#334155',
                    verticalAlign: 'top',
                    maxWidth: 260,
                    wordBreak: 'break-word',
                  }}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const DEEP_PICK_NESTED_KEYS = ['data', 'result', 'payload'] as const

function toRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function pickArrayDeep(value: unknown, keys: string[]): unknown[] {
  const stack: unknown[] = [value]
  const visited = new WeakSet<object>()

  while (stack.length) {
    const current = stack.pop()
    const row = toRecord(current)
    if (!row) continue

    for (const key of keys) {
      const val = row[key]
      if (Array.isArray(val)) return val
    }

    const obj = current as object
    if (visited.has(obj)) continue
    visited.add(obj)

    for (let i = DEEP_PICK_NESTED_KEYS.length - 1; i >= 0; i -= 1) {
      const next = row[DEEP_PICK_NESTED_KEYS[i]]
      if (next && typeof next === 'object') stack.push(next)
    }
  }

  return []
}

function pickStringDeep(value: unknown, keys: string[]): string {
  const stack: unknown[] = [value]
  const visited = new WeakSet<object>()

  while (stack.length) {
    const current = stack.pop()
    const row = toRecord(current)
    if (!row) continue

    for (const key of keys) {
      const val = row[key]
      if (typeof val === 'string' && val.trim()) return val.trim()
    }

    const obj = current as object
    if (visited.has(obj)) continue
    visited.add(obj)

    for (let i = DEEP_PICK_NESTED_KEYS.length - 1; i >= 0; i -= 1) {
      const next = row[DEEP_PICK_NESTED_KEYS[i]]
      if (next && typeof next === 'object') stack.push(next)
    }
  }

  return ''
}

function pickBooleanDeep(value: unknown, keys: string[]): boolean | null {
  const stack: unknown[] = [value]
  const visited = new WeakSet<object>()

  while (stack.length) {
    const current = stack.pop()
    const row = toRecord(current)
    if (!row) continue

    for (const key of keys) {
      const val = row[key]
      if (typeof val === 'boolean') return val
    }

    const obj = current as object
    if (visited.has(obj)) continue
    visited.add(obj)

    for (let i = DEEP_PICK_NESTED_KEYS.length - 1; i >= 0; i -= 1) {
      const next = row[DEEP_PICK_NESTED_KEYS[i]]
      if (next && typeof next === 'object') stack.push(next)
    }
  }

  return null
}

function formatShortDateTime(input?: string): string {
  if (!input) return '-'
  const dt = new Date(input)
  if (Number.isNaN(dt.getTime())) return String(input)
  const m = String(dt.getMonth() + 1).padStart(2, '0')
  const d = String(dt.getDate()).padStart(2, '0')
  const hh = String(dt.getHours()).padStart(2, '0')
  const mm = String(dt.getMinutes()).padStart(2, '0')
  return `${m}/${d} ${hh}:${mm}`
}

function pickNumberDeep(value: unknown, keys: string[]): number | null {
  const stack: unknown[] = [value]
  const visited = new WeakSet<object>()

  while (stack.length) {
    const current = stack.pop()
    const row = toRecord(current)
    if (!row) continue

    for (const key of keys) {
      const val = row[key]
      if (typeof val === 'number' && Number.isFinite(val)) return val
      if (typeof val === 'string') {
        const n = Number(val)
        if (Number.isFinite(n)) return n
      }
    }

    const obj = current as object
    if (visited.has(obj)) continue
    visited.add(obj)

    for (let i = DEEP_PICK_NESTED_KEYS.length - 1; i >= 0; i -= 1) {
      const next = row[DEEP_PICK_NESTED_KEYS[i]]
      if (next && typeof next === 'object') stack.push(next)
    }
  }

  return null
}

function asRecord(value: unknown): Record<string, unknown> {
  return (value && typeof value === 'object' && !Array.isArray(value)) ? (value as Record<string, unknown>) : {}
}

function ProjectSelectCard({ project: p, onSelect }: { project: Project; onSelect: () => void }) {
  const TYPE_ICONS: Record<string, string> = {
    highway: '🛣️',
    road: '🛤️',
    bridge: '🌉',
    tunnel: '🚇',
    municipal: '🏙️',
    urban: '🏢',
    water: '💧',
    building: '🏗️',
  }

  return (
    <div
      onClick={onSelect}
      style={{
        padding: 16,
        background: '#F8FAFF',
        border: '1px solid #E2E8F0',
        borderRadius: 12,
        cursor: 'pointer',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ fontSize: 24, marginBottom: 8 }}>{TYPE_ICONS[p.type] || '🎯'}</div>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#0F172A', marginBottom: 4 }}>{p.name}</div>
      <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 6 }}>{p.owner_unit}</div>
      <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#94A3B8' }}>{p.v_uri}</div>
    </div>
  )
}
