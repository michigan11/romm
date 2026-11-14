import type {
  ScheduledAnnouncementSchema,
  ScheduledAnnouncementWrite,
} from "@/__generated__";
import api from "@/services/api";

async function list() {
  return api.get<ScheduledAnnouncementSchema[]>("/scheduled-announcements");
}

async function create(payload: ScheduledAnnouncementWrite) {
  return api.post<ScheduledAnnouncementSchema>(
    "/scheduled-announcements",
    payload,
  );
}

async function update(id: number, payload: ScheduledAnnouncementWrite) {
  return api.put<ScheduledAnnouncementSchema>(
    `/scheduled-announcements/${id}`,
    payload,
  );
}

async function remove(id: number) {
  return api.delete(`/scheduled-announcements/${id}`);
}

export default { list, create, update, remove };
