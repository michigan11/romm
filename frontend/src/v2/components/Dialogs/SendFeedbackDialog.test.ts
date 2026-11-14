import { flushPromises, mount } from "@vue/test-utils";
import mitt from "mitt";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import storeHeartbeat from "@/stores/heartbeat";
import type { Events } from "@/types/emitter";
import SendFeedbackDialog from "./SendFeedbackDialog.vue";

const { create, getPlatforms } = vi.hoisted(() => ({
  create: vi.fn(),
  getPlatforms: vi.fn(),
}));

vi.mock("@/services/api/feedback", async () => {
  const actual = await vi.importActual<
    typeof import("@/services/api/feedback")
  >("@/services/api/feedback");
  return { ...actual, default: { ...actual.default, create } };
});

vi.mock("@/services/api/platform", () => ({
  default: { getPlatforms },
}));

vi.mock("vue-i18n");
vi.mock("vue-router", () => ({
  useRoute: () => ({ fullPath: "/rom/12" }),
}));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const RSelectStub = {
  name: "RSelect",
  props: {
    modelValue: { type: [String, Number], default: "" },
    label: { type: String, default: "" },
    items: { type: Array, default: () => [] },
  },
  emits: ["update:modelValue"],
  template: `<label>{{ label }}<select :value="modelValue" @change="$emit('update:modelValue', $event.target.value)"><option v-for="item in items" :key="String(item.value)" :value="item.value">{{ item.title }}</option></select></label>`,
};

const RTextFieldStub = {
  name: "RTextField",
  props: {
    modelValue: { type: String, default: "" },
    label: { type: String, default: "" },
  },
  emits: ["update:modelValue"],
  template: `<label>{{ label }}<textarea :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" /></label>`,
};

const RFormStub = {
  name: "RForm",
  emits: ["submit"],
  methods: {
    validate: () => Promise.resolve({ valid: true }),
  },
  template: `<form @submit.prevent="$emit('submit', $event)"><slot /></form>`,
};

async function open() {
  const heartbeat = storeHeartbeat();
  heartbeat.value = {
    ...heartbeat.value,
    SYSTEM: { ...heartbeat.value.SYSTEM, VERSION: "5.4.1" },
  };
  const emitter = mitt<Events>();
  const wrapper = mount(SendFeedbackDialog, {
    global: {
      provide: { emitter },
      stubs: {
        RDialog: {
          props: { modelValue: { type: Boolean, default: false } },
          template: `<div v-if="modelValue"><slot name="header" /><slot name="content" /><slot name="footer" /></div>`,
        },
        RSelect: RSelectStub,
        RTextField: RTextFieldStub,
        RForm: RFormStub,
        RBtn: {
          emits: ["click"],
          template: `<button type="button" @click="$emit('click')"><slot /></button>`,
        },
      },
    },
  });
  emitter.emit("showFeedbackDialog", null);
  await nextTick();
  return wrapper;
}

describe("SendFeedbackDialog", () => {
  beforeEach(() => {
    create.mockReset();
    getPlatforms.mockReset();
    getPlatforms.mockResolvedValue({ data: [] });
    create.mockResolvedValue({ data: { id: 1 } });
  });

  it("sends the note with the current page and version", async () => {
    const wrapper = await open();

    const message = wrapper
      .findAll("label")
      .find((label) => label.text().includes("settings.feedback-message"));
    await message!.find("textarea").setValue("The cover never loads.");
    await wrapper.find("button").trigger("click");
    await flushPromises();

    expect(create).toHaveBeenCalledWith({
      kind: "bug",
      message: "The cover never loads.",
      page_path: "/rom/12",
      app_version: "5.4.1",
      platform_id: null,
      game_title: null,
    });
  });

  it("sends a game title when the kind is a request", async () => {
    const wrapper = await open();

    const kind = wrapper
      .findAll("label")
      .find((label) => label.text().includes("settings.feedback-kind"));
    await kind!.find("select").setValue("request");
    await nextTick();

    const title = wrapper
      .findAll("label")
      .find((label) => label.text().includes("settings.feedback-game-title"));
    await title!.find("textarea").setValue("Ico");
    const message = wrapper
      .findAll("label")
      .find((label) => label.text().includes("settings.feedback-message"));
    await message!.find("textarea").setValue("Please add it.");
    await wrapper.find("button").trigger("click");
    await flushPromises();

    expect(create).toHaveBeenCalledWith({
      kind: "request",
      message: "Please add it.",
      page_path: "/rom/12",
      app_version: "5.4.1",
      platform_id: null,
      game_title: "Ico",
    });
  });
});
