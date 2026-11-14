<script setup lang="ts">
// The server-wide notice. Admins edit it here; everyone else sees it once
// after signing in, and again when the title or message changes.
import { RAlert, RBtn, RSpinner, RTextField } from "@v2/lib";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { onBeforeRouteLeave } from "vue-router";
import type { AnnouncementSchema } from "@/__generated__";
import announcementApi from "@/services/api/announcement";
import SettingsSaveBar from "@/v2/components/Settings/SettingsSaveBar.vue";
import SettingsSection from "@/v2/components/Settings/SettingsSection.vue";
import SettingsToggleRow from "@/v2/components/Settings/SettingsToggleRow.vue";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useFetchState } from "@/v2/composables/useFetchState";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import { useUnloadGuard } from "@/v2/composables/useUnloadGuard";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const confirm = useConfirm();
const snackbar = useSnackbar();

type Draft = { enabled: boolean; title: string; message: string };

const EMPTY: AnnouncementSchema = {
  enabled: false,
  title: "",
  message: "",
  revision: 0,
  pending: false,
};

function draftOf(value: AnnouncementSchema): Draft {
  return { enabled: value.enabled, title: value.title, message: value.message };
}

const saved = ref<Draft>(draftOf(EMPTY));
const draft = ref<Draft>(draftOf(EMPTY));

function apply(value: AnnouncementSchema) {
  saved.value = draftOf(value);
  draft.value = draftOf(value);
}

const {
  isLoading: loading,
  error,
  execute: load,
} = useFetchState(() => announcementApi.get().then(({ data }) => data), EMPTY, {
  onSuccess: apply,
  onError: (err) => {
    console.error(err);
  },
});

const loadFailed = computed(() => error.value !== undefined);
const dirty = computed(
  () =>
    draft.value.enabled !== saved.value.enabled ||
    draft.value.title !== saved.value.title ||
    draft.value.message !== saved.value.message,
);
const needsMessage = computed(
  () => draft.value.enabled && draft.value.message.trim() === "",
);
const saving = ref(false);

async function save() {
  if (needsMessage.value || saving.value) return;
  saving.value = true;
  try {
    const { data } = await announcementApi.update(draft.value);
    apply(data);
    snackbar.success(t("settings.announcement-saved"));
  } catch (err) {
    console.error(err);
    snackbar.error(t("settings.announcement-save-failed"));
  } finally {
    saving.value = false;
  }
}

function discard() {
  draft.value = { ...saved.value };
}

onBeforeRouteLeave(async () => {
  if (!dirty.value) return true;
  return confirm({
    title: t("settings.announcement-leave-title"),
    body: t("settings.announcement-leave-body"),
    confirmText: t("settings.announcement-leave-confirm"),
    tone: "warning",
  });
});

useUnloadGuard(dirty);
</script>

<template>
  <div class="r-v2-announcement">
    <div v-if="loading" class="r-v2-announcement__loading">
      <RSpinner />
    </div>

    <div v-else-if="loadFailed" class="r-v2-announcement__error">
      <RAlert type="error">
        {{ t("settings.announcement-load-failed") }}
      </RAlert>
      <RBtn variant="text" @click="load()">
        {{ t("common.try-again") }}
      </RBtn>
    </div>

    <template v-else>
      <SettingsSection
        :title="t('settings.announcement')"
        icon="mdi-bullhorn-outline"
      >
        <SettingsToggleRow
          v-model="draft.enabled"
          :title="t('settings.announcement-enabled')"
          :description="t('settings.announcement-enabled-hint')"
        />
        <div class="r-v2-announcement__fields">
          <RTextField
            v-model="draft.title"
            :label="t('settings.announcement-title')"
            prefix-label="stacked"
            :maxlength="255"
          />
          <RTextField
            v-model="draft.message"
            :label="t('settings.announcement-message')"
            :hint="t('settings.announcement-message-hint')"
            prefix-label="stacked"
            multiline
            :rows="8"
            :maxlength="4000"
            :error="needsMessage"
            :error-messages="
              needsMessage ? t('settings.announcement-required') : undefined
            "
          />
        </div>
      </SettingsSection>

      <SettingsSaveBar
        :visible="dirty"
        :label="t('settings.announcement-unsaved')"
        :saving="saving"
        :save-disabled="needsMessage"
        @save="save"
        @discard="discard"
      />
    </template>
  </div>
</template>

<style scoped>
.r-v2-announcement {
  padding-bottom: 72px;
}

.r-v2-announcement__loading {
  display: grid;
  place-items: center;
  min-height: 240px;
}

.r-v2-announcement__error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.r-v2-announcement__fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border-top: 1px solid var(--r-color-border);
}
</style>
