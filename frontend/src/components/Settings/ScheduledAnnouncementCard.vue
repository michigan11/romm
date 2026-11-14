<script setup lang="ts">
// v1 editor for scheduled notices. The same data the v2 section edits.
import type { Emitter } from "mitt";
import { computed, inject, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type {
  ScheduledAnnouncementSchema,
  ScheduledAnnouncementWrite,
} from "@/__generated__";
import scheduledAnnouncementsApi from "@/services/api/scheduledAnnouncements";
import storeAuth from "@/stores/auth";
import type { Events } from "@/types/emitter";
import {
  formatLocalDateTime,
  fromDatetimeLocal,
  toDatetimeLocal,
} from "@/utils/localDateTime";

const { t } = useI18n();
const auth = storeAuth();
const emitter = inject<Emitter<Events>>("emitter");
const isAdmin = computed(() => auth.user?.role === "admin");

type Draft = { title: string; message: string; starts: string; ends: string };

const EMPTY_DRAFT: Draft = { title: "", message: "", starts: "", ends: "" };

const schedules = ref<ScheduledAnnouncementSchema[]>([]);
const draft = ref<Draft>({ ...EMPTY_DRAFT });
const editingId = ref<number | null>(null);
const loading = ref(true);
const saving = ref(false);
const loadFailed = ref(false);

function reset() {
  editingId.value = null;
  draft.value = { ...EMPTY_DRAFT };
}

async function load() {
  loading.value = true;
  loadFailed.value = false;
  try {
    const { data } = await scheduledAnnouncementsApi.list();
    schedules.value = data;
  } catch (err) {
    console.error(err);
    loadFailed.value = true;
  } finally {
    loading.value = false;
  }
}

const endBeforeStart = computed(() => {
  if (!draft.value.ends || !draft.value.starts) return false;
  return (
    new Date(draft.value.ends).getTime() <=
    new Date(draft.value.starts).getTime()
  );
});
const canSave = computed(
  () =>
    draft.value.message.trim() !== "" &&
    draft.value.starts !== "" &&
    !endBeforeStart.value,
);

function statusLabel(row: ScheduledAnnouncementSchema): string {
  if (row.ended_at) return t("settings.scheduled-announcements-ended");
  if (row.activated_at) return t("settings.scheduled-announcements-live");
  return t("settings.scheduled-announcements-upcoming");
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

function notify(msg: string, color: "green" | "red") {
  emitter?.emit("snackbarShow", {
    msg,
    icon: color === "green" ? "mdi-check-bold" : "mdi-close-circle",
    color,
  });
}

async function save() {
  if (!canSave.value || saving.value) return;
  const startsAt = fromDatetimeLocal(draft.value.starts);
  const endsAt = draft.value.ends ? fromDatetimeLocal(draft.value.ends) : null;
  if (!startsAt || (draft.value.ends && !endsAt)) return;
  const body: ScheduledAnnouncementWrite = {
    title: draft.value.title,
    message: draft.value.message,
    starts_at: startsAt,
    ends_at: endsAt,
  };
  saving.value = true;
  try {
    if (editingId.value === null) {
      await scheduledAnnouncementsApi.create(body);
    } else {
      await scheduledAnnouncementsApi.update(editingId.value, body);
    }
    reset();
    notify(t("settings.scheduled-announcements-saved"), "green");
    await load();
  } catch (err) {
    console.error(err);
    notify(t("settings.scheduled-announcements-save-failed"), "red");
  } finally {
    saving.value = false;
  }
}

async function remove(row: ScheduledAnnouncementSchema) {
  if (!window.confirm(t("settings.scheduled-announcements-delete-title")))
    return;
  try {
    await scheduledAnnouncementsApi.remove(row.id);
    if (editingId.value === row.id) reset();
    notify(t("settings.scheduled-announcements-deleted"), "green");
    await load();
  } catch (err) {
    console.error(err);
    notify(t("settings.scheduled-announcements-delete-failed"), "red");
  }
}

watch(
  isAdmin,
  (admin) => {
    if (admin) void load();
  },
  { immediate: true },
);
</script>

<template>
  <v-card v-if="isAdmin" class="mt-6" rounded="lg">
    <v-card-title class="d-flex align-center">
      <v-icon class="mr-2" icon="mdi-calendar-clock" />
      {{ t("settings.scheduled-announcements") }}
    </v-card-title>
    <v-card-text>
      <v-progress-linear v-if="loading" indeterminate />
      <v-alert v-else-if="loadFailed" type="error" variant="tonal">
        {{ t("settings.scheduled-announcements-load-failed") }}
        <v-btn class="ml-2" variant="text" @click="load">
          {{ t("common.try-again") }}
        </v-btn>
      </v-alert>
      <template v-else>
        <p class="text-medium-emphasis">
          {{ t("settings.scheduled-announcements-hint") }}
        </p>
        <v-text-field
          v-model="draft.title"
          class="mt-2"
          :label="t('settings.announcement-title')"
          :maxlength="255"
          hide-details="auto"
        />
        <v-textarea
          v-model="draft.message"
          class="mt-4"
          :label="t('settings.announcement-message')"
          :hint="t('settings.announcement-message-hint')"
          :error-messages="
            draft.message.trim() === '' &&
            (draft.starts !== '' || draft.title !== '')
              ? [t('settings.scheduled-announcements-message-required')]
              : []
          "
          persistent-hint
          :maxlength="4000"
          rows="4"
          auto-grow
        />
        <v-text-field
          v-model="draft.starts"
          class="mt-4"
          type="datetime-local"
          :label="t('settings.scheduled-announcements-starts')"
          :error-messages="
            draft.starts === '' && draft.message.trim() !== ''
              ? [t('settings.scheduled-announcements-start-required')]
              : []
          "
          hide-details="auto"
        />
        <v-text-field
          v-model="draft.ends"
          class="mt-4"
          type="datetime-local"
          :label="t('settings.scheduled-announcements-ends')"
          :hint="t('settings.scheduled-announcements-ends-hint')"
          :error-messages="
            endBeforeStart
              ? [t('settings.scheduled-announcements-end-before-start')]
              : []
          "
          persistent-hint
          clearable
        />
        <div v-if="schedules.length === 0" class="mt-6 text-medium-emphasis">
          {{ t("settings.scheduled-announcements-empty") }}
        </div>
        <v-list v-else class="mt-4" lines="two">
          <v-list-item v-for="row in schedules" :key="row.id">
            <v-list-item-title>
              {{ row.title || row.message }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ statusLabel(row) }}
              {{ formatLocalDateTime(row.starts_at) }}
              <template v-if="row.ends_at">
                - {{ formatLocalDateTime(row.ends_at) }}
              </template>
            </v-list-item-subtitle>
            <template v-if="!row.activated_at" #append>
              <v-btn variant="text" @click="edit(row)">
                {{ t("common.edit") }}
              </v-btn>
              <v-btn variant="text" @click="remove(row)">
                {{ t("common.delete") }}
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </template>
    </v-card-text>
    <v-card-actions v-if="!loading && !loadFailed">
      <v-spacer />
      <v-btn
        v-if="editingId !== null || draft.message || draft.starts"
        variant="text"
        :disabled="saving"
        @click="reset"
      >
        {{ t("common.discard") }}
      </v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :loading="saving"
        :disabled="!canSave"
        @click="save"
      >
        {{
          editingId === null
            ? t("settings.scheduled-announcements-schedule")
            : t("common.save")
        }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
