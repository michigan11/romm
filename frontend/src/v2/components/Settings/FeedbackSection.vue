<script setup lang="ts">
// Admin list of notes, newest first. Kind narrows it to bugs, ideas, or
// game requests.
import { RAlert, RBtn, RChip, REmptyState, RSelect, RSpinner } from "@v2/lib";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import feedbackApi, {
  type FeedbackKind,
  type FeedbackPage,
  type FeedbackSchema,
} from "@/services/api/feedback";
import { formatRelativeDate } from "@/utils";
import SettingsSection from "@/v2/components/Settings/SettingsSection.vue";
import { useConfirm } from "@/v2/composables/useConfirm";
import { useFetchState } from "@/v2/composables/useFetchState";
import { useSnackbar } from "@/v2/composables/useSnackbar";

defineOptions({ inheritAttrs: false });

const PAGE_SIZE = 100;

const { t } = useI18n();
const confirm = useConfirm();
const snackbar = useSnackbar();

const kinds: FeedbackKind[] = ["bug", "idea", "other", "request"];
const kind = ref<FeedbackKind | "">("");
const busyId = ref<number | null>(null);
const loadingMore = ref(false);

const emptyPage: FeedbackPage = {
  items: [],
  total: 0,
  limit: PAGE_SIZE,
  offset: 0,
};

const kindItems = computed(() => [
  { title: t("common.all"), value: "" },
  ...kinds.map((value) => ({
    title: t(`settings.feedback-kind-${value}`),
    value,
  })),
]);

function listParams(offset: number, selected: FeedbackKind | "") {
  return {
    ...(selected ? { kind: selected } : {}),
    limit: PAGE_SIZE,
    offset,
  };
}

function kindColor(value: FeedbackKind): string {
  if (value === "bug") return "danger";
  if (value === "request") return "warning";
  if (value === "idea") return "primary";
  return "info";
}

const {
  state,
  isLoading,
  error,
  execute: load,
} = useFetchState(
  () => feedbackApi.list(listParams(0, kind.value)).then(({ data }) => data),
  emptyPage,
  {
    onError: (err) => {
      console.error(err);
    },
  },
);

watch(kind, () => {
  void load();
});

const items = computed(() => state.value.items);
const hasMore = computed(() => items.value.length < state.value.total);
const loadFailed = computed(
  () => error.value !== undefined && items.value.length === 0,
);

async function showMore() {
  if (loadingMore.value || !hasMore.value) return;
  const requested = kind.value;
  loadingMore.value = true;
  try {
    const { data } = await feedbackApi.list(
      listParams(state.value.items.length, requested),
    );
    if (requested !== kind.value) return;
    state.value = {
      ...data,
      items: [...state.value.items, ...data.items],
    };
  } catch (err) {
    console.error(err);
    snackbar.error(t("settings.feedback-load-failed"));
  } finally {
    loadingMore.value = false;
  }
}

function replace(updated: FeedbackSchema) {
  state.value = {
    ...state.value,
    items: state.value.items.map((item) =>
      item.id === updated.id ? updated : item,
    ),
  };
}

async function setResolved(item: FeedbackSchema, resolved: boolean) {
  if (busyId.value !== null) return;
  busyId.value = item.id;
  try {
    const { data } = await feedbackApi.update(item.id, { resolved });
    replace(data);
  } catch (err) {
    console.error(err);
    snackbar.error(t("settings.feedback-update-failed"));
  } finally {
    busyId.value = null;
  }
}

async function remove(item: FeedbackSchema) {
  if (busyId.value !== null) return;
  const ok = await confirm({
    title: t("settings.feedback-delete-title"),
    body: t("settings.feedback-delete-body"),
    confirmText: t("common.delete"),
    tone: "danger",
  });
  if (!ok) return;
  busyId.value = item.id;
  try {
    await feedbackApi.remove(item.id);
    state.value = {
      ...state.value,
      total: Math.max(0, state.value.total - 1),
      items: state.value.items.filter((row) => row.id !== item.id),
    };
    snackbar.success(t("settings.feedback-deleted"));
  } catch (err) {
    console.error(err);
    snackbar.error(t("settings.feedback-delete-failed"));
  } finally {
    busyId.value = null;
  }
}
</script>

