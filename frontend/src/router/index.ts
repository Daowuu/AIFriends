import { createRouter, createWebHistory } from 'vue-router'

import ChatView from '@/views/ChatView.vue'
import HomeView from '@/views/HomeView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import StudioView from '@/views/StudioView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/studio',
      name: 'studio',
      component: StudioView,
    },
    {
      path: '/workspace',
      redirect: { name: 'studio' },
    },
    {
      path: '/chat/:characterId',
      name: 'chat',
      component: ChatView,
    },
    {
      path: '/friends',
      redirect: { name: 'home' },
    },
    {
      path: '/profile',
      redirect: { name: 'studio' },
    },
    {
      path: '/settings/api',
      redirect: { name: 'studio' },
    },
    {
      path: '/space/:id',
      redirect: { name: 'home' },
    },
    {
      path: '/login',
      redirect: { name: 'home' },
    },
    {
      path: '/register',
      redirect: { name: 'home' },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView,
    },
  ],
})

export default router
