<script setup lang="ts">
// Schedules that replace the current announcement at a start time.
import { RAlert, RBtn, RForm, RSpinner, RTextField } from "@v2/lib";
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { onBeforeRouteLeave } from "vue-router";
import type {
  ScheduledAnnouncementSchema,
  ScheduledAnnouncementWrite,
} from "@/__generated__";
import scheduledAnnouncementsApi from "@/services/api/scheduledAnnouncements";
import {
  formatLocalDateTime,
  fromDatetimeLocal,
  toDatetimeLocal,
} from "@/utils/localDateTime";
import SettingsSection from "@/v2/components/Settings/SettingsSection.vue";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useFetchState } from "@/v2/composables/useFetchState";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import { useUnloadGuard } from "@/v2/composables/useUnloadGuard";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const confirm = useConfirm();
const snackbar = useSnackbar();

type Draft = { title: string; message: string; starts: string; ends: string };

const EMPTY_DRAFT: Draft = { title: "", message: "", starts: "", ends: "" };

const draft = ref<Draft>({ ...EMPTY_DRAFT });
const editingId = ref<number | null>(null);
const saving = ref(false);

const {
  state: schedules,
  isLoading: loading,
  error,
  execute: load,
} = useFetchState(
  () => scheduledAnnouncementsApi.list().then(({ data }) => data),
  [] as ScheduledAnnouncementSchema[],
  {
    onError: (err) => {
      console.error(err);
    },
  },
);

const loadFailed = computed(() => error.value !== undefined);
const endBeforeStart = computed(() => {
  if (!draft.value.ends || !draft.value.starts) return false;
  return (
    new Date(draft.value.ends).getTime() <=
    new Date(draft.value.starts).getTime()
  );
});
const messageMissing = computed(() => draft.value.message.trim() === "");
const startMissing = computed(() => draft.value.starts === "");
const canSave = computed(
  () => !messageMissing.value && !startMissing.value && !endBeforeStart.value,
);
const dirty = computed(
  () =>
    editingId.value !== null ||
    draft.value.title !== "" ||
    draft.value.message !== "" ||
    draft.value.starts !== "" ||
    draft.value.ends !== "",
);

function reset() {
  editingId.value = null;
  draft.value = { ...EMPTY_DRAFT };
}

type StatusKey =
  | "settings.scheduled-announcements-ended"
  | "settings.scheduled-announcements-live"
  | "settings.scheduled-announcements-upcoming";

function statusKey(row: ScheduledAnnouncementSchema): StatusKey {
  if (row.ended_at) return "settings.scheduled-announcements-ended";
  if (row.activated_at) return "settings.scheduled-announcements-live";
  return "settings.scheduled-announcements-upcoming";
}

function edit(row: ScheduledAnnouncementSchema) {
  editingId.value = row.id;
  draft.value = {
    title: row.title,
    message: row.message,
    starts: toDatetimeLocal(row.starts_at),
    ends: row.ends_at ? toDatetimeLocal(row.ends_at) : "",
  };
}

function payload(): ScheduledAnnouncementWrite | null {
  const startsAt = fromDatetimeLocal(draft.value.starts);
  if (!canSave.value || startsAt === "") return null;
  const endsAt = draft.value.ends ? fromDatetimeLocal(draft.value.ends) : null;
  if (draft.value.ends && !endsAt) return null;
  return {
    title: draft.value.title,
    message: draft.value.message,
    starts_at: startsAt,
    ends_at: endsAt,
  };
}

async function save() {
  const body = payload();
  if (!body || saving.value) return;
  saving.value = true;
  try {
    if (editingId.value === null) {
      await scheduledAnnouncementsApi.create(body);
    } else {
      await scheduledAnnouncementsApi.update(editingId.value, body);
    }
    reset();
    snackbar.success(t("settings.scheduled-announcements-saved"));
    await load();
  } catch (err) {
    console.error(err);
    snackbar.error(t("settings.scheduled-announcements-save-failed"));
  } finally {
    saving.value = false;
  }
}

