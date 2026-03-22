import { useRoute, useRouter } from 'vue-router'

import api from '@/api/http'
import { useUserStore } from '@/stores/user'
import type { Character } from '@/types/character'
import type { Friend } from '@/types/friend'

export const useCharacterChatNavigation = () => {
  const route = useRoute()
  const router = useRouter()
  const user = useUserStore()

  const ensureChatCharacter = async (character: Character) => {
    if (!user.isAuthenticated) {
      await router.push({
        name: 'chat',
        params: { characterId: character.id },
        state: { character: JSON.parse(JSON.stringify(character)) as Character, from: route.fullPath },
      })
      return null
    }

    if (character.friend_id) {
      return character
    }

    const response = await api.post<{ friend: Friend }>('/friend/get_or_create/', {
      character_id: character.id,
    })

    return {
      ...character,
      friend_id: response.data.friend.id,
    }
  }

  const openCharacterChat = async (character: Character) => {
    const nextCharacter = await ensureChatCharacter(character)
    if (!nextCharacter) return null

    const stateCharacter = JSON.parse(JSON.stringify(nextCharacter)) as Character

    await router.push({
      name: 'chat',
      params: { characterId: nextCharacter.id },
      state: { character: stateCharacter, from: route.fullPath },
    })

    return nextCharacter
  }

  return {
    ensureChatCharacter,
    openCharacterChat,
  }
}
