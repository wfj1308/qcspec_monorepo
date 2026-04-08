import type { MobileFormSpec, MobileWorkorder } from '../types/mobile'

export const mobileMockWorkorders: Record<string, MobileWorkorder> = {
  'K12-340-phase4B': {
    code: 'K12-340-phase4B',
    name: 'K12+340 钻孔灌注桩',
    vUri: 'v://cn.dajing/djgs/bridge/K12-340-phase4B',
    steps: [
      {
        key: 'casing',
        name: '护筒埋设',
        status: 'done',
        requiredRole: '施工单位',
        doneAt: '04-06 09:30',
        doneBy: '张三',
        proofId: 'NINST-561A7B64',
      },
      {
        key: 'hole_check',
        name: '成孔检查',
        status: 'current',
        requiredRole: '检查',
        formName: '桥施7表',
        normrefUri: 'v://normref.com/qc/pile-foundation@v1',
      },
      {
        key: 'rebar_install',
        name: '钢筋安装',
        status: 'todo',
        requiredRole: '施工单位',
        formName: '桥施11表',
        normrefUri: 'v://normref.com/qc/rebar-processing@v1',
      },
      {
        key: 'concrete_pour',
        name: '混凝土浇筑',
        status: 'todo',
        requiredRole: '施工单位',
        formName: '桥施12表',
        normrefUri: 'v://normref.com/qc/concrete-compressive-test@v1',
      },
      {
        key: 'acceptance',
        name: '验收',
        status: 'todo',
        requiredRole: '监理',
        formName: '验收检查表',
        normrefUri: 'v://normref.com/qc/template/general-quality-inspection@v1',
      },
    ],
  },
  'K12-340-4C': {
    code: 'K12-340-4C',
    name: 'K12+340 钻孔灌注桩',
    vUri: 'v://cn.dajing/djgs/bridge/K12-340-4C',
    steps: [
      {
        key: 'casing',
        name: '护筒埋设',
        status: 'done',
        requiredRole: '施工单位',
        doneAt: '04-07 08:40',
        doneBy: '李四',
        proofId: 'NINST-5BB704CE',
      },
      {
        key: 'hole_check',
        name: '成孔检查',
        status: 'done',
        requiredRole: '检查',
        doneAt: '04-07 09:20',
        doneBy: '王工',
        proofId: 'NINST-A8E91BCD',
      },
      {
        key: 'rebar_install',
        name: '钢筋安装',
        status: 'current',
        requiredRole: '施工单位',
        formName: '桥施11表',
        normrefUri: 'v://normref.com/qc/rebar-processing@v1',
      },
      {
        key: 'concrete_pour',
        name: '混凝土浇筑',
        status: 'todo',
        requiredRole: '施工单位',
        formName: '桥施12表',
        normrefUri: 'v://normref.com/qc/concrete-compressive-test@v1',
      },
      {
        key: 'acceptance',
        name: '验收',
        status: 'todo',
        requiredRole: '监理',
        formName: '验收检查表',
        normrefUri: 'v://normref.com/qc/template/general-quality-inspection@v1',
      },
    ],
  },
}

export const fallbackFormSpecsByStepKey: Record<string, Omit<MobileFormSpec, 'baseFields' | 'normrefUri'>> = {
  hole_check: {
    subtitle: '桥施7表',
    fields: [
      {
        key: 'hole_diameter',
        label: '7.1 孔径',
        hint: '设计>=1.5m',
        unit: 'm',
        required: true,
        threshold: { operator: 'gte', value: 1.5 },
      },
      {
        key: 'hole_depth',
        label: '7.2 孔深',
        hint: '设计>=22m',
        unit: 'm',
        required: true,
        threshold: { operator: 'gte', value: 22 },
      },
      {
        key: 'inclination',
        label: '7.3 倾斜度',
        hint: '规范<=1%',
        unit: '%',
        required: true,
        threshold: { operator: 'lte', value: 1 },
      },
    ],
  },
  rebar_install: {
    subtitle: '桥施11表',
    fields: [
      {
        key: 'main_spacing',
        label: '11.1 主筋间距',
        hint: '设计<=200mm',
        unit: 'mm',
        required: true,
        threshold: { operator: 'lte', value: 200 },
      },
      {
        key: 'stirrup_spacing',
        label: '11.2 箍筋间距',
        hint: '设计<=100mm',
        unit: 'mm',
        required: true,
        threshold: { operator: 'lte', value: 100 },
      },
      {
        key: 'cover_thickness',
        label: '11.3 保护层厚度',
        hint: '设计>=50mm',
        unit: 'mm',
        required: true,
        threshold: { operator: 'gte', value: 50 },
      },
    ],
  },
  concrete_pour: {
    subtitle: '桥施12表',
    fields: [
      {
        key: 'slump',
        label: '12.1 坍落度',
        hint: '允许范围 180-220mm',
        unit: 'mm',
        required: true,
        threshold: { operator: 'range', value: [180, 220] },
      },
      {
        key: 'temperature',
        label: '12.2 入模温度',
        hint: '规范<=30℃',
        unit: '℃',
        required: true,
        threshold: { operator: 'lte', value: 30 },
      },
      {
        key: 'pour_duration',
        label: '12.3 浇筑持续时长',
        hint: '设计<=4h',
        unit: 'h',
        required: true,
        threshold: { operator: 'lte', value: 4 },
      },
    ],
  },
}

export function cloneMockWorkorder(code: string): MobileWorkorder | null {
  const source = mobileMockWorkorders[code]
  if (!source) return null
  return {
    ...source,
    steps: source.steps.map((step) => ({ ...step })),
  }
}


