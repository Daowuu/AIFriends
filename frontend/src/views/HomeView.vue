<template>
  <main class="flex-1 py-8">
    <section
      class="hero overflow-hidden rounded-[2rem] border border-base-200 bg-base-100/85 shadow-xl"
    >
      <div class="hero-content w-full flex-col gap-12 px-6 py-10 lg:flex-row lg:px-10 lg:py-14">
        <div class="max-w-2xl">
          <p class="mb-4 text-sm font-semibold uppercase tracking-[0.28em] text-primary">
            One server entry
          </p>
          <h1 class="text-5xl font-black leading-tight text-base-content md:text-6xl">
            Django now serves the Vue app directly.
          </h1>
          <p class="mt-6 max-w-xl text-lg leading-8 text-base-content/70">
            The frontend is mounted under the same backend service. Top-level app routes now share
            one entrypoint, while API endpoints stay under <code>/api/</code>.
          </p>
          <div class="mt-8 flex flex-wrap gap-3">
            <a href="/api/token/" class="btn btn-primary">JWT endpoint</a>
            <a href="/admin/" class="btn btn-outline">Django admin</a>
          </div>
        </div>

        <div class="grid w-full max-w-xl gap-4 md:grid-cols-2">
          <article class="card border border-base-200 bg-base-100 shadow-sm">
            <div class="card-body">
              <p class="text-sm uppercase tracking-[0.2em] text-base-content/50">Navigation</p>
              <p class="card-title text-3xl font-black">App Shell</p>
              <p class="text-base-content/70">A responsive navbar now wraps the SPA layout.</p>
            </div>
          </article>
          <article class="card border border-base-200 bg-base-100 shadow-sm">
            <div class="card-body">
              <p class="text-sm uppercase tracking-[0.2em] text-base-content/50">Routing</p>
              <p class="card-title text-3xl font-black">SPA Fallback</p>
              <p class="text-base-content/70">Direct visits to frontend routes resolve through Django.</p>
            </div>
          </article>
          <article class="card border border-base-200 bg-base-100 shadow-sm md:col-span-2">
            <div class="card-body gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p class="text-sm uppercase tracking-[0.2em] text-base-content/50">Stack status</p>
                <p class="text-xl font-semibold text-base-content">
                  Frontend build artifacts and backend routes are aligned now.
                </p>
              </div>
              <div class="stats border border-base-200 bg-base-200/50 shadow-none">
                <div class="stat px-6">
                  <div class="stat-title">Frontend</div>
                  <div class="stat-value text-2xl">Vue 3</div>
                </div>
                <div class="stat px-6">
                  <div class="stat-title">Backend</div>
                  <div class="stat-value text-2xl">Django</div>
                </div>
                <div class="stat px-6">
                  <div class="stat-title">UI</div>
                  <div class="stat-value text-2xl">daisyUI</div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>
  </main>
</template>
