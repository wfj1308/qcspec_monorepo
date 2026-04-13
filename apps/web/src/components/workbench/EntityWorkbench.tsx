import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../../store'
import { resolveActorContext } from '../../services/docpeg/httpClient'
import {
  fetchChainStatus,
  fetchNormrefForm,
  fetchProofDetails,
  fetchProjectChains,
  fetchTripHistory,
  fetchWorkbenchEntities,
  postInterpretPreview,
  saveDraftInstance,
  submitDraftInstance,
  submitTripRole,
  workbenchKeys,
} from './workbenchApi'
import type {
  ChainStatusResponse,
  ProcessStep,
  SubmitDraftResponse,
  TripRecord,
  WorkbenchEntity,
} from './workbenchTypes'

export interface EntityWorkbenchProps {
  projectId: string
  className?: string
}

function sortEntities(items: WorkbenchEntity[]): WorkbenchEntity[] {
  return [...items].sort((a, b) => {
    const byCode = String(a.entity_code || '').localeCompare(String(b.entity_code || ''))
    if (byCode !== 0) return byCode
    return String(a.entity_name || '').localeCompare(String(b.entity_name || ''))
  })
}

function parseJsonText(text: string): { value: Record<string, unknown> | null; error: string } {
  try {
    const parsed = JSON.parse(text)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { value: null, error: '表单输入必须是 JSON 对象' }
    }
    return { value: parsed as Record<string, unknown>, error: '' }
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'JSON 解析失败'
    return { value: null, error: message }
  }
}

function statusTone(status: string): string {
  const text = String(status || '').toLowerCase()
  if (text.includes('submit') || text.includes('complete') || text.includes('pass')) {
    return 'text-emerald-600 bg-emerald-50 border-emerald-200'
  }
  if (text.includes('processing') || text.includes('progress') || text.includes('running')) {
    return 'text-blue-600 bg-blue-50 border-blue-200'
  }
  if (text.includes('reject') || text.includes('fail') || text.includes('error')) {
    return 'text-rose-600 bg-rose-50 border-rose-200'
  }
  return 'text-slate-600 bg-slate-50 border-slate-200'
}

function getNodeLabel(entity: WorkbenchEntity): string {
  const code = String(entity.entity_code || '').trim()
  const name = String(entity.entity_name || '').trim()
  if (code && name) return `${code} · ${name}`
  return name || code || entity.id
}

