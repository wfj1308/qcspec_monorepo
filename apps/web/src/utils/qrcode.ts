// Minimal QR generator based on qrcodegen (MIT License) by Project Nayuki
// https://www.nayuki.io/page/qr-code-generator-library (adapted for TS)

export type QrEcc = 'low' | 'medium' | 'quartile' | 'high'

const ECC_LEVELS = {
  low: { formatBits: 1 },
  medium: { formatBits: 0 },
  quartile: { formatBits: 3 },
  high: { formatBits: 2 },
} as const

class BitBuffer {
  private data: number[] = []
  get length() { return this.data.length }
  appendBits(value: number, length: number) {
    for (let i = length - 1; i >= 0; i -= 1) this.data.push((value >>> i) & 1)
  }
  getBits() { return this.data }
}

function toUtf8Bytes(str: string): number[] {
  const encoder = new TextEncoder()
  return Array.from(encoder.encode(str))
}

function getNumRawDataModules(ver: number): number {
  let result = (16 * ver + 128) * ver + 64
  if (ver >= 2) {
    const numAlign = Math.floor(ver / 7) + 2
    result -= (25 * numAlign - 10) * numAlign - 55
    if (ver >= 7) result -= 36
  }
  return result
}

function getNumDataCodewords(ver: number, ecc: QrEcc): number {
  const total = Math.floor(getNumRawDataModules(ver) / 8)
  const eccTable: Record<QrEcc, number[]> = {
    low:     [0, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    medium:  [0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
    quartile:[0, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    high:    [0, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  }
  return total - eccTable[ecc][ver]
}

function reedSolomonComputeDivisor(degree: number): number[] {
  let result = [1]
  let root = 1
  for (let i = 0; i < degree; i += 1) {
    const next: number[] = new Array(result.length + 1).fill(0)
    for (let j = 0; j < result.length; j += 1) {
      next[j] ^= multiply(result[j], root)
      next[j + 1] ^= result[j]
    }
    result = next
    root = multiply(root, 2)
  }
  return result
}

function reedSolomonComputeRemainder(data: number[], divisor: number[]): number[] {
  const result = new Array(divisor.length - 1).fill(0)
  for (const b of data) {
    const factor = b ^ result[0]
    result.shift()
    result.push(0)
    for (let i = 0; i < result.length; i += 1) {
      result[i] ^= multiply(divisor[i], factor)
    }
  }
  return result
}

function multiply(x: number, y: number): number {
  let z = 0
  for (let i = 7; i >= 0; i -= 1) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d)
    if (((y >>> i) & 1) !== 0) z ^= x
  }
  return z & 0xff
}

function getCharCountBits(version: number): number {
  return version <= 9 ? 8 : version <= 26 ? 16 : 16
}

function makeDataBits(text: string): BitBuffer {
  const bb = new BitBuffer()
  const bytes = toUtf8Bytes(text)
  bb.appendBits(0b0100, 4)
  bb.appendBits(bytes.length, getCharCountBits(1))
  for (const b of bytes) bb.appendBits(b, 8)
  return bb
}

function buildCodewords(text: string, ecc: QrEcc): { version: number; data: number[]; ecc: number[] } {
  const dataBits = makeDataBits(text)
  for (let version = 1; version <= 10; version += 1) {
    const dataCapacityBits = getNumDataCodewords(version, ecc) * 8
    if (dataBits.length <= dataCapacityBits) {
      dataBits.appendBits(0, Math.min(4, dataCapacityBits - dataBits.length))
      while (dataBits.length % 8 !== 0) dataBits.appendBits(0, 1)
      const padBytes = [0xec, 0x11]
      let i = 0
      while (dataBits.length < dataCapacityBits) {
        dataBits.appendBits(padBytes[i % 2], 8)
        i += 1
      }
      const data: number[] = []
      const bits = dataBits.getBits()
      for (let j = 0; j < bits.length; j += 8) {
        let b = 0
        for (let k = 0; k < 8; k += 1) b = (b << 1) | bits[j + k]
        data.push(b)
      }
      const eccLen = Math.floor(getNumRawDataModules(version) / 8) - getNumDataCodewords(version, ecc)
      const divisor = reedSolomonComputeDivisor(eccLen)
      const eccBytes = reedSolomonComputeRemainder(data, divisor)
      return { version, data, ecc: eccBytes }
    }
  }
  return { version: 10, data: [], ecc: [] }
}

function drawFinder(mod: boolean[][], x: number, y: number) {
  for (let dy = -1; dy <= 7; dy += 1) {
    for (let dx = -1; dx <= 7; dx += 1) {
      const xx = x + dx
      const yy = y + dy
      if (0 <= xx && xx < mod.length && 0 <= yy && yy < mod.length) {
        const dist = Math.max(Math.abs(dx), Math.abs(dy))
        mod[yy][xx] = dist !== 1 && dist !== 5
      }
    }
  }
}

function drawFormatBits(mod: boolean[][], ecc: QrEcc, mask: number) {
  const data = (ECC_LEVELS[ecc].formatBits << 3) | mask
  let rem = data
  for (let i = 0; i < 10; i += 1) rem = (rem << 1) ^ ((rem >>> 9) * 0x537)
  const bits = ((data << 10) | rem) ^ 0x5412
  const size = mod.length
  for (let i = 0; i <= 5; i += 1) mod[8][i] = ((bits >>> i) & 1) !== 0
  mod[8][7] = ((bits >>> 6) & 1) !== 0
  mod[8][8] = ((bits >>> 7) & 1) !== 0
  mod[7][8] = ((bits >>> 8) & 1) !== 0
  for (let i = 9; i < 15; i += 1) mod[14 - i][8] = ((bits >>> i) & 1) !== 0
  for (let i = 0; i < 8; i += 1) mod[size - 1 - i][8] = ((bits >>> i) & 1) !== 0
  for (let i = 8; i < 15; i += 1) mod[8][size - 15 + i] = ((bits >>> i) & 1) !== 0
  mod[8][size - 8] = true
}

function applyMask(mod: boolean[][], mask: number) {
  const size = mod.length
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      let invert = false
      if (mask === 0) invert = (x + y) % 2 === 0
      if (mask === 1) invert = y % 2 === 0
      if (mask === 2) invert = x % 3 === 0
      if (mask === 3) invert = (x + y) % 3 === 0
      if (invert) mod[y][x] = !mod[y][x]
    }
  }
}

