import React from 'react'

import './PublicVerifyPage.css'
import PublicVerifyView from './publicVerify/PublicVerifyView'
import { usePublicVerifyController } from './publicVerify/usePublicVerifyController'

export default function PublicVerifyPage() {
  const vm = usePublicVerifyController()
  return <PublicVerifyView vm={vm} />
}
