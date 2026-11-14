<script setup lang="ts">
// v1 editor for the server-wide notice. The same data the v2 tab edits.
import type { Emitter } from "mitt";
import { computed, inject, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { AnnouncementSchema } from "@/__generated__";
import announcementApi from "@/services/api/announcement";
import storeAuth from "@/stores/auth";
import type { Events } from "@/types/emitter";

const { t } = useI18n();
const auth = storeAuth();
const emitter = inject<Emitter<Events>>("emitter");
const isAdmin = computed(() => auth.user?.role === "admin");

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
const loading = ref(true);
const saving = ref(false);
const loadFailed = ref(false);

function apply(value: AnnouncementSchema) {
  saved.value = draftOf(value);
  draft.value = draftOf(value);
}

async function load() {
  loading.value = true;
  loadFailed.value = false;
  try {
    const { data } = await announcementApi.get();
    apply(data);
  } catch (err) {
    console.error(err);
    loadFailed.value = true;
  } finally {
    loading.value = false;
  }
}

const dirty = computed(
  () =>
    draft.value.enabled !== saved.value.enabled ||
    draft.value.title !== saved.value.title ||
    draft.value.message !== saved.value.message,
);
const needsMessage = computed(
  () => draft.value.enabled && draft.value.message.trim() === "",
);

async function save() {
  if (needsMessage.value || saving.value) return;
  saving.value = true;
  try {
    const { data } = await announcementApi.update(draft.value);
    apply(data);
    emitter?.emit("snackbarShow", {
      msg: t("settings.announcement-saved"),
      icon: "mdi-check-bold",
      color: "green",
    });
  } catch (err) {
    console.error(err);
    emitter?.emit("snackbarShow", {
      msg: t("settings.announcement-save-failed"),
      icon: "mdi-close-circle",
      color: "red",
    });
  } finally {
    saving.value = false;
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
      <v-icon class="mr-2" icon="mdi-bullhorn-outline" />
      {{ t("settings.announcement") }}
    </v-card-title>
    <v-card-text>
      <v-progress-linear v-if="loading" indeterminate />
      <v-alert v-else-if="loadFailed" type="error" variant="tonal">
        {{ t("settings.announcement-load-failed") }}
        <v-btn class="ml-2" variant="text" @click="load">
          {{ t("common.try-again") }}
        </v-btn>
      </v-alert>
      <template v-else>
        <v-switch
          :model-value="draft.enabled"
          color="primary"
          @update:model-value="draft.enabled = Boolean($event)"
          :label="t('settings.announcement-enabled')"
          :hint="t('settings.announcement-enabled-hint')"
          persistent-hint
          hide-details="auto"
        />
        <v-text-field
          v-model="draft.title"
          class="mt-4"
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
            needsMessage ? [t('settings.announcement-required')] : []
          "
          persistent-hint
          :maxlength="4000"
          rows="6"
          auto-grow
        />
      </template>
    </v-card-text>
    <v-card-actions v-if="!loading && !loadFailed && dirty">
      <v-spacer />
      <v-btn variant="text" :disabled="saving" @click="draft = { ...saved }">
        {{ t("common.discard") }}
      </v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :loading="saving"
        :disabled="needsMessage"
        @click="save"
      >
        {{ t("common.save") }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
