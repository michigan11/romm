<script setup lang="ts">
// v1 copy of the sign-in notice. Closing it records the revision shown.
import type { Emitter } from "mitt";
import { computed, inject, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useTheme } from "vuetify";
import type { AnnouncementSchema } from "@/__generated__";
import announcementApi from "@/services/api/announcement";
import type { Events } from "@/types/emitter";
import {
  AsyncMdPreview as MdPreview,
  loadMdPreview,
} from "@/v2/components/shared/asyncMarkdown";

const { t } = useI18n();
const theme = useTheme();
const emitter = inject<Emitter<Events>>("emitter");
const show = ref(false);
const notice = ref<AnnouncementSchema | null>(null);
const closed = ref(false);
const mdTheme = computed(() =>
  theme.global.current.value.dark ? "dark" : "light",
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

function onModel(open: boolean) {
  if (!open) void acknowledge();
}

async function acknowledge() {
  const current = notice.value;
  if (!current || closed.value) return;
  closed.value = true;
  try {
    await announcementApi.dismiss(current.revision);
    show.value = false;
  } catch (err) {
    console.error(err);
    closed.value = false;
    show.value = true;
    emitter?.emit("snackbarShow", {
      msg: t("common.announcement-dismiss-failed"),
      icon: "mdi-close-circle",
      color: "red",
    });
  }
}
</script>

<template>
  <v-dialog v-model="show" max-width="560" @update:model-value="onModel">
    <v-card v-if="notice">
      <v-card-title>{{ heading }}</v-card-title>
      <v-card-text>
        <MdPreview
          :model-value="notice.message"
          :theme="mdTheme"
          language="en-US"
          preview-theme="vuepress"
          code-theme="github"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" variant="flat" @click="acknowledge">
          {{ t("common.announcement-dismiss") }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
/* md-editor ships its own font stack, white or black surface and grey
   text. Take the card's font and the Vuetify theme colors instead. */
.v-card-text :deep(.md-editor) {
  --md-color: rgb(var(--v-theme-on-surface));
  --md-bk-color: transparent;
  --md-border-color: rgba(var(--v-border-color), var(--v-border-opacity));
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-family: inherit;
}

.v-card-text :deep(.md-editor-preview.vuepress-theme) {
  --md-theme-color: rgb(var(--v-theme-on-surface));
  --md-theme-heading-color: rgb(var(--v-theme-on-surface));
  --md-theme-link-color: rgb(var(--v-theme-primary));
  --md-theme-border-color: rgba(var(--v-border-color), var(--v-border-opacity));
  --md-theme-quote-border: 4px solid rgb(var(--v-theme-secondary));
  --md-theme-table-td-border-color: rgba(
    var(--v-border-color),
    var(--v-border-opacity)
  );
  --md-theme-table-stripe-color: rgb(var(--v-theme-toplayer));
  --md-theme-code-inline-bg-color: rgb(var(--v-theme-toplayer));
  --md-theme-code-block-bg-color: rgb(var(--v-theme-toplayer));
  background: transparent !important;
  color: rgb(var(--v-theme-on-surface));
  font-family: inherit;
  font-size: inherit;
  word-break: break-word;
  padding: 0;
}
</style>
