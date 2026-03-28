import type { SettingsState } from './appShellShared'

export interface EnterpriseInfoState {
  name: string
  vUri: string
  creditCode: string
  adminEmail: string
}

export interface GitpegVerifyMessage {
  text: string
  color: string
}

export interface WebhookResultState {
  text: string
  color: string
  visible: boolean
}

export type PersistSettingsPayload = Partial<SettingsState> & Record<string, unknown>
