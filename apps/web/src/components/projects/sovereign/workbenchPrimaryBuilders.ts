import { type buildWorkbenchSectionsProps } from './workbench/sectionPropsBuilders'

type WorkbenchSectionsArgs = Parameters<typeof buildWorkbenchSectionsProps>[0]
type WorkbenchShellBuilderArgs = WorkbenchSectionsArgs['shell']
type WorkbenchPrimaryBuilderArgs = WorkbenchSectionsArgs['primary']

export function buildSovereignWorkbenchShell(
  args: WorkbenchShellBuilderArgs,
): WorkbenchShellBuilderArgs {
  return args
}

export function buildSovereignWorkbenchPrimary(
  args: WorkbenchPrimaryBuilderArgs,
): WorkbenchPrimaryBuilderArgs {
  return args
}
