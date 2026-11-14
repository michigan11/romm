import type { AnnouncementSchema, AnnouncementUpdate } from "@/__generated__";
import api from "@/services/api";

async function get() {
  return api.get<AnnouncementSchema>("/announcement");
}

async function update(payload: AnnouncementUpdate) {
  return api.put<AnnouncementSchema>("/announcement", payload);
}

async function dismiss(revision: number) {
  return api.post("/announcement/dismiss", { revision });
}

export default { get, update, dismiss };
