import Papa from 'papaparse'

export async function shaBuffer(buf: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

export async function sha(file: File): Promise<string> {
  const buf = await file.arrayBuffer()
  return shaBuffer(buf)
}

export async function shaJson(payload: Record<string, unknown>): Promise<string> {
  const raw = JSON.stringify(payload)
  const buf = new TextEncoder().encode(raw)
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

export async function sha256Hex(input: string): Promise<string> {
  const buf = new TextEncoder().encode(input)
  const digest = await crypto.subtle.digest('SHA-256', buf)
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

function formatExifDate(raw: string): string {
  const text = String(raw || '').trim()
  if (!text) return ''
  const normalized = text.replace(/^(\d{4}):(\d{2}):(\d{2})/, '$1-$2-$3')
  const dt = new Date(normalized)
  if (!Number.isFinite(dt.getTime())) return text
  return dt.toISOString()
}

function readExifValue(
  view: DataView,
  entryOffset: number,
  little: boolean,
): { tag: number; type: number; count: number; valueOffset: number } {
  const tag = view.getUint16(entryOffset, little)
  const type = view.getUint16(entryOffset + 2, little)
  const count = view.getUint32(entryOffset + 4, little)
  const valueOffset = view.getUint32(entryOffset + 8, little)
  return { tag, type, count, valueOffset }
}

function exifTypeSize(type: number): number {
  if (type === 1 || type === 2 || type === 7) return 1
  if (type === 3) return 2
  if (type === 4 || type === 9) return 4
  if (type === 5 || type === 10) return 8
  return 0
}

function readExifAscii(view: DataView, offset: number, count: number): string {
  let out = ''
  for (let i = 0; i < count; i += 1) {
    const c = view.getUint8(offset + i)
    if (c === 0) break
    out += String.fromCharCode(c)
  }
  return out
}

function readExifRational(view: DataView, offset: number, little: boolean, signed = false): number {
  const num = signed ? view.getInt32(offset, little) : view.getUint32(offset, little)
  const den = signed ? view.getInt32(offset + 4, little) : view.getUint32(offset + 4, little)
  if (!den) return 0
  return num / den
}

function readExifTagValue(
  view: DataView,
  tiffStart: number,
  entryOffset: number,
  type: number,
  count: number,
  valueOffset: number,
  little: boolean,
): string | number | number[] {
  const size = exifTypeSize(type) * count
  const offset = size <= 4 ? entryOffset + 8 : tiffStart + valueOffset
  const valueInline = size <= 4 ? view.getUint32(entryOffset + 8, little) : 0

  if (type === 2) {
    if (size <= 4) {
      const bytes = new Uint8Array([
        valueInline & 0xff,
        (valueInline >> 8) & 0xff,
        (valueInline >> 16) & 0xff,
        (valueInline >> 24) & 0xff,
      ])
      return String.fromCharCode(...bytes).replace(/\0+$/, '')
    }
    return readExifAscii(view, offset, count)
  }
  if (type === 3) {
    if (count === 1) {
      return size <= 4 ? (little ? (valueInline & 0xffff) : (valueInline >> 16)) : view.getUint16(offset, little)
    }
    const arr: number[] = []
    for (let i = 0; i < count; i += 1) arr.push(view.getUint16(offset + i * 2, little))
    return arr
  }
  if (type === 4) {
    if (count === 1) return size <= 4 ? valueInline : view.getUint32(offset, little)
    const arr: number[] = []
    for (let i = 0; i < count; i += 1) arr.push(view.getUint32(offset + i * 4, little))
    return arr
  }
  if (type === 5) {
    const arr: number[] = []
    for (let i = 0; i < count; i += 1) arr.push(readExifRational(view, offset + i * 8, little))
    return count === 1 ? arr[0] : arr
  }
  if (type === 9) {
    if (count === 1) return size <= 4 ? (valueInline | 0) : view.getInt32(offset, little)
  }
  if (type === 10) {
    const arr: number[] = []
    for (let i = 0; i < count; i += 1) arr.push(readExifRational(view, offset + i * 8, little, true))
    return count === 1 ? arr[0] : arr
  }
  if (type === 1 || type === 7) {
    if (count === 1) return size <= 4 ? (valueInline & 0xff) : view.getUint8(offset)
  }
  return ''
}

export function parseExifFromJpeg(
  buffer: ArrayBuffer,
): { lat?: number; lng?: number; capturedAt?: string; warning?: string; ok: boolean } {
  const view = new DataView(buffer)
  if (view.byteLength < 4 || view.getUint16(0, false) !== 0xffd8) {
    return { ok: false, warning: '非 JPEG，无法解析 EXIF' }
  }
  let offset = 2
  while (offset + 4 < view.byteLength) {
    if (view.getUint8(offset) !== 0xff) break
    const marker = view.getUint8(offset + 1)
    const size = view.getUint16(offset + 2, false)
    if (marker === 0xe1) {
      const header = String.fromCharCode(
        view.getUint8(offset + 4),
        view.getUint8(offset + 5),
        view.getUint8(offset + 6),
        view.getUint8(offset + 7),
        view.getUint8(offset + 8),
        view.getUint8(offset + 9),
      )
      if (header === 'Exif\u0000\u0000') {
        const tiffStart = offset + 10
        const endian = view.getUint16(tiffStart, false)
        const little = endian === 0x4949
        const firstIfdOffset = view.getUint32(tiffStart + 4, little)
        let exifIfdOffset = 0
        let gpsIfdOffset = 0
        let dateTime = ''

        const ifd0Offset = tiffStart + firstIfdOffset
        const ifd0Entries = view.getUint16(ifd0Offset, little)
        for (let i = 0; i < ifd0Entries; i += 1) {
          const entryOffset = ifd0Offset + 2 + i * 12
          const { tag, type, count, valueOffset } = readExifValue(view, entryOffset, little)
          if (tag === 0x8769) exifIfdOffset = valueOffset
          if (tag === 0x8825) gpsIfdOffset = valueOffset
          if (tag === 0x0132) {
            const val = readExifTagValue(view, tiffStart, entryOffset, type, count, valueOffset, little)
            if (typeof val === 'string') dateTime = val
          }
        }

        let dateTimeOriginal = ''
        if (exifIfdOffset) {
          const exifOffset = tiffStart + exifIfdOffset
          const exifEntries = view.getUint16(exifOffset, little)
          for (let i = 0; i < exifEntries; i += 1) {
            const entryOffset = exifOffset + 2 + i * 12
            const { tag, type, count, valueOffset } = readExifValue(view, entryOffset, little)
            if (tag === 0x9003 || tag === 0x9004) {
              const val = readExifTagValue(view, tiffStart, entryOffset, type, count, valueOffset, little)
              if (typeof val === 'string') dateTimeOriginal = val
            }
          }
        }

        let lat: number | undefined
        let lng: number | undefined
        let gpsDate = ''
        let gpsTime: number[] | null = null
        let latRef = ''
        let lngRef = ''
        if (gpsIfdOffset) {
          const gpsOffset = tiffStart + gpsIfdOffset
          const gpsEntries = view.getUint16(gpsOffset, little)
          for (let i = 0; i < gpsEntries; i += 1) {
            const entryOffset = gpsOffset + 2 + i * 12
            const { tag, type, count, valueOffset } = readExifValue(view, entryOffset, little)
            const val = readExifTagValue(view, tiffStart, entryOffset, type, count, valueOffset, little)
            if (tag === 0x0001 && typeof val === 'string') latRef = val.trim()
            if (tag === 0x0003 && typeof val === 'string') lngRef = val.trim()
            if (tag === 0x0002 && Array.isArray(val)) {
              const [d, m, s] = val as number[]
              lat = d + m / 60 + s / 3600
            }
            if (tag === 0x0004 && Array.isArray(val)) {
              const [d, m, s] = val as number[]
              lng = d + m / 60 + s / 3600
            }
            if (tag === 0x001d && typeof val === 'string') gpsDate = val.trim()
            if (tag === 0x0007 && Array.isArray(val)) gpsTime = val as number[]
          }
        }

        if (lat != null && /S/i.test(latRef)) lat = -Math.abs(lat)
        if (lng != null && /W/i.test(lngRef)) lng = -Math.abs(lng)

        let capturedAt = ''
        if (dateTimeOriginal) capturedAt = formatExifDate(dateTimeOriginal)
        else if (dateTime) capturedAt = formatExifDate(dateTime)
        if (!capturedAt && gpsDate && gpsTime && gpsTime.length >= 2) {
          const [h, m, s = 0] = gpsTime
          const iso = `${gpsDate.replace(/:/g, '-') || gpsDate} ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(Math.floor(s)).padStart(2, '0')}`
          capturedAt = formatExifDate(iso)
        }

        const ok = !!(lat != null && lng != null && capturedAt)
        const warning = ok ? '' : 'EXIF 信息不完整'
        return { lat, lng, capturedAt, ok, warning }
      }
    }
    offset += 2 + size
  }
  return { ok: false, warning: '未检测到 EXIF' }
}

export function haversineMeters(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const toRad = (x: number) => (x * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return 2 * 6371000 * Math.asin(Math.sqrt(a))
}

export function extractNodeGeo(meta: Record<string, unknown>): { lat: number; lng: number; radiusM: number } | null {
  const pickNum = (value: unknown) => (Number.isFinite(Number(value)) ? Number(value) : null)
  const lat =
    pickNum(meta.gps_lat) ??
    pickNum(meta.lat) ??
    pickNum((meta.geo_location as Record<string, unknown> | undefined)?.lat) ??
    pickNum((meta.coordinate as Record<string, unknown> | undefined)?.lat)
  const lng =
    pickNum(meta.gps_lng) ??
    pickNum(meta.lng) ??
    pickNum((meta.geo_location as Record<string, unknown> | undefined)?.lng) ??
    pickNum((meta.coordinate as Record<string, unknown> | undefined)?.lng)
  if (lat == null || lng == null) return null
  const radiusM = pickNum(meta.geo_radius_m) ?? pickNum(meta.radius_m) ?? 150
  return { lat, lng, radiusM }
}

export function downloadJson(filename: string, data: unknown): void {
  const payload = JSON.stringify(data, null, 2)
  const blob = new Blob([payload], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function downloadCsv(filename: string, rows: Array<Record<string, unknown>>): void {
  const headers: string[] = []
  rows.forEach((row) => {
    Object.keys(row || {}).forEach((key) => {
      if (!headers.includes(key)) headers.push(key)
    })
  })
  const data = rows.map((row) => headers.map((key) => (row && key in row ? row[key] : '')))
  const csv = Papa.unparse({ fields: headers, data })
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
