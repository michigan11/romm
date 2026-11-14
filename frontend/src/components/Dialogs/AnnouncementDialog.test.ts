import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AnnouncementSchema } from "@/__generated__";
import AnnouncementDialog from "./AnnouncementDialog.vue";

const { get, dismiss, error } = vi.hoisted(() => ({
  get: vi.fn(),
  dismiss: vi.fn(),
  error: vi.fn(),
}));

vi.mock("@/services/api/announcement", () => ({
  default: { get, dismiss, update: vi.fn() },
}));

vi.mock("vue-i18n");
vi.mock("@/composables/useSnackbar", () => ({
  useSnackbar: () => ({ error }),
}));
vi.mock("@/composables/useThemeMode", () => ({
  useThemeMode: () => ({ isLight: { value: false } }),
}));
vi.mock("@/components/shared/asyncMarkdown", () => ({
  AsyncMdPreview: {
    name: "MdPreview",
    props: ["modelValue"],
    template: `<div class="md">{{ modelValue }}</div>`,
  },
  loadMdPreview: () => Promise.resolve(),
}));

function notice(
  overrides: Partial<AnnouncementSchema> = {},
): AnnouncementSchema {
  return {
    enabled: true,
    title: "Heads up",
    message: "PS2 games stream.",
    revision: 4,
    pending: true,
    ...overrides,
  };
}

const RDialogStub = {
  name: "RDialog",
  props: ["modelValue"],
  template: `<div v-if="modelValue"><slot name="header" /><slot name="content" /><slot name="footer" /></div>`,
};

const RBtnStub = {
  name: "RBtn",
  template: `<button class="dismiss" @click="$emit('click')"><slot /></button>`,
};

async function mountDialog() {
  const wrapper = mount(AnnouncementDialog, {
    global: {
      stubs: {
        RDialog: RDialogStub,
        RBtn: RBtnStub,
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe("AnnouncementDialog", () => {
  beforeEach(() => {
    get.mockReset();
    dismiss.mockReset();
    error.mockReset();
    dismiss.mockResolvedValue({});
  });

  it("shows a pending notice and records the revision on dismiss", async () => {
    get.mockResolvedValue({ data: notice() });
    const wrapper = await mountDialog();

    expect(wrapper.find(".md").text()).toBe("PS2 games stream.");
    expect(wrapper.text()).toContain("Heads up");

    await wrapper.find(".dismiss").trigger("click");
    await flushPromises();

    expect(dismiss).toHaveBeenCalledWith(4);
    expect(wrapper.find(".md").exists()).toBe(false);
  });

  it("stays closed when the caller has already dismissed it", async () => {
    get.mockResolvedValue({ data: notice({ pending: false }) });
    const wrapper = await mountDialog();

    expect(wrapper.find(".md").exists()).toBe(false);
    expect(dismiss).not.toHaveBeenCalled();
  });
});
