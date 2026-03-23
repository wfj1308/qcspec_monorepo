/**
 * QCSpec · 全局状态
 * apps/web/src/store/index.ts
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Enterprise, Project, Inspection, Photo } from '@qcspec/types'

// ── Auth Store ──
interface AuthState {
  user:         User | null
  enterprise:   Enterprise | null
  token:        string | null
  setUser:      (user: User, enterprise: Enterprise, token: string) => void
  logout:       () => void
  isLoggedIn:   () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user:       null,
      enterprise: null,
      token:      null,

      setUser: (user, enterprise, token) =>
        set({ user, enterprise, token }),

      logout: () =>
        set({ user: null, enterprise: null, token: null }),

      isLoggedIn: () => !!get().token,
    }),
    { name: 'qcspec-auth' }
  )
)

// ── Project Store ──
interface ProjectState {
  projects:       Project[]
  currentProject: Project | null
  setProjects:    (p: Project[]) => void
  setCurrentProject: (p: Project | null) => void
  addProject:     (p: Project) => void
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects:          [],
  currentProject:    null,
  setProjects:       (projects) => set({ projects }),
  setCurrentProject: (p) => set({ currentProject: p }),
  addProject:        (p) => set((s) => ({ projects: [p, ...s.projects] })),
}))

// ── Inspection Store ──
interface InspectionState {
  inspections:    Inspection[]
  photoLinksByInspection: Record<string, string[]>
  setInspections: (list: Inspection[]) => void
  addInspection:  (i: Inspection) => void
  removeInspection: (id: string) => void
  setInspectionPhotoLinks: (inspectionId: string, photoIds: string[]) => void
  stats: {
    total: number; pass: number; warn: number; fail: number; pass_rate: number
  }
  computeStats: () => void
}

export const useInspectionStore = create<InspectionState>((set, get) => ({
  inspections:    [],
  photoLinksByInspection: {},
  stats: { total: 0, pass: 0, warn: 0, fail: 0, pass_rate: 0 },

  setInspections: (list) => {
    set({ inspections: list })
    get().computeStats()
  },

  addInspection: (i) => {
    set((s) => ({ inspections: [i, ...s.inspections] }))
    get().computeStats()
  },

  removeInspection: (id) => {
    set((s) => {
      const nextLinks = { ...s.photoLinksByInspection }
      delete nextLinks[id]
      return { inspections: s.inspections.filter(x => x.id !== id), photoLinksByInspection: nextLinks }
    })
    get().computeStats()
  },

  setInspectionPhotoLinks: (inspectionId, photoIds) => {
    set((s) => ({
      photoLinksByInspection: {
        ...s.photoLinksByInspection,
        [inspectionId]: photoIds,
      },
    }))
  },

  computeStats: () => {
    const list  = get().inspections
    const total = list.length
    const pass  = list.filter(i => i.result === 'pass').length
    const warn  = list.filter(i => i.result === 'warn').length
    const fail  = list.filter(i => i.result === 'fail').length
    set({ stats: {
      total, pass, warn, fail,
      pass_rate: total ? Math.round(pass / total * 100 * 10) / 10 : 0
    }})
  },
}))

// ── Photo Store ──
interface PhotoState {
  photos:       Photo[]
  selected:     Set<string>
  pendingLinkPhotoIds: string[]
  setPhotos:    (p: Photo[]) => void
  addPhoto:     (p: Photo) => void
  toggleSelect: (id: string) => void
  clearSelect:  () => void
  removePhoto:  (id: string) => void
  setPendingLinkPhotoIds: (ids: string[]) => void
  clearPendingLinkPhotoIds: () => void
}

export const usePhotoStore = create<PhotoState>((set) => ({
  photos:       [],
  selected:     new Set(),
  pendingLinkPhotoIds: [],

  setPhotos:    (photos) => set({ photos }),

  addPhoto:     (p) => set((s) => ({ photos: [p, ...s.photos] })),

  toggleSelect: (id) => set((s) => {
    const next = new Set(s.selected)
    next.has(id) ? next.delete(id) : next.add(id)
    return { selected: next }
  }),

  clearSelect:  () => set({ selected: new Set() }),

  removePhoto:  (id) => set((s) => ({
    photos: s.photos.filter(p => p.id !== id),
    selected: (() => { const n = new Set(s.selected); n.delete(id); return n })()
  })),

  setPendingLinkPhotoIds: (ids) => set({ pendingLinkPhotoIds: ids }),
  clearPendingLinkPhotoIds: () => set({ pendingLinkPhotoIds: [] }),
}))

// ── UI Store ──
interface UIState {
  sidebarOpen:    boolean
  activeTab:      string
  loading:        boolean
  toastMsg:       string
  setSidebarOpen: (v: boolean) => void
  setActiveTab:   (t: string) => void
  setLoading:     (v: boolean) => void
  showToast:      (msg: string) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen:    true,
  activeTab:      'dashboard',
  loading:        false,
  toastMsg:       '',

  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  setActiveTab:   (t) => set({ activeTab: t }),
  setLoading:     (v) => set({ loading: v }),

  showToast: (msg) => {
    set({ toastMsg: msg })
    setTimeout(() => set({ toastMsg: '' }), 2400)
  },
}))
