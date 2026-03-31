declare module 'pdfjs-dist/legacy/build/pdf' {
  export const GlobalWorkerOptions: { workerSrc: string }
  export function getDocument(src: unknown): any
}
