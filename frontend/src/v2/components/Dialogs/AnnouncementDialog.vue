<script setup lang="ts">
// Shown once after sign-in when an admin has published a notice, and again
// after the title or message changes. Closing it records the revision shown.
import { RBtn, RDialog } from "@v2/lib";
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { AnnouncementSchema } from "@/__generated__";
import announcementApi from "@/services/api/announcement";
import {
  AsyncMdPreview as MdPreview,
  loadMdPreview,
} from "@/v2/components/shared/asyncMarkdown";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import { useThemeMode } from "@/v2/composables/useThemeMode";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const snackbar = useSnackbar();
const { isLight } = useThemeMode();

const show = ref(false);
const dismissing = ref(false);
const notice = ref<AnnouncementSchema | null>(null);
const mdTheme = computed<"light" | "dark">(() =>
  isLight.value ? "light" : "dark",
);
const heading = computed(
  () => notice.value?.title || t("settings.announcement"),
);

onMounted(async () => {
  try {
    const { data } = await announcementApi.get();
    if (!data.pending || !data.message) return;
    await loadMdPreview();
    notice.value = data;
    show.value = true;
  } catch (err) {
    console.error(err);
  }
});

async function acknowledge() {
  const current = notice.value;
  if (!current || dismissing.value) return;
  dismissing.value = true;
  try {
    await announcementApi.dismiss(current.revision);
    show.value = false;
  } catch (err) {
    console.error(err);
    show.value = true;
    snackbar.error(t("common.announcement-dismiss-failed"));
  } finally {
    dismissing.value = false;
  }
}
</script>

<template>
  <RDialog
    v-model="show"
    icon="mdi-bullhorn-outline"
    width="560"
    scroll-content
    :aria-label="heading"
    @close="acknowledge"
  >
    <template #header>
      <span>{{ heading }}</span>
    </template>
    <template #content>
      <MdPreview
        v-if="notice"
        :model-value="notice.message"
        :theme="mdTheme"
        language="en-US"
        preview-theme="vuepress"
        code-theme="github"
        class="r-v2-announcement-dialog__body"
      />
    </template>
    <template #footer>
      <RBtn
        variant="flat"
        color="primary"
        :loading="dismissing"
        @click="acknowledge"
      >
        {{ t("common.announcement-dismiss") }}
      </RBtn>
    </template>
  </RDialog>
</template>

<style scoped>
/* The class lands on md-editor's own root, which ships its own font stack,
   surface and colors. Point md-editor's theme variables at the app tokens so
   the notice reads like the body of the other v2 dialogs (ConfirmDialog). */
.r-v2-announcement-dialog__body.md-editor {
  --md-color: var(--r-color-fg-secondary);
  --md-bk-color: transparent;
  --md-border-color: var(--r-color-border);
  min-width: 0;
  background: transparent;
  color: var(--r-color-fg-secondary);
  font-family: var(--r-font-family-sans);
}

.r-v2-announcement-dialog__body :deep(.md-editor-preview-wrapper) {
  background: transparent;
  color: var(--r-color-fg-secondary);
  padding: 0;
}

.r-v2-announcement-dialog__body :deep(.md-editor-preview.vuepress-theme) {
  --md-theme-color: var(--r-color-fg-secondary);
  --md-theme-heading-color: var(--r-color-fg-heading);
  --md-theme-link-color: var(--r-color-brand-primary);
  --md-theme-border-color: var(--r-color-border);
  --md-theme-quote-border: 4px solid var(--r-color-border-strong);
  --md-theme-table-td-border-color: var(--r-color-border);
  --md-theme-table-stripe-color: var(--r-color-surface);
  --md-theme-code-inline-color: var(--r-color-fg);
  --md-theme-code-block-color: var(--r-color-fg);
  background: transparent !important;
  color: var(--r-color-fg-secondary);
  font-family: var(--r-font-family-sans);
  font-size: var(--r-font-size-md);
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: var(--r-line-height-normal);
  padding: 0;
}

.r-v2-announcement-dialog__body :deep(.md-editor-preview > :first-child) {
  margin-top: 0;
}

.r-v2-announcement-dialog__body :deep(.md-editor-preview > :last-child) {
  margin-bottom: 0;
}

.r-v2-announcement-dialog__body :deep(.md-editor-preview pre) {
  white-space: pre-wrap;
  word-break: break-word;
  max-width: 100%;
}

.r-v2-announcement-dialog__body :deep(.md-editor-preview img) {
  max-width: 100%;
  height: auto;
}

.r-v2-announcement-dialog__body :deep(.md-editor-preview a) {
  color: var(--r-color-brand-primary);
}

.r-v2-announcement-dialog__body :deep(.md-editor-preview code),
.r-v2-announcement-dialog__body :deep(.md-editor-preview pre) {
  background: var(--r-color-surface) !important;
  color: var(--r-color-fg) !important;
  font-family: var(--r-font-family-mono);
}
</style>
