<script setup lang="ts">
// Opened from the user menu. The page and version go with the note so an
// admin can see where it was sent from.
import { RBtn, RDialog, RForm, RSelect, RTextField } from "@v2/lib";
import axios from "axios";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import feedbackApi, {
  FEEDBACK_GAME_TITLE_MAX_LENGTH,
  FEEDBACK_MESSAGE_MAX_LENGTH,
  type FeedbackKind,
} from "@/services/api/feedback";
import storePlatforms from "@/stores/platforms";
import { useEmitterEvent } from "@/v2/composables/useEmitterEvent";
import { useSnackbar } from "@/v2/composables/useSnackbar";
import { useVersionDisplay } from "@/v2/composables/useVersionDisplay";
import { notBlank } from "@/v2/utils/validation";

defineOptions({ inheritAttrs: false });

const { t } = useI18n();
const route = useRoute();
const snackbar = useSnackbar();
const { version } = useVersionDisplay();
const platforms = storePlatforms();

const show = ref(false);
const sending = ref(false);
const kind = ref<FeedbackKind>("bug");
const message = ref("");
const platformId = ref<number | null>(null);
const gameTitle = ref("");
const form = ref<InstanceType<typeof RForm> | null>(null);

const kinds: FeedbackKind[] = ["bug", "idea", "other", "request"];

const kindItems = computed(() =>
  kinds.map((value) => ({
    title: t(`settings.feedback-kind-${value}`),
    value,
  })),
);

const platformItems = computed(() =>
  platforms.allPlatforms
    .map((platform) => ({ title: platform.display_name, value: platform.id }))
    .sort((a, b) => a.title.localeCompare(b.title)),
);

const isRequest = computed(() => kind.value === "request");

function open() {
  kind.value = "bug";
  message.value = "";
  platformId.value = null;
  gameTitle.value = "";
  show.value = true;
  if (platforms.allPlatforms.length === 0) void platforms.fetchPlatforms();
}

useEmitterEvent("showFeedbackDialog", open);

watch(kind, (value) => {
  if (value !== "request") {
    platformId.value = null;
    gameTitle.value = "";
  }
});

async function submit() {
  if (sending.value) return;
  const result = await form.value?.validate();
  if (!result?.valid) return;
  sending.value = true;
  try {
    await feedbackApi.create({
      kind: kind.value,
      message: message.value.trim(),
      page_path: route.fullPath,
      app_version: version.value,
      platform_id: isRequest.value ? platformId.value : null,
      game_title: isRequest.value ? gameTitle.value.trim() || null : null,
    });
    snackbar.success(t("settings.feedback-sent"));
    show.value = false;
  } catch (err) {
    console.error(err);
    const limited = axios.isAxiosError(err) && err.response?.status === 429;
    snackbar.error(
      limited
        ? t("settings.feedback-rate-limited")
        : t("settings.feedback-send-failed"),
    );
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <RDialog
    v-model="show"
    icon="mdi-message-text-outline"
    width="440px"
    cancelable
    :cancel-disabled="sending"
  >
    <template #header>{{ t("common.send-feedback") }}</template>
    <template #content>
      <RForm ref="form" class="r-v2-feedback-dialog" @submit="submit">
        <RSelect
          v-model="kind"
          :items="kindItems"
          :label="t('settings.feedback-kind')"
          prefix-label="stacked"
          hide-details
        />
        <RTextField
          v-model="message"
          :label="t('settings.feedback-message')"
          :hint="t('settings.feedback-message-hint')"
          prefix-label="stacked"
          multiline
          :rows="5"
          :maxlength="FEEDBACK_MESSAGE_MAX_LENGTH"
          :rules="[notBlank()]"
        />
        <template v-if="isRequest">
          <RSelect
            v-model="platformId"
            :items="platformItems"
            :label="t('settings.feedback-platform')"
            :hint="t('settings.feedback-request-hint')"
            prefix-label="stacked"
            clearable
            searchable
          />
          <RTextField
            v-model="gameTitle"
            :label="t('settings.feedback-game-title')"
            prefix-label="stacked"
            :maxlength="FEEDBACK_GAME_TITLE_MAX_LENGTH"
          />
        </template>
        <p class="r-v2-feedback-dialog__meta">
          <span>{{ t("settings.feedback-page") }}</span>
          {{ route.fullPath }}
          <span>{{ t("settings.feedback-version") }}</span>
          {{ version }}
        </p>
      </RForm>
    </template>
    <template #footer>
      <RBtn
        :loading="sending"
        :disabled="message.trim().length === 0"
        @click="submit"
      >
        {{ t("common.send-feedback") }}
      </RBtn>
    </template>
  </RDialog>
</template>

<style scoped>
.r-v2-feedback-dialog {
  display: flex;
  flex-direction: column;
  gap: var(--r-space-4);
}

.r-v2-feedback-dialog__meta {
  margin: 0;
  color: var(--r-color-fg-muted);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.r-v2-feedback-dialog__meta span {
  display: inline-block;
  margin-right: 6px;
  font-weight: var(--r-font-weight-semibold);
  color: var(--r-color-fg);
}

.r-v2-feedback-dialog__meta span + span {
  margin-left: 12px;
}
</style>