function EntityTreeNode({
  node,
  selectedEntityUri,
  expandedUris,
  childrenByParent,
  onSelect,
  onToggle,
}: {
  node: WorkbenchEntity
  selectedEntityUri: string
  expandedUris: Set<string>
  childrenByParent: Map<string, WorkbenchEntity[]>
  onSelect: (entityUri: string) => void
  onToggle: (entityUri: string) => void
}) {
  const entityUri = String(node.entity_uri || '')
  const children = childrenByParent.get(entityUri) || []
  const hasChildren = children.length > 0
  const isExpanded = expandedUris.has(entityUri)
  const selected = entityUri === selectedEntityUri

  return (
    <div>
      <div className="flex items-start gap-1.5">
        {hasChildren ? (
          <button
            type="button"
            className="mt-0.5 rounded border border-slate-200 bg-white px-1 text-[10px] leading-4 text-slate-600 hover:bg-slate-50"
            onClick={() => onToggle(entityUri)}
            aria-label={isExpanded ? '收起子节点' : '展开子节点'}
          >
            {isExpanded ? '-' : '+'}
          </button>
        ) : (
          <span className="mt-0.5 inline-block w-4 text-center text-[10px] text-slate-300">·</span>
        )}

        <button
          type="button"
          className={[
            'flex-1 rounded-md border px-2 py-1 text-left text-xs transition',
            selected
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50',
          ].join(' ')}
          onClick={() => onSelect(entityUri)}
        >
          <div className="font-medium">{getNodeLabel(node)}</div>
          <div className="mt-0.5 text-[11px] text-slate-500">{node.entity_type || 'entity'}</div>
        </button>
      </div>

      {hasChildren && isExpanded ? (
        <div className="ml-5 mt-1 space-y-1">
          {children.map((child) => (
            <EntityTreeNode
              key={child.id}
              node={child}
              selectedEntityUri={selectedEntityUri}
              expandedUris={expandedUris}
              childrenByParent={childrenByParent}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}

function formatTime(value: string | undefined): string {
  const text = String(value || '').trim()
  if (!text) return '-'
  const date = new Date(text)
  if (Number.isNaN(date.getTime())) return text
  return date.toLocaleString('zh-CN', { hour12: false })
}

export default function EntityWorkbench({ projectId, className }: EntityWorkbenchProps) {
  const queryClient = useQueryClient()
  const user = useAuthStore((s) => s.user)

  const [selectedEntityUri, setSelectedEntityUri] = useState('')
  const [expandedUris, setExpandedUris] = useState<Set<string>>(new Set())
  const [selectedTripId, setSelectedTripId] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [activeStepId, setActiveStepId] = useState('')
  const [inputText, setInputText] = useState('{}')
  const [lastDraftInstanceId, setLastDraftInstanceId] = useState('')
  const [lastSubmitResult, setLastSubmitResult] = useState<SubmitDraftResponse | null>(null)

  const entitiesQuery = useQuery({
    queryKey: workbenchKeys.entities(projectId),
    queryFn: () => fetchWorkbenchEntities(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  })

  const chainsQuery = useQuery({
    queryKey: workbenchKeys.chains(projectId),
    queryFn: () => fetchProjectChains(projectId),
    enabled: Boolean(projectId),
    staleTime: 60_000,
  })

  const entities = entitiesQuery.data?.items || []

  const entityByUri = useMemo(() => {
    return new Map(entities.map((entity) => [String(entity.entity_uri || ''), entity]))
  }, [entities])

  const childrenByParent = useMemo(() => {
    const map = new Map<string, WorkbenchEntity[]>()
    entities.forEach((entity) => {
      const parentUri = String(entity.parent_uri || '').trim()
      if (!parentUri) return
      const bucket = map.get(parentUri) || []
      bucket.push(entity)
      map.set(parentUri, bucket)
    })
    map.forEach((bucket, key) => map.set(key, sortEntities(bucket)))
    return map
  }, [entities])

  const rootEntities = useMemo(() => {
    const roots = entities.filter((entity) => {
      const parentUri = String(entity.parent_uri || '').trim()
      if (!parentUri) return true
      return !entityByUri.has(parentUri)
    })
    return sortEntities(roots)
  }, [entities, entityByUri])

  const selectedEntity = selectedEntityUri ? entityByUri.get(selectedEntityUri) || null : null
  const fallbackChainId = chainsQuery.data?.items?.[0]?.chain_id || ''
  const activeChainId = String(selectedEntity?.chain_id || fallbackChainId || '')

  const chainStatusQuery = useQuery<ChainStatusResponse>({
    queryKey: workbenchKeys.chainStatus(projectId, activeChainId, selectedEntityUri),
    queryFn: () => fetchChainStatus(projectId, activeChainId, selectedEntityUri),
    enabled: Boolean(projectId && activeChainId && selectedEntityUri),
    staleTime: 20_000,
    refetchInterval: 20_000,
  })

  const tripsQuery = useQuery({
    queryKey: workbenchKeys.trips(projectId, selectedEntityUri),
    queryFn: () => fetchTripHistory(projectId, selectedEntityUri),
    enabled: Boolean(projectId && selectedEntityUri),
    staleTime: 20_000,
    refetchInterval: 20_000,
  })

  const trips = tripsQuery.data?.items || []
  const selectedTrip = useMemo<TripRecord | null>(() => {
    if (!trips.length) return null
    if (!selectedTripId) return trips[0]
    return trips.find((item) => item.trip_id === selectedTripId) || trips[0]
  }, [selectedTripId, trips])

  const selectedProofId = String(selectedTrip?.proof_id || '').trim()
  const proofQuery = useQuery({
    queryKey: workbenchKeys.proof(selectedProofId),
    queryFn: () => fetchProofDetails(selectedProofId),
    enabled: Boolean(selectedProofId),
    staleTime: 20_000,
  })

  const steps = chainStatusQuery.data?.steps || []
  const activeStep = useMemo<ProcessStep | null>(() => {
    if (!steps.length) return null
    if (!activeStepId) return null
    return steps.find((step) => step.step_id === activeStepId) || null
  }, [activeStepId, steps])

  const formCode = String(activeStep?.form_code || '').trim()
  const formTemplateQuery = useQuery({
    queryKey: workbenchKeys.form(projectId, formCode),
    queryFn: () => fetchNormrefForm(projectId, formCode),
    enabled: Boolean(formOpen && projectId && formCode),
    staleTime: 120_000,
  })

  const interpretMutation = useMutation({
    mutationFn: (inputJson: Record<string, unknown>) => {
      if (!formCode) throw new Error('当前工序未配置 form_code')
      return postInterpretPreview(projectId, formCode, { input_json: inputJson })
    },
  })

  const draftMutation = useMutation({
    mutationFn: (inputJson: Record<string, unknown>) => {
      if (!formCode) throw new Error('当前工序未配置 form_code')
      if (!selectedEntity) throw new Error('请先选择一个工程实体')

      return saveDraftInstance(projectId, formCode, {
        input_json: inputJson,
        normalized_json: interpretMutation.data?.preview?.normalized || {},
        derived_json: interpretMutation.data?.preview?.derived || {},
        component_uri: selectedEntity.entity_uri,
        pile_id: selectedEntity.entity_code,
        inspection_location: selectedEntity.location_chain || selectedEntity.entity_name,
      })
    },
    onSuccess: (result) => {
      setLastDraftInstanceId(String(result.instance_id || ''))
    },
  })

  const submitDraftMutation = useMutation({
    mutationFn: (instanceId: string) => {
      if (!formCode) throw new Error('当前工序未配置 form_code')
      if (!instanceId) throw new Error('请先保存草稿后再提交')
      return submitDraftInstance(projectId, formCode, instanceId, resolveActorContext())
    },
    onSuccess: (result) => {
      setLastSubmitResult(result)
      queryClient.invalidateQueries({ queryKey: workbenchKeys.chainStatus(projectId, activeChainId, selectedEntityUri) })
      queryClient.invalidateQueries({ queryKey: workbenchKeys.trips(projectId, selectedEntityUri) })
    },
  })

  const submitTripMutation = useMutation({
    mutationFn: (inputJson: Record<string, unknown>) => {
      if (!selectedEntity) throw new Error('请先选择一个工程实体')
      if (!activeStep) throw new Error('请先选择工序步骤')

      const instanceId =
        String(lastSubmitResult?.instance_id || '').trim() ||
        String(lastDraftInstanceId || '').trim() ||
        String(activeStep.latest_instance?.instance_id || '').trim()

      if (!instanceId) throw new Error('未找到可提交的 instance_id，请先保存/提交表单')

      return submitTripRole({
        project_id: projectId,
        component_uri: selectedEntity.entity_uri,
        trip_role: activeStep.step_name,
        form_code: activeStep.form_code,
        instance_id: instanceId,
        payload: inputJson,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workbenchKeys.chainStatus(projectId, activeChainId, selectedEntityUri) })
      queryClient.invalidateQueries({ queryKey: workbenchKeys.trips(projectId, selectedEntityUri) })
    },
  })

  useEffect(() => {
    if (selectedEntityUri) return
    const firstEntity = entities[0]
    if (!firstEntity) return
    setSelectedEntityUri(String(firstEntity.entity_uri || ''))
  }, [entities, selectedEntityUri])

  useEffect(() => {
    if (!rootEntities.length) return
    setExpandedUris((prev) => {
      if (prev.size > 0) return prev
      return new Set(rootEntities.map((item) => item.entity_uri))
    })
  }, [rootEntities])

  useEffect(() => {
    if (!trips.length) {
      setSelectedTripId('')
      return
    }
    if (selectedTripId && trips.some((trip) => trip.trip_id === selectedTripId)) return
    setSelectedTripId(trips[0]?.trip_id || '')
  }, [selectedTripId, trips])

  useEffect(() => {
    if (!formOpen || !activeStep || !selectedEntity) return

    const defaultPayload = {
      component_uri: selectedEntity.entity_uri,
      pile_id: selectedEntity.entity_code,
      inspection_location: selectedEntity.location_chain || selectedEntity.entity_name,
      trip_role: activeStep.step_name,
      actor_name: user?.name || resolveActorContext().actor_name,
      actor_role: resolveActorContext().actor_role,
    }

    setInputText(JSON.stringify(defaultPayload, null, 2))
    setLastDraftInstanceId(String(activeStep.latest_instance?.instance_id || ''))
    setLastSubmitResult(null)
  }, [
    activeStep,
    formOpen,
    selectedEntity,
    user?.name,
  ])

  const onToggleNode = (entityUri: string) => {
    setExpandedUris((prev) => {
      const next = new Set(prev)
      if (next.has(entityUri)) next.delete(entityUri)
      else next.add(entityUri)
      return next
    })
  }

  const openStepDialog = (step: ProcessStep) => {
    setActiveStepId(step.step_id)
    setFormOpen(true)
  }

  const closeStepDialog = () => {
    setFormOpen(false)
  }

  const runInterpretPreview = async () => {
    const parsed = parseJsonText(inputText)
    if (!parsed.value) return
    await interpretMutation.mutateAsync(parsed.value)
  }

  const runSaveDraft = async () => {
    const parsed = parseJsonText(inputText)
    if (!parsed.value) return
    await draftMutation.mutateAsync(parsed.value)
  }

  const runSubmitDraft = async () => {
    const instanceId =
      String(lastDraftInstanceId || '').trim() ||
      String(activeStep?.latest_instance?.instance_id || '').trim()
    await submitDraftMutation.mutateAsync(instanceId)
  }

  const runTripSubmit = async () => {
    const parsed = parseJsonText(inputText)
    if (!parsed.value) return
    await submitTripMutation.mutateAsync(parsed.value)
  }

  return (
    <div className={[
      'grid grid-cols-1 gap-4 xl:grid-cols-[320px_minmax(0,1fr)_360px]',
      className || '',
    ].join(' ')}>
      <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <header className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">工程实体树</h3>
            <p className="text-xs text-slate-500">按 parent_uri 递归渲染</p>
          </div>
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{entities.length}</span>
        </header>

        <div className="max-h-[420px] space-y-1 overflow-auto pr-1">
          {entitiesQuery.isLoading ? <p className="text-xs text-slate-500">加载实体中...</p> : null}
          {!entitiesQuery.isLoading && rootEntities.length === 0 ? (
            <p className="text-xs text-slate-500">暂无工程实体</p>
          ) : null}

          {rootEntities.map((root) => (
            <EntityTreeNode
              key={root.id}
              node={root}
              selectedEntityUri={selectedEntityUri}
              expandedUris={expandedUris}
              childrenByParent={childrenByParent}
              onSelect={setSelectedEntityUri}
              onToggle={onToggleNode}
            />
          ))}
        </div>

        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700">
          <div className="mb-1 font-semibold text-slate-900">实体信息</div>
          <div>编码: {selectedEntity?.entity_code || '-'}</div>
          <div>名称: {selectedEntity?.entity_name || '-'}</div>
          <div>类型: {selectedEntity?.entity_type || '-'}</div>
          <div>里程: {selectedEntity?.location_chain || '-'}</div>
          <div>状态: {selectedEntity?.status || '-'}</div>
          <div className="break-all">链ID: {selectedEntity?.chain_id || fallbackChainId || '-'}</div>
          <div className="break-all">URI: {selectedEntity?.entity_uri || '-'}</div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <header className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">单体工序链</h3>
            <p className="text-xs text-slate-500">点击步骤可打开动态表单</p>
          </div>
          <div className={[
            'rounded border px-2 py-0.5 text-xs',
            statusTone(chainStatusQuery.data?.chain_state || ''),
          ].join(' ')}>
            {chainStatusQuery.data?.chain_state || '未加载'}
          </div>
        </header>

        {chainStatusQuery.isLoading ? <p className="text-xs text-slate-500">加载工序链状态中...</p> : null}

        {!chainStatusQuery.isLoading && steps.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-center text-xs text-slate-500">
            当前实体暂无可用工序步骤
          </div>
        ) : null}

        <div className="space-y-2">
          {steps.map((step, index) => {
            const latestStatus = String(step.latest_instance?.status || '')
            const isCurrent = String(step.step_name || '') === String(chainStatusQuery.data?.current_step || '')

            return (
              <button
                key={step.step_id}
                type="button"
                onClick={() => openStepDialog(step)}
                className={[
                  'w-full rounded-lg border px-3 py-2 text-left transition',
                  isCurrent
                    ? 'border-blue-400 bg-blue-50'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50',
                ].join(' ')}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-medium text-slate-900">{index + 1}. {step.step_name}</div>
                    <div className="mt-0.5 text-[11px] text-slate-500">表单: {step.form_code || '-'}</div>
                  </div>
                  <div className={[
                    'rounded border px-2 py-0.5 text-[11px]',
                    statusTone(latestStatus),
                  ].join(' ')}>
                    {latestStatus || 'pending'}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <header className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">存证历史</h3>
            <p className="text-xs text-slate-500">按工序执行记录展示</p>
          </div>
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{trips.length}</span>
        </header>

        <div className="max-h-[280px] space-y-1 overflow-auto pr-1">
          {tripsQuery.isLoading ? <p className="text-xs text-slate-500">加载执行历史中...</p> : null}
          {!tripsQuery.isLoading && trips.length === 0 ? (
            <p className="text-xs text-slate-500">暂无执行历史</p>
          ) : null}

          {trips.map((trip) => {
            const active = trip.trip_id === selectedTrip?.trip_id
            return (
              <button
                key={trip.trip_id}
                type="button"
                onClick={() => setSelectedTripId(trip.trip_id)}
                className={[
                  'w-full rounded-md border px-2 py-1.5 text-left text-xs',
                  active
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50',
                ].join(' ')}
              >
                <div className="font-medium">{trip.trip_role || trip.trip_id}</div>
                <div className="mt-0.5 text-[11px] text-slate-500">{formatTime(trip.created_at)}</div>
                <div className="mt-0.5 break-all text-[11px] text-slate-500">存证ID: {trip.proof_id || '-'}</div>
              </button>
            )
          })}
        </div>

        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700">
          <div className="mb-1 font-semibold text-slate-900">存证详情</div>
          {!selectedProofId ? <div>请选择一条包含 proof_id 的执行记录</div> : null}
          {selectedProofId && proofQuery.isLoading ? <div>加载存证详情中...</div> : null}
          {selectedProofId && !proofQuery.isLoading ? (
            <>
              <div>存证ID: {proofQuery.data?.proof.proof_id || selectedProofId}</div>
              <div className="break-all">哈希: {String(proofQuery.data?.proof.hash || '-')}</div>
              <div>结果: {String(proofQuery.data?.proof.result || '-')}</div>
              <div>签名数: {Array.isArray(proofQuery.data?.proof.signatures) ? proofQuery.data?.proof.signatures.length : 0}</div>
              <div>附件数: {Array.isArray(proofQuery.data?.proof.attachments) ? proofQuery.data?.proof.attachments.length : 0}</div>
              <div>创建时间: {formatTime(String(proofQuery.data?.proof.created_at || ''))}</div>
            </>
          ) : null}
        </div>
      </section>

      {formOpen && activeStep ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="w-full max-w-4xl rounded-xl border border-slate-200 bg-white p-4 shadow-xl">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h4 className="text-sm font-semibold text-slate-900">{activeStep.step_name} · 动态表单</h4>
                <p className="text-xs text-slate-500">form_code: {activeStep.form_code || '-'}</p>
              </div>
              <button
                type="button"
                onClick={closeStepDialog}
                className="rounded border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
              >
                关闭
              </button>
            </div>

            <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.2fr_1fr]">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-700">输入 JSON</label>
                <textarea
                  className="h-72 w-full rounded-lg border border-slate-300 bg-slate-50 p-2 font-mono text-xs text-slate-800 outline-none focus:border-blue-400"
                  value={inputText}
                  onChange={(event) => setInputText(event.target.value)}
                />
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={runInterpretPreview}
                    disabled={interpretMutation.isPending}
                    className="rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {interpretMutation.isPending ? '预览中...' : '解释预览'}
                  </button>
                  <button
                    type="button"
                    onClick={runSaveDraft}
                    disabled={draftMutation.isPending}
                    className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {draftMutation.isPending ? '保存中...' : '保存草稿'}
                  </button>
                  <button
                    type="button"
                    onClick={runSubmitDraft}
                    disabled={submitDraftMutation.isPending}
                    className="rounded bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {submitDraftMutation.isPending ? '提交中...' : '提交草稿'}
                  </button>
                  <button
                    type="button"
                    onClick={runTripSubmit}
                    disabled={submitTripMutation.isPending}
                    className="rounded bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {submitTripMutation.isPending ? '触发中...' : '触发工序提交'}
                  </button>
                </div>

                <div className="mt-2 space-y-1 text-xs text-slate-600">
                  {lastDraftInstanceId ? <div>草稿实例: {lastDraftInstanceId}</div> : null}
                  {lastSubmitResult?.proof_id ? <div>提交产出存证: {lastSubmitResult.proof_id}</div> : null}
                  {submitTripMutation.data?.trip_id ? <div>执行ID: {submitTripMutation.data.trip_id}</div> : null}
                </div>

                {interpretMutation.error ? <p className="mt-2 text-xs text-rose-600">{interpretMutation.error.message}</p> : null}
                {draftMutation.error ? <p className="mt-2 text-xs text-rose-600">{draftMutation.error.message}</p> : null}
                {submitDraftMutation.error ? <p className="mt-2 text-xs text-rose-600">{submitDraftMutation.error.message}</p> : null}
                {submitTripMutation.error ? <p className="mt-2 text-xs text-rose-600">{submitTripMutation.error.message}</p> : null}
              </div>

              <div className="space-y-2">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <div className="mb-1 text-xs font-semibold text-slate-900">模板信息</div>
                  {formTemplateQuery.isLoading ? <div className="text-xs text-slate-500">加载模板中...</div> : null}
                  {!formTemplateQuery.isLoading ? (
                    <>
                      <div className="text-xs text-slate-700">标题: {formTemplateQuery.data?.form.title || '-'}</div>
                      <div className="text-xs text-slate-700">族系: {formTemplateQuery.data?.form.family || '-'}</div>
                      <div className="mt-1 rounded border border-slate-200 bg-white p-2 text-[11px] text-slate-600">
                        <pre className="max-h-24 overflow-auto whitespace-pre-wrap break-all">
                          {JSON.stringify(formTemplateQuery.data?.form.template || {}, null, 2)}
                        </pre>
                      </div>
                    </>
                  ) : null}
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <div className="mb-1 text-xs font-semibold text-slate-900">预览结果</div>
                  {!interpretMutation.data ? <div className="text-xs text-slate-500">尚未执行 interpret-preview</div> : null}
                  {interpretMutation.data ? (
                    <pre className="max-h-60 overflow-auto whitespace-pre-wrap break-all text-[11px] text-slate-700">
                      {JSON.stringify(interpretMutation.data.preview || {}, null, 2)}
                    </pre>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
