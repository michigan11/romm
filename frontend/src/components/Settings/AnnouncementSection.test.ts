import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AnnouncementSchema } from "@/__generated__";
import AnnouncementSection from "./AnnouncementSection.vue";

const { get, update, confirm } = vi.hoisted(() => ({
  get: vi.fn(),
  update: vi.fn(),
  confirm: vi.fn(),
}));

vi.mock("@/services/api/announcement", () => ({
  default: { get, update, dismiss: vi.fn() },
}));

vi.mock("vue-i18n");
vi.mock("vue-router", () => ({ onBeforeRouteLeave: vi.fn() }));
vi.mock("@/composables/useConfirm", () => ({ useConfirm: () => confirm }));
vi.mock("@/composables/useSnackbar", () => ({
  useSnackbar: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const notice: AnnouncementSchema = {
  enabled: false,
  title: "",
  message: "",
  revision: 0,
  pending: false,
};

const RTextFieldStub = {
  name: "RTextField",
  props: ["modelValue", "label"],
  emits: ["update:modelValue"],
  template:
    "<label>{{ label }}<textarea :value='modelValue' @input=\"$emit('update:modelValue', $event.target.value)\" /></label>",
};

const SettingsToggleRowStub = {
  name: "SettingsToggleRow",
  props: ["modelValue"],
  emits: ["update:modelValue"],
  template:
    "<button type='button' class='toggle' @click=\"$emit('update:modelValue', !modelValue)\" />",
};

const SettingsSaveBarStub = {
  name: "SettingsSaveBar",
  props: ["visible", "saveDisabled"],
  emits: ["save"],
  template:
    "<div v-if='visible'><button class='save' :disabled='saveDisabled' @click=\"$emit('save')\">save</button></div>",
};

async function mountSection() {
  const wrapper = mount(AnnouncementSection, {
    global: {
      stubs: {
        RTextField: RTextFieldStub,
        SettingsToggleRow: SettingsToggleRowStub,
        SettingsSaveBar: SettingsSaveBarStub,
        RSpinner: true,
        RAlert: true,
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe("AnnouncementSection", () => {
  beforeEach(() => {
    get.mockReset();
    update.mockReset();
    get.mockResolvedValue({ data: notice });
  });

  it("saves a message the admin typed", async () => {
    update.mockImplementation((payload: AnnouncementSchema) => ({
      data: { ...notice, ...payload, revision: 1, pending: true },
    }));
    const wrapper = await mountSection();

    const message = wrapper
      .findAll("label")
      .find((label) => label.text().includes("settings.announcement-message"));
    await message!.find("textarea").setValue("PS2 games stream.");
    await wrapper.find(".save").trigger("click");
    await flushPromises();

    expect(update).toHaveBeenCalledWith({
      enabled: false,
      title: "",
      message: "PS2 games stream.",
    });
    expect(wrapper.find(".save").exists()).toBe(false);
  });

  it("refuses to show an empty message", async () => {
    const wrapper = await mountSection();

    await wrapper.find(".toggle").trigger("click");

    const save = wrapper.find(".save");
    expect(save.exists()).toBe(true);
    expect(save.attributes("disabled")).toBeDefined();
    expect(update).not.toHaveBeenCalled();
  });
});
