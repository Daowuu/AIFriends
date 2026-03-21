<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div data-theme="cupcake" class="min-h-screen">
    <div class="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-4 sm:px-6 lg:px-8">
      <header class="navbar rounded-box border border-base-200 bg-base-100/80 px-4 shadow-sm backdrop-blur">
        <div class="navbar-start gap-2">
          <div class="dropdown lg:hidden">
            <label tabindex="0" class="btn btn-ghost btn-square">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                class="inline-block h-5 w-5 stroke-current"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </label>
            <ul
              tabindex="0"
              class="menu dropdown-content z-20 mt-3 w-56 rounded-box border border-base-200 bg-base-100 p-2 shadow"
            >
              <li>
                <RouterLink to="/" exact-active-class="active">Home</RouterLink>
              </li>
              <li>
                <RouterLink to="/friends" active-class="active">Friends</RouterLink>
              </li>
              <li>
                <RouterLink to="/workspace" active-class="active">Workspace</RouterLink>
              </li>
            </ul>
          </div>

          <RouterLink to="/" class="flex items-center gap-3">
            <div
              class="grid h-11 w-11 place-items-center rounded-2xl bg-primary text-sm font-black tracking-[0.2em] text-primary-content shadow-sm"
            >
              AI
            </div>
            <div>
              <p class="text-lg font-black tracking-tight text-base-content">AIFrients</p>
              <p class="text-xs uppercase tracking-[0.24em] text-base-content/45">Merged Stack</p>
            </div>
          </RouterLink>
        </div>

        <div class="navbar-center hidden lg:flex">
          <ul class="menu menu-horizontal gap-2 rounded-full border border-base-200 bg-base-200/60 p-1">
            <li>
              <RouterLink
                to="/"
                class="rounded-full px-4"
                active-class="active"
                exact-active-class="active"
              >
                Home
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/friends" class="rounded-full px-4" active-class="active">
                Friends
              </RouterLink>
            </li>
            <li>
              <RouterLink to="/workspace" class="rounded-full px-4" active-class="active">
                Workspace
              </RouterLink>
            </li>
          </ul>
        </div>

        <div class="navbar-end">
          <div class="badge badge-primary badge-outline gap-2 px-3 py-3">
            <span class="h-2 w-2 rounded-full bg-success"></span>
            Django + Vue
          </div>
        </div>
      </header>

      <RouterView />
    </div>
  </div>
</template>
