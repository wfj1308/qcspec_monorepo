import { useEffect } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import type { Project } from '@qcspec/types'
import type { ProjectRegisterMeta } from './appShellShared'
import { projectMetaFromRow } from './projectMetaUtils'

interface UseProjectMetaSyncArgs {
  projects: Project[]
  memberCount: number
  setProjectMeta: Dispatch<SetStateAction<Record<string, ProjectRegisterMeta>>>
}

export function useProjectMetaSync({
  projects,
  memberCount,
  setProjectMeta,
}: UseProjectMetaSyncArgs): void {
  useEffect(() => {
    setProjectMeta((prev) => {
      let changed = false
      const next = { ...prev }
      const validIds = new Set(projects.map((project) => project.id))

      Object.keys(next).forEach((projectId) => {
        if (!validIds.has(projectId)) {
          delete next[projectId]
          changed = true
        }
      })

      projects.forEach((project) => {
        const derived = projectMetaFromRow(project, memberCount)
        if (!derived) return
        const existing = next[project.id]
        const same = existing && JSON.stringify(existing) === JSON.stringify(derived)
        if (!same) {
          next[project.id] = derived
          changed = true
        }
      })

      return changed ? next : prev
    })
  }, [projects, memberCount, setProjectMeta])
}
