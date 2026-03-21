import { createRouter, createWebHistory } from 'vue-router'

import { pinia } from '@/stores'
import { useUserStore } from '@/stores/user'
import FriendsView from '@/views/FriendsView.vue'
import ChatView from '@/views/ChatView.vue'
import CreateCharacterView from '@/views/CreateCharacterView.vue'
import HomeView from '@/views/HomeView.vue'
import ApiSettingsView from '@/views/ApiSettingsView.vue'
import LoginView from '@/views/LoginView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import ProfileView from '@/views/ProfileView.vue'
import RegisterView from '@/views/RegisterView.vue'
import SpaceView from '@/views/SpaceView.vue'
import UpdateCharacterView from '@/views/UpdateCharacterView.vue'
import WorkspaceView from '@/views/WorkspaceView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/friends',
      name: 'friends',
      component: FriendsView,
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/workspace',
      name: 'workspace',
      component: WorkspaceView,
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/settings/api',
      name: 'api-settings',
      component: ApiSettingsView,
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/space/:id',
      name: 'space',
      component: SpaceView,
    },
    {
      path: '/chat/:characterId',
      name: 'chat',
      component: ChatView,
    },
    {
      path: '/characters/create',
      name: 'character-create',
      component: CreateCharacterView,
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/characters/:id/edit',
      name: 'character-edit',
      component: UpdateCharacterView,
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: {
        publicOnly: true,
      },
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: {
        publicOnly: true,
      },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView,
    },
  ],
})

router.beforeEach(async (to) => {
  const user = useUserStore(pinia)

  await user.ensureUserLoaded()

  if (to.meta.requiresAuth && !user.isAuthenticated) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }

  if (to.meta.publicOnly && user.isAuthenticated) {
    return { name: 'home' }
  }

  return true
})

export default router
