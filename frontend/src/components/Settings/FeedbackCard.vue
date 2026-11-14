<script setup lang="ts">
// v1 admin list of notes, newest first, filterable by kind.
import type { Emitter } from "mitt";
import { computed, inject, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import feedbackApi, {
  type FeedbackKind,
  type FeedbackSchema,
} from "@/services/api/feedback";
import storeAuth from "@/stores/auth";
import type { Events } from "@/types/emitter";
import { formatRelativeDate } from "@/utils";

const PAGE_SIZE = 100;

const { t } = useI18n();
const auth = storeAuth();
const emitter = inject<Emitter<Events>>("emitter");
const isAdmin = computed(() => auth.user?.role === "admin");

const kinds: FeedbackKind[] = ["bug", "idea", "other", "request"];
const kind = ref<FeedbackKind | "">("");
const items = ref<FeedbackSchema[]>([]);
const total = ref(0);
const loading = ref(false);
const loadingMore = ref(false);
const loadFailed = ref(false);
const busyId = ref<number | null>(null);
const pendingDelete = ref<FeedbackSchema | null>(null);

const kindItems = computed(() => [
  { title: t("common.all"), value: "" },
  ...kinds.map((value) => ({
    title: t(`settings.feedback-kind-${value}`),
    value,
  })),
]);

const hasMore = computed(() => items.value.length < total.value);

function notify(msg: string, color: string) {
  emitter?.emit("snackbarShow", {
    msg,
    icon: color === "green" ? "mdi-check-bold" : "mdi-close-circle",
    color,
  });
}

function listParams(offset: number, selected: FeedbackKind | "" = kind.value) {
  return {
    ...(selected ? { kind: selected } : {}),
    limit: PAGE_SIZE,
    offset,
  };
}

async function load() {
  loading.value = true;
  loadFailed.value = false;
  try {
    const { data } = await feedbackApi.list(listParams(0));
    items.value = data.items;
    total.value = data.total;
  } catch (err) {
    console.error(err);
    items.value = [];
    total.value = 0;
    loadFailed.value = true;
  } finally {
    loading.value = false;
  }
}

async function showMore() {
  if (loadingMore.value || !hasMore.value) return;
  const requested = kind.value;
  loadingMore.value = true;
  try {
    const { data } = await feedbackApi.list(
      listParams(items.value.length, requested),
    );
    if (requested !== kind.value) return;
    items.value = [...items.value, ...data.items];
    total.value = data.total;
  } catch (err) {
    console.error(err);
    notify(t("settings.feedback-load-failed"), "red");
  } finally {
    loadingMore.value = false;
  }
}

async function setResolved(item: FeedbackSchema, resolved: boolean) {
  if (busyId.value !== null) return;
  busyId.value = item.id;
  try {
    const { data } = await feedbackApi.update(item.id, { resolved });
    items.value = items.value.map((row) => (row.id === data.id ? data : row));
  } catch (err) {
    console.error(err);
    notify(t("settings.feedback-update-failed"), "red");
  } finally {
    busyId.value = null;
  }
}

async function confirmDelete() {
  const item = pendingDelete.value;
  if (!item || busyId.value !== null) return;
  busyId.value = item.id;
  try {
    await feedbackApi.remove(item.id);
    items.value = items.value.filter((row) => row.id !== item.id);
    total.value = Math.max(0, total.value - 1);
    pendingDelete.value = null;
    notify(t("settings.feedback-deleted"), "green");
  } catch (err) {
    console.error(err);
    notify(t("settings.feedback-delete-failed"), "red");
  } finally {
    busyId.value = null;
  }
}

watch(kind, () => {
  if (isAdmin.value) void load();
});

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
    <v-card-title>{{ t("settings.feedback") }}</v-card-title>
    <v-card-text>
      <v-select
        v-model="kind"
        :items="kindItems"
        :label="t('settings.feedback-filter')"
        variant="outlined"
        hide-details
        style="max-width: 280px"
      />

      <div v-if="loading" class="d-flex justify-center py-8">
        <v-progress-circular indeterminate color="primary" />
      </div>
      <v-alert v-else-if="loadFailed" type="error" class="mt-4" variant="tonal">
        {{ t("settings.feedback-load-failed") }}
        <template #append>
          <v-btn variant="text" @click="load">{{
            t("common.try-again")
          }}</v-btn>
        </template>
      </v-alert>
      <p v-else-if="items.length === 0" class="text-medium-emphasis mt-4 mb-0">
        {{ t("settings.feedback-empty") }}
      </p>

      <template v-else>
        <div v-for="item in items" :key="item.id" class="py-4">
          <div class="d-flex flex-wrap align-center ga-2">
            <v-chip size="small" label>
              {{ t(`settings.feedback-kind-${item.kind}`) }}
            </v-chip>
            <v-chip
              size="small"
              label
              :color="item.resolved ? 'success' : undefined"
            >
              {{
                item.resolved
                  ? t("settings.feedback-resolved")
                  : t("settings.feedback-unresolved")
              }}
            </v-chip>
            <span class="font-weight-medium">{{ item.username }}</span>
            <span class="text-caption text-medium-emphasis">
              {{ formatRelativeDate(item.created_at) }}
            </span>
          </div>
          <p v-if="item.platform_name || item.game_title" class="mt-2 mb-0">
            <span v-if="item.platform_name" class="mr-3">{{
              item.platform_name
            }}</span>
            <span v-if="item.game_title">{{ item.game_title }}</span>
          </p>
          <p class="mt-2 mb-0" style="white-space: pre-wrap">
            {{ item.message }}
          </p>
          <p class="text-caption text-medium-emphasis mt-2 mb-0">
            {{ t("settings.feedback-page") }} {{ item.page_path }} ·
            {{ t("settings.feedback-version") }} {{ item.app_version }}
          </p>
          <div class="d-flex ga-2 mt-2">
            <v-btn
              variant="text"
              size="small"
              :loading="busyId === item.id"
              @click="setResolved(item, !item.resolved)"
            >
              {{
                item.resolved
                  ? t("settings.feedback-mark-unresolved")
                  : t("settings.feedback-mark-resolved")
              }}
            </v-btn>
            <v-btn
              variant="text"
              size="small"
              color="error"
              :disabled="busyId === item.id"
              @click="pendingDelete = item"
            >
              {{ t("common.delete") }}
            </v-btn>
          </div>
        </div>

        <div v-if="hasMore" class="d-flex justify-center">
          <v-btn variant="text" :loading="loadingMore" @click="showMore">
            {{ t("settings.feedback-show-more") }}
          </v-btn>
        </div>
      </template>
    </v-card-text>

    <v-dialog :model-value="pendingDelete !== null" max-width="420" persistent>
      <v-card>
        <v-card-title>{{ t("settings.feedback-delete-title") }}</v-card-title>
        <v-card-text>{{ t("settings.feedback-delete-body") }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            :disabled="busyId !== null"
            @click="pendingDelete = null"
          >
            {{ t("common.cancel") }}
          </v-btn>
          <v-btn
            color="error"
            variant="flat"
            :loading="busyId !== null"
            @click="confirmDelete"
          >
            {{ t("common.delete") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>
