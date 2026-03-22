<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

const props = defineProps<{
  content: string
}>()

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})

const defaultLinkOpenRenderer = markdown.renderer.rules.link_open

markdown.renderer.rules.link_open = (
  tokens: any[],
  idx: number,
  options: any,
  env: any,
  self: any,
) => {
  const token = tokens[idx]
  const targetIndex = token.attrIndex('target')
  const relIndex = token.attrIndex('rel')

  if (targetIndex < 0) token.attrPush(['target', '_blank'])
  else token.attrs![targetIndex]![1] = '_blank'

  if (relIndex < 0) token.attrPush(['rel', 'noreferrer noopener'])
  else token.attrs![relIndex]![1] = 'noreferrer noopener'

  if (defaultLinkOpenRenderer) {
    return defaultLinkOpenRenderer(tokens, idx, options, env, self)
  }
  return self.renderToken(tokens, idx, options)
}

const renderedHtml = computed(() => markdown.render(props.content || ''))
</script>

<template>
  <div class="markdown-content" v-html="renderedHtml" />
</template>

<style scoped>
.markdown-content {
  color: inherit;
  word-break: break-word;
}

.markdown-content :deep(p) {
  margin: 0;
}

.markdown-content :deep(p + p),
.markdown-content :deep(p + ul),
.markdown-content :deep(p + ol),
.markdown-content :deep(p + pre),
.markdown-content :deep(ul + p),
.markdown-content :deep(ol + p),
.markdown-content :deep(pre + p),
.markdown-content :deep(blockquote + p),
.markdown-content :deep(p + blockquote) {
  margin-top: 0.75rem;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0.75rem 0 0;
  padding-left: 1.2rem;
}

.markdown-content :deep(li + li) {
  margin-top: 0.3rem;
}

.markdown-content :deep(a) {
  text-decoration: underline;
  text-underline-offset: 0.16rem;
}

.markdown-content :deep(code) {
  border-radius: 0.5rem;
  background: rgba(15, 23, 42, 0.08);
  padding: 0.12rem 0.4rem;
  font-size: 0.92em;
}

.markdown-content :deep(pre) {
  margin: 0.9rem 0 0;
  overflow-x: auto;
  border-radius: 1rem;
  background: rgba(15, 23, 42, 0.08);
  padding: 0.9rem 1rem;
}

.markdown-content :deep(pre code) {
  background: transparent;
  padding: 0;
  font-size: 0.92em;
}

.markdown-content :deep(blockquote) {
  margin: 0.9rem 0 0;
  border-left: 3px solid rgba(15, 23, 42, 0.16);
  padding-left: 0.9rem;
  opacity: 0.9;
}

.markdown-content :deep(hr) {
  margin: 1rem 0;
  border: none;
  border-top: 1px solid rgba(15, 23, 42, 0.12);
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin: 1rem 0 0;
  font-size: 1em;
  font-weight: 700;
}
</style>