async function remove(row: ScheduledAnnouncementSchema) {
  const ok = await confirm({
    title: t("settings.scheduled-announcements-delete-title"),
    body: t("settings.scheduled-announcements-delete-body"),
    confirmText: t("common.delete"),
    tone: "danger",
  });
  if (!ok) return;
  try {
    await scheduledAnnouncementsApi.remove(row.id);
    if (editingId.value === row.id) reset();
    snackbar.success(t("settings.scheduled-announcements-deleted"));
    await load();
  } catch (err) {
    console.error(err);
    snackbar.error(t("settings.scheduled-announcements-delete-failed"));
  }
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
  <div class="r-v2-scheduled">
    <div
      v-if="loading && schedules.length === 0"
      class="r-v2-scheduled__loading"
    >
      <RSpinner />
    </div>

    <div
      v-else-if="loadFailed && schedules.length === 0"
      class="r-v2-scheduled__error"
    >
      <RAlert type="error">
        {{ t("settings.scheduled-announcements-load-failed") }}
      </RAlert>
      <RBtn variant="text" @click="load()">
        {{ t("common.try-again") }}
      </RBtn>
    </div>

    <SettingsSection
      v-else
      :title="t('settings.scheduled-announcements')"
      icon="mdi-calendar-clock"
    >
      <p class="r-v2-scheduled__hint">
        {{ t("settings.scheduled-announcements-hint") }}
      </p>
      <RForm @submit="save">
        <div class="r-v2-scheduled__fields">
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
            :rows="6"
            :maxlength="4000"
            :error="messageMissing && draft.starts !== ''"
            :error-messages="
              messageMissing && draft.starts !== ''
                ? t('settings.scheduled-announcements-message-required')
                : undefined
            "
          />
          <RTextField
            v-model="draft.starts"
            type="datetime-local"
            :label="t('settings.scheduled-announcements-starts')"
            prefix-label="stacked"
            :error="startMissing && draft.message.trim() !== ''"
            :error-messages="
              startMissing && draft.message.trim() !== ''
                ? t('settings.scheduled-announcements-start-required')
                : undefined
            "
          />
          <RTextField
            v-model="draft.ends"
            type="datetime-local"
            :label="t('settings.scheduled-announcements-ends')"
            :hint="t('settings.scheduled-announcements-ends-hint')"
            prefix-label="stacked"
            clearable
            :error="endBeforeStart"
            :error-messages="
              endBeforeStart
                ? t('settings.scheduled-announcements-end-before-start')
                : undefined
            "
          />
          <div class="r-v2-scheduled__actions">
            <RBtn v-if="dirty" variant="text" type="button" @click="reset">
              {{ t("common.discard") }}
            </RBtn>
            <RBtn
              class="schedule-save"
              variant="flat"
              color="primary"
              type="submit"
              :loading="saving"
              :disabled="!canSave"
            >
              {{
                editingId === null
                  ? t("settings.scheduled-announcements-schedule")
                  : t("common.save")
              }}
            </RBtn>
          </div>
        </div>
      </RForm>

      <p v-if="schedules.length === 0" class="r-v2-scheduled__empty">
        {{ t("settings.scheduled-announcements-empty") }}
      </p>
      <ul v-else class="r-v2-scheduled__list">
        <li v-for="row in schedules" :key="row.id" class="r-v2-scheduled__item">
          <div>
            <div class="r-v2-scheduled__label">
              {{ row.title || row.message }}
            </div>
            <div class="r-v2-scheduled__meta">
              <span class="r-v2-scheduled__status">{{
                t(statusKey(row))
              }}</span>
              {{ formatLocalDateTime(row.starts_at) }}
              <template v-if="row.ends_at">
                - {{ formatLocalDateTime(row.ends_at) }}
              </template>
            </div>
          </div>
          <div v-if="!row.activated_at" class="r-v2-scheduled__actions">
            <RBtn variant="text" type="button" @click="edit(row)">
              {{ t("common.edit") }}
            </RBtn>
            <RBtn
              class="schedule-delete"
              variant="text"
              type="button"
              @click="remove(row)"
            >
              {{ t("common.delete") }}
            </RBtn>
          </div>
        </li>
      </ul>
    </SettingsSection>
  </div>
</template>

<style scoped>
.r-v2-scheduled__loading {
  display: grid;
  place-items: center;
  min-height: 160px;
}

.r-v2-scheduled__error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.r-v2-scheduled__hint,
.r-v2-scheduled__empty {
  margin: 0;
  padding: 16px 16px 0;
  color: var(--r-color-fg-muted);
  font-size: 13px;
}

.r-v2-scheduled__empty {
  padding-bottom: 16px;
}

.r-v2-scheduled__fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.r-v2-scheduled__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.r-v2-scheduled__list {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--r-color-border);
}

.r-v2-scheduled__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--r-color-border);
}

.r-v2-scheduled__item:first-child {
  border-top: none;
}

.r-v2-scheduled__label {
  font-weight: var(--r-font-weight-medium);
}

.r-v2-scheduled__meta {
  color: var(--r-color-fg-muted);
  font-size: 12px;
}

.r-v2-scheduled__status {
  margin-right: 8px;
  font-size: 11px;
  font-weight: var(--r-font-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
