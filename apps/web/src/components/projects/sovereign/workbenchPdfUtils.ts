export function asWorkbenchDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function escapePdfText(input: string): string {
  return String(input || '').replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)').replace(/\r?\n/g, ' ')
}

export function buildDraftPdfBase64(lines: string[]): string {
  const safeLines = lines.filter(Boolean).map((line) => escapePdfText(line))
  const content = safeLines
    .map((line, idx) => {
      const y = 720 - idx * 16
      return `BT /F1 12 Tf 72 ${y} Td (${line}) Tj ET`
    })
    .join('\n')
  const encoder = new TextEncoder()
  const header = '%PDF-1.4\n'
  const obj1 = '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
  const obj2 = '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
  const obj3 = '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n'
  const contentBytes = encoder.encode(content)
  const obj4 = `4 0 obj\n<< /Length ${contentBytes.length} >>\nstream\n${content}\nendstream\nendobj\n`
  const obj5 = '5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n'
  const objects = [obj1, obj2, obj3, obj4, obj5]
  const offsets: number[] = [0]
  let cursor = encoder.encode(header).length
  for (const obj of objects) {
    offsets.push(cursor)
    cursor += encoder.encode(obj).length
  }
  let xref = `xref\n0 ${objects.length + 1}\n`
  xref += '0000000000 65535 f \n'
  for (let i = 1; i < offsets.length; i += 1) {
    xref += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`
  }
  const trailer = `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${cursor}\n%%EOF`
  const pdf = header + objects.join('') + xref + trailer
  const bytes = encoder.encode(pdf)
  let binary = ''
  bytes.forEach((b) => { binary += String.fromCharCode(b) })
  return btoa(binary)
}
