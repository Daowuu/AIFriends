import { useRouter } from 'vue-router'

import type { Character } from '@/types/character'

export function useCharacterChatNavigation() {
  const router = useRouter()

  const openCharacterChat = async (character: Character) => {
    await router.push({
      name: 'chat',
      params: { characterId: character.id },
      state: {
        from: router.currentRoute.value.fullPath,
        character,
      },
    })
    return character
  }

  return {
    openCharacterChat,
  }
}
