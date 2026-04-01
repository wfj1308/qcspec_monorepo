declare module 'pdfjs-dist/legacy/build/pdf' {
  export const GlobalWorkerOptions: { workerSrc: string }
  export function getDocument(src: unknown): any
}

declare module 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url' {
  const workerUrl: string
  export default workerUrl
}
