import { useState  } from 'react'
import PhotosPage from './PhotosPage'
import LogPegPage from './LogPegPage'

type RecordsTab = 'photos' | 'log'

export default function SiteRecordsPage() {
  const [tab, setTab] = useState<RecordsTab>('photos')

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        <button
          type="button"
          className={`act-btn ${tab === 'photos' ? 'act-enter' : 'act-detail'}`}
          onClick={() => setTab('photos')}
        >
          现场影像
        </button>
        <button
          type="button"
          className={`act-btn ${tab === 'log' ? 'act-enter' : 'act-detail'}`}
          onClick={() => setTab('log')}
        >
          施工日志
        </button>
      </div>

      {tab === 'photos' ? <PhotosPage /> : <LogPegPage />}
    </div>
  )
}

