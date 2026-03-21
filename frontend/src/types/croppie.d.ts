declare module 'croppie' {
  export default class Croppie {
    constructor(element: HTMLElement, options?: Record<string, unknown>)
    bind(options: Record<string, unknown>): Promise<void>
    result(options: Record<string, unknown>): Promise<string>
    destroy(): void
  }
}