export function createQrSvg(text: string, size = 160, ecc: QrEcc = 'medium') {
  const { version, data, ecc: eccBytes } = buildCodewords(text, ecc)
  const sizeModules = version * 4 + 17
  const mod: boolean[][] = Array.from({ length: sizeModules }, () => Array.from({ length: sizeModules }, () => false))
  drawFinder(mod, 0, 0)
  drawFinder(mod, sizeModules - 7, 0)
  drawFinder(mod, 0, sizeModules - 7)

  let i = 0
  let dir = -1
  const codewords = data.concat(eccBytes)
  for (let x = sizeModules - 1; x >= 1; x -= 2) {
    if (x === 6) x -= 1
    for (let y = 0; y < sizeModules; y += 1) {
      const yy = dir === 1 ? y : sizeModules - 1 - y
      for (let dx = 0; dx < 2; dx += 1) {
        const xx = x - dx
        if (mod[yy][xx]) continue
        const bit = i < codewords.length * 8
          ? (((codewords[Math.floor(i / 8)] >>> (7 - (i % 8))) & 1) !== 0)
          : false
        mod[yy][xx] = bit
        i += 1
      }
    }
    dir = -dir
  }

  const mask = 0
  applyMask(mod, mask)
  drawFormatBits(mod, ecc, mask)

  const cell = Math.max(1, Math.floor(size / sizeModules))
  const dim = cell * sizeModules
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${dim}" height="${dim}" viewBox="0 0 ${dim} ${dim}">`
  svg += `<rect width="100%" height="100%" fill="#fff"/>`
  for (let y = 0; y < sizeModules; y += 1) {
    for (let x = 0; x < sizeModules; x += 1) {
      if (mod[y][x]) svg += `<rect x="${x * cell}" y="${y * cell}" width="${cell}" height="${cell}" fill="#0F172A"/>`
    }
  }
  svg += '</svg>'
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}
