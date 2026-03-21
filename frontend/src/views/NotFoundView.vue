<template>
  <section class="flex min-h-[calc(100vh-74px)] items-center justify-center p-6">
    <div class="w-full max-w-lg rounded-3xl border border-base-200 bg-base-100 p-10 text-center shadow-sm">
      <p class="text-sm font-semibold uppercase tracking-[0.24em] text-base-content/45">404</p>
      <h1 class="mt-3 text-4xl font-black text-base-content">页面不存在</h1>
      <p class="mt-4 text-base-content/60">你访问的前端路由没有对应页面。</p>
      <RouterLink to="/" class="btn btn-primary mt-8">返回首页</RouterLink>
    </div>
  </section>
</template>
