import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import type { FeedbackPage } from "@/services/api/feedback";
import FeedbackSection from "./FeedbackSection.vue";

const { list, update } = vi.hoisted(() => ({
  list: vi.fn(),
  update: vi.fn(),
}));

vi.mock("@/services/api/feedback", async () => {
  const actual = await vi.importActual<
    typeof import("@/services/api/feedback")
  >("@/services/api/feedback");
  return {
    ...actual,
    default: { ...actual.default, list, update, remove: vi.fn() },
  };
});

vi.mock("vue-i18n");
vi.mock("@/v2/composables/useConfirm", () => ({
  useConfirm: () => vi.fn(),
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const page: FeedbackPage = {
  items: [
    {
      id: 4,
      user_id: 2,
      username: "ada",
      kind: "bug",
      message: "Cover is blank.",
      page_path: "/gallery",
      app_version: "5.4.1",
      platform_id: null,
      platform_name: null,
      game_title: null,
      resolved: false,
      created_at: "2026-11-14T00:00:00Z",
      updated_at: "2026-11-14T00:00:00Z",
    },
  ],
  total: 1,
  limit: 100,
  offset: 0,
};

const RSelectStub = {
  name: "RSelect",
  props: {
    modelValue: { type: String, default: "" },
    label: { type: String, default: "" },
    items: { type: Array, default: () => [] },
  },
  emits: ["update:modelValue"],
  template: `<label>{{ label }}<select :value="modelValue" @change="$emit('update:modelValue', $event.target.value)"><option v-for="item in items" :key="String(item.value)" :value="item.value">{{ item.title }}</option></select></label>`,
};

async function mountSection() {
  const wrapper = mount(FeedbackSection, {
    global: {
      stubs: {
        RSelect: RSelectStub,
        RSpinner: true,
        RAlert: true,
        REmptyState: true,
        RChip: { template: `<span><slot /></span>` },
        RBtn: {
          emits: ["click"],
          template: `<button type="button" @click="$emit('click')"><slot /></button>`,
        },
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe("FeedbackSection", () => {
  beforeEach(() => {
    list.mockReset();
    update.mockReset();
    list.mockResolvedValue({ data: page });
  });

  it("lists notes and filters them by kind", async () => {
    const wrapper = await mountSection();

    expect(wrapper.text()).toContain("Cover is blank.");
    expect(list).toHaveBeenCalledWith({
      limit: 100,
      offset: 0,
    });

    await wrapper.find("select").setValue("request");
    await nextTick();
    await flushPromises();

    expect(list).toHaveBeenLastCalledWith({
      kind: "request",
      limit: 100,
      offset: 0,
    });
  });

  it("marks a note resolved", async () => {
    update.mockResolvedValue({
      data: { ...page.items[0], resolved: true },
    });
    const wrapper = await mountSection();

    const resolve = wrapper
      .findAll("button")
      .find((button) =>
        button.text().includes("settings.feedback-mark-resolved"),
      );
    await resolve!.trigger("click");
    await flushPromises();

    expect(update).toHaveBeenCalledWith(4, { resolved: true });
    expect(wrapper.text()).toContain("settings.feedback-mark-unresolved");
  });
});
