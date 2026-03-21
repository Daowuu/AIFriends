export function base64ToFile(base64: string, filename: string) {
  const [header, data] = base64.split(',')
  const mime = (header ?? '').match(/:(.*?);/)?.[1] ?? 'image/png'
  const binary = atob(data ?? '')
  const bytes = new Uint8Array(binary.length)

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }

  return new File([bytes], filename, { type: mime })
}
