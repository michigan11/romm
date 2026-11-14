<script setup lang="ts">
// Administration: v2-native page chrome for the admin-only sections.
// Uses the shared `RTabNav` primitive (same one Library Management
// uses) to expose Users / Groups / Tasks / Streaming as sibling tabs,
// keeping the `?tab=` query param so deep links survive a reload.
//
// Tabs are gated by scope: `users.write` for the groups tab,
// `tasks.run` for the Tasks tab, `app.admin` for Streaming, whose every
// endpoint is admin-only. Users tab is always visible to anyone who can
// reach this route (route-level guard already checks `app.admin`).
import { RTabNav, type RTabNavItem } from "@v2/lib";
import { computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import storeAuth from "@/stores/auth";
import storePermissions from "@/stores/permissions";
import AnnouncementSection from "@/v2/components/Settings/AnnouncementSection.vue";
import CreateUserDialog from "@/v2/components/Settings/CreateUserDialog.vue";
import EditUserDialog from "@/v2/components/Settings/EditUserDialog.vue";
import FeedbackSection from "@/v2/components/Settings/FeedbackSection.vue";
import GroupFormDialog from "@/v2/components/Settings/GroupFormDialog.vue";
import InviteLinkDialog from "@/v2/components/Settings/InviteLinkDialog.vue";
import PermissionGroupsSection from "@/v2/components/Settings/PermissionGroupsSection.vue";
import ScheduledAnnouncementsSection from "@/v2/components/Settings/ScheduledAnnouncementsSection.vue";
import StreamingSection from "@/v2/components/Settings/StreamingSection.vue";
import TasksSection from "@/v2/components/Settings/TasksSection.vue";
import UsersSection from "@/v2/components/Settings/UsersSection.vue";
import { useCan } from "@/v2/composables/useCan";
import { useRouteQueryParam } from "@/v2/composables/useRouteQueryParam";

const { t } = useI18n();
const auth = storeAuth();
const permissions = storePermissions();
const isAdmin = useCan("app.admin");

type Tab =
  "users" | "groups" | "tasks" | "streaming" | "announcement" | "feedback";
const validTabs: readonly Tab[] = [
  "users",
  "groups",
  "tasks",
  "streaming",
  "announcement",
  "feedback",
];

const tab = useRouteQueryParam("tab", "users", validTabs);

const tabs = computed<RTabNavItem[]>(() => {
  const items: RTabNavItem[] = [
    {
      id: "users",
      label: t("settings.users"),
      icon: "mdi-account-group",
    },
  ];
  if (auth.scopes.includes("users.write")) {
    items.push({
      id: "groups",
      label: t("settings.permission-groups"),
      icon: "mdi-shield-lock-outline",
    });
  }
  if (auth.scopes.includes("tasks.run")) {
    items.push({
      id: "tasks",
      label: t("settings.tasks"),
      icon: "mdi-pulse",
    });
  }
  if (isAdmin.value) {
    items.push({
      id: "streaming",
      label: t("settings.streaming"),
      icon: "mdi-monitor-dashboard",
    });
    items.push({
      id: "announcement",
      label: t("settings.announcement"),
      icon: "mdi-bullhorn-outline",
    });
    items.push({
      id: "feedback",
      label: t("settings.feedback"),
      icon: "mdi-message-text-outline",
    });
  }
  return items;
});

// A tab nobody can see is not one the query param may select: the route
// admits `users.write` as well, and Streaming would otherwise deep-link them
// to a panel whose every request 403s.
watch(
  () => [tabs.value, permissions.hydrated] as const,
  ([items, hydrated]) => {
    if (!hydrated) return; // Admin-only tabs appear once permissions load.
    if (!items.some((item) => item.id === tab.value)) tab.value = "users";
  },
  { immediate: true },
);

// Bridge between RTabNav's string modelValue and our Tab union.
const tabModel = computed<string>({
  get: () => tab.value,
  set: (v) => {
    if ((validTabs as readonly string[]).includes(v)) tab.value = v as Tab;
  },
});
</script>

<template>
  <div class="r-v2-section-stack">
    <RTabNav v-model="tabModel" :items="tabs" />

    <UsersSection v-if="tab === 'users'" />
    <PermissionGroupsSection v-else-if="tab === 'groups'" />
    <TasksSection v-else-if="tab === 'tasks'" />
    <StreamingSection v-else-if="tab === 'streaming' && isAdmin" />
    <!-- Stays mounted across tab changes so an unsaved draft is not dropped. -->
    <AnnouncementSection v-if="isAdmin" v-show="tab === 'announcement'" />
    <ScheduledAnnouncementsSection
      v-if="isAdmin"
      v-show="tab === 'announcement'"
    />
    <FeedbackSection v-if="tab === 'feedback' && isAdmin" />

    <CreateUserDialog />
    <EditUserDialog />
    <InviteLinkDialog />
    <GroupFormDialog />
  </div>
</template>