<template>
  <SettingsSection
    :title="t('settings.feedback')"
    icon="mdi-message-text-outline"
  >
    <div class="r-v2-feedback__filter">
      <RSelect
        v-model="kind"
        :items="kindItems"
        :label="t('settings.feedback-filter')"
        prefix-label="stacked"
        hide-details
      />
    </div>

    <div v-if="isLoading && items.length === 0" class="r-v2-feedback__loading">
      <RSpinner />
    </div>

    <div v-else-if="loadFailed" class="r-v2-feedback__error">
      <RAlert type="error">{{ t("settings.feedback-load-failed") }}</RAlert>
      <RBtn variant="text" @click="load()">{{ t("common.try-again") }}</RBtn>
    </div>

    <REmptyState
      v-else-if="items.length === 0"
      icon="mdi-message-outline"
      :title="t('settings.feedback-empty')"
      variant="plain"
    />

    <ul v-else class="r-v2-feedback__list">
      <li v-for="item in items" :key="item.id" class="r-v2-feedback__item">
        <div class="r-v2-feedback__head">
          <RChip size="small" label :color="kindColor(item.kind)">
            {{ t(`settings.feedback-kind-${item.kind}`) }}
          </RChip>
          <RChip
            size="small"
            label
            :color="item.resolved ? 'success' : undefined"
          >
            {{
              item.resolved
                ? t("settings.feedback-resolved")
                : t("settings.feedback-unresolved")
            }}
          </RChip>
          <span class="r-v2-feedback__who">{{ item.username }}</span>
          <span class="r-v2-feedback__when">
            {{ formatRelativeDate(item.created_at) }}
          </span>
        </div>
        <p
          v-if="item.platform_name || item.game_title"
          class="r-v2-feedback__game"
        >
          <span v-if="item.platform_name">{{ item.platform_name }}</span>
          <span v-if="item.game_title">{{ item.game_title }}</span>
        </p>
        <p class="r-v2-feedback__message">{{ item.message }}</p>
        <p class="r-v2-feedback__meta">
          <span>{{ t("settings.feedback-page") }}</span>
          {{ item.page_path }}
          <span>{{ t("settings.feedback-version") }}</span>
          {{ item.app_version }}
        </p>
        <div class="r-v2-feedback__actions">
          <RBtn
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
          </RBtn>
          <RBtn
            variant="text"
            size="small"
            color="danger"
            :disabled="busyId === item.id"
            @click="remove(item)"
          >
            {{ t("common.delete") }}
          </RBtn>
        </div>
      </li>
      <li v-if="hasMore" class="r-v2-feedback__more">
        <RBtn variant="text" :loading="loadingMore" @click="showMore">
          {{ t("settings.feedback-show-more") }}
        </RBtn>
      </li>
    </ul>
  </SettingsSection>
</template>

<style scoped>
.r-v2-feedback__filter {
  padding: var(--r-space-4);
  border-bottom: 1px solid var(--r-color-border);
  max-width: 280px;
}

.r-v2-feedback__loading {
  display: grid;
  place-items: center;
  min-height: 200px;
}

.r-v2-feedback__error {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--r-space-2);
  padding: var(--r-space-4);
}

.r-v2-feedback__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.r-v2-feedback__item {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-2);
  padding: var(--r-space-4);
  border-top: 1px solid var(--r-color-border);
}

.r-v2-feedback__item:first-child {
  border-top: none;
}

.r-v2-feedback__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--r-space-2);
}

.r-v2-feedback__who {
  font-weight: var(--r-font-weight-semibold);
}

.r-v2-feedback__when,
.r-v2-feedback__meta {
  color: var(--r-color-fg-muted);
  font-size: 12px;
}

.r-v2-feedback__game,
.r-v2-feedback__message,
.r-v2-feedback__meta {
  margin: 0;
}

.r-v2-feedback__game {
  display: flex;
  flex-wrap: wrap;
  gap: var(--r-space-3);
  font-weight: var(--r-font-weight-medium);
}

.r-v2-feedback__message {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.r-v2-feedback__meta {
  overflow-wrap: anywhere;
}

.r-v2-feedback__meta span {
  margin-right: 4px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
}

.r-v2-feedback__meta span + span {
  margin-left: 12px;
}

.r-v2-feedback__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--r-space-2);
}

.r-v2-feedback__more {
  display: flex;
  justify-content: center;
  padding: var(--r-space-2);
  border-top: 1px solid var(--r-color-border);
}
</style>
