import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ScheduledAnnouncementSchema } from "@/__generated__";
import { fromDatetimeLocal } from "@/utils/localDateTime";
import ScheduledAnnouncementsSection from "./ScheduledAnnouncementsSection.vue";

const { list, create, update, remove, confirm } = vi.hoisted(() => ({
  list: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  remove: vi.fn(),
  confirm: vi.fn(),
}));

vi.mock("@/services/api/scheduledAnnouncements", () => ({
  default: { list, create, update, remove },
}));

vi.mock("vue-i18n");
vi.mock("vue-router", () => ({ onBeforeRouteLeave: vi.fn() }));
vi.mock("@/v2/composables/useConfirm", () => ({ useConfirm: () => confirm }));
vi.mock("@/v2/composables/useSnackbar", () => ({
  useSnackbar: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const RTextFieldStub = {
  name: "RTextField",
  props: ["modelValue", "label"],
  emits: ["update:modelValue"],
  template:
    "<label>{{ label }}<textarea :value='modelValue' @input=\"$emit('update:modelValue', $event.target.value)\" /></label>",
};

const RFormStub = {
  name: "RForm",
  emits: ["submit"],
  template: "<form @submit.prevent=\"$emit('submit', $event)\"><slot /></form>",
};

const RBtnStub = {
  name: "RBtn",
  props: ["disabled", "type"],
  emits: ["click"],
  template:
    "<button :type='type || \"button\"' :disabled='disabled' @click=\"$emit('click')\"><slot /></button>",
};

function row(
  overrides: Partial<ScheduledAnnouncementSchema>,
): ScheduledAnnouncementSchema {
  return {
    id: 1,
    title: "Soon",
    message: "Hello",
    starts_at: "2026-12-01T15:00:00.000Z",
    ends_at: null,
    activated_at: null,
    ended_at: null,
    ...overrides,
  };
}

async function mountSection() {
  const wrapper = mount(ScheduledAnnouncementsSection, {
    global: {
      stubs: {
        RTextField: RTextFieldStub,
        RForm: RFormStub,
        RBtn: RBtnStub,
        RSpinner: true,
        RAlert: true,
        SettingsSection: { template: "<section><slot /></section>" },
      },
    },
  });
  await flushPromises();
  return wrapper;
}

function field(
  wrapper: Awaited<ReturnType<typeof mountSection>>,
  label: string,
) {
  const match = wrapper
    .findAll("label")
    .find((item) => item.text().includes(label));
  if (!match) throw new Error(`missing field ${label}`);
  return match.find("textarea");
}

describe("ScheduledAnnouncementsSection", () => {
  beforeEach(() => {
    list.mockReset();
    create.mockReset();
    update.mockReset();
    remove.mockReset();
    confirm.mockReset();
    list.mockResolvedValue({ data: [] });
    confirm.mockResolvedValue(true);
  });

  it("schedules a message at the admin's local start time", async () => {
    create.mockResolvedValue({ data: row({}) });
    const wrapper = await mountSection();

    await field(wrapper, "settings.announcement-title").setValue("Tonight");
    await field(wrapper, "settings.announcement-message").setValue(
      "Down for a scan.",
    );
    await field(wrapper, "settings.scheduled-announcements-starts").setValue(
      "2026-12-01T09:30",
    );
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(create).toHaveBeenCalledWith({
      title: "Tonight",
      message: "Down for a scan.",
      starts_at: fromDatetimeLocal("2026-12-01T09:30"),
      ends_at: null,
    });
  });

  it("does not save without a message and a start time", async () => {
    const wrapper = await mountSection();

    const save = wrapper
      .findAll("button")
      .find((button) =>
        button.text().includes("settings.scheduled-announcements-schedule"),
      );
    expect(save!.attributes("disabled")).toBeDefined();
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(create).not.toHaveBeenCalled();
  });

  it("cancels an upcoming schedule and leaves a live one in place", async () => {
    list.mockResolvedValue({
      data: [
        row({ id: 4, title: "Later", activated_at: null }),
        row({
          id: 9,
          title: "Now",
          activated_at: "2026-11-14T12:00:00.000Z",
        }),
      ],
    });
    remove.mockResolvedValue({});
    const wrapper = await mountSection();

    const deletes = wrapper
      .findAll("button")
      .filter((button) => button.text().includes("common.delete"));
    expect(deletes).toHaveLength(1);
    expect(wrapper.text()).toContain(
      "settings.scheduled-announcements-upcoming",
    );
    expect(wrapper.text()).toContain("settings.scheduled-announcements-live");

    await deletes[0]!.trigger("click");
    await flushPromises();

    expect(confirm).toHaveBeenCalledOnce();
    expect(remove).toHaveBeenCalledWith(4);
  });
});
