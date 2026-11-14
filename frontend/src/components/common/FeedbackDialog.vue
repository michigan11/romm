<script setup lang="ts">
// v1 send-feedback dialog. The page and version go with the note.
import axios from "axios";
import type { Emitter } from "mitt";
import { computed, inject, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";
import RDialog from "@/components/common/RDialog.vue";
import feedbackApi, {
  FEEDBACK_GAME_TITLE_MAX_LENGTH,
  FEEDBACK_MESSAGE_MAX_LENGTH,
  type FeedbackKind,
} from "@/services/api/feedback";
import storeHeartbeat from "@/stores/heartbeat";
import storePlatforms from "@/stores/platforms";
import type { Events } from "@/types/emitter";

const { t } = useI18n();
const route = useRoute();
const heartbeat = storeHeartbeat();
const platforms = storePlatforms();
const emitter = inject<Emitter<Events>>("emitter");

const show = ref(false);
const sending = ref(false);
const kind = ref<FeedbackKind>("bug");
const message = ref("");
const platformId = ref<number | null>(null);
const gameTitle = ref("");

const kinds: FeedbackKind[] = ["bug", "idea", "other", "request"];
const version = computed(() => heartbeat.value.SYSTEM.VERSION);
const isRequest = computed(() => kind.value === "request");

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

function open() {
  kind.value = "bug";
  message.value = "";
  platformId.value = null;
  gameTitle.value = "";
  show.value = true;
  if (platforms.allPlatforms.length === 0) void platforms.fetchPlatforms();
}

emitter?.on("showFeedbackDialog", open);

watch(kind, (value) => {
  if (value !== "request") {
    platformId.value = null;
    gameTitle.value = "";
  }
});

function notify(msg: string, color: string) {
  emitter?.emit("snackbarShow", {
    msg,
    icon: color === "green" ? "mdi-check-bold" : "mdi-close-circle",
    color,
  });
}

async function submit() {
  if (sending.value || message.value.trim().length === 0) return;
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
    notify(t("settings.feedback-sent"), "green");
    show.value = false;
  } catch (err) {
    console.error(err);
    const limited = axios.isAxiosError(err) && err.response?.status === 429;
    notify(
      limited
        ? t("settings.feedback-rate-limited")
        : t("settings.feedback-send-failed"),
      "red",
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
    scroll-content
    width="480px"
    @close="show = false"
  >
    <template #header>
      <v-toolbar-title class="ml-2">
        {{ t("common.send-feedback") }}
      </v-toolbar-title>
    </template>
    <template #content>
      <v-form class="pa-4" @submit.prevent="submit">
        <v-select
          v-model="kind"
          :items="kindItems"
          :label="t('settings.feedback-kind')"
          variant="outlined"
          hide-details
        />
        <v-textarea
          v-model="message"
          class="mt-4"
          :label="t('settings.feedback-message')"
          :hint="t('settings.feedback-message-hint')"
          persistent-hint
          :maxlength="FEEDBACK_MESSAGE_MAX_LENGTH"
          rows="5"
          auto-grow
          variant="outlined"
        />
        <template v-if="isRequest">
          <v-select
            v-model="platformId"
            class="mt-4"
            :items="platformItems"
            :label="t('settings.feedback-platform')"
            :hint="t('settings.feedback-request-hint')"
            persistent-hint
            clearable
            variant="outlined"
          />
          <v-text-field
            v-model="gameTitle"
            class="mt-4"
            :label="t('settings.feedback-game-title')"
            :maxlength="FEEDBACK_GAME_TITLE_MAX_LENGTH"
            variant="outlined"
            hide-details
          />
        </template>
        <p class="text-caption text-medium-emphasis mt-4 mb-0">
          {{ t("settings.feedback-page") }} {{ route.fullPath }} ·
          {{ t("settings.feedback-version") }} {{ version }}
        </p>
      </v-form>
    </template>
    <template #footer>
      <v-btn
        color="primary"
        variant="flat"
        class="ma-2"
        :loading="sending"
        :disabled="message.trim().length === 0"
        @click="submit"
      >
        {{ t("common.send-feedback") }}
      </v-btn>
    </template>
  </RDialog>
</template>
