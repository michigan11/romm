<script setup lang="ts">
// Shown once after sign-in when an admin has published a notice, and again
// after the title or message changes. Closing it records the revision shown.
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { AnnouncementSchema } from "@/__generated__";
import {
  AsyncMdPreview as MdPreview,
  loadMdPreview,
} from "@/components/shared/asyncMarkdown";
import { useSnackbar } from "@/composables/useSnackbar";
import { useThemeMode } from "@/composables/useThemeMode";
import { RBtn, RDialog } from "@/lib";
import announcementApi from "@/services/api/announcement";

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
        class="r-announcement-dialog__body"
      />
    </template>
    <template #footer>
      <RBtn
        variant="flat"
        color="primary"
        autofocus
        :loading="dismissing"
        @click="acknowledge"
      >
        {{ t("common.announcement-dismiss") }}
      </RBtn>
    </template>
  </RDialog>
</template>

<style scoped>
.r-announcement-dialog__body {
  min-width: 0;
  border-radius: var(--r-radius-lg);
  background: var(--r-color-bg-elevated);
  padding: 4px 16px;
}

.r-announcement-dialog__body :deep(.md-editor),
.r-announcement-dialog__body :deep(.md-editor-preview-wrapper) {
  background: transparent;
  color: var(--r-color-fg);
  padding: 0;
}

.r-announcement-dialog__body :deep(.md-editor-preview) {
  background: transparent !important;
  color: var(--r-color-fg);
  font-family: inherit;
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: 1.55;
  padding: 0;
}

.r-announcement-dialog__body :deep(.md-editor-preview pre) {
  white-space: pre-wrap;
  word-break: break-word;
  max-width: 100%;
}

.r-announcement-dialog__body :deep(.md-editor-preview img) {
  max-width: 100%;
  height: auto;
}

.r-announcement-dialog__body :deep(.md-editor-preview a) {
  color: var(--r-color-brand-primary);
}

.r-announcement-dialog__body :deep(.md-editor-preview code),
.r-announcement-dialog__body :deep(.md-editor-preview pre) {
  background: color-mix(in srgb, black 30%, transparent) !important;
  color: var(--r-color-fg) !important;
}
</style>
