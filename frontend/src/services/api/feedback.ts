import type {
  FeedbackCreate,
  FeedbackKind,
  FeedbackSchema,
  FeedbackUpdate,
  LimitOffsetPage_FeedbackSchema_,
} from "@/__generated__";
import api from "@/services/api";

// Mirrors the backend limits in models/feedback.py.
export const FEEDBACK_MESSAGE_MAX_LENGTH = 2000;
export const FEEDBACK_GAME_TITLE_MAX_LENGTH = 255;

export type { FeedbackCreate, FeedbackKind, FeedbackSchema };
export type FeedbackPage = LimitOffsetPage_FeedbackSchema_;

async function create(payload: FeedbackCreate) {
  return api.post<FeedbackSchema>("/feedback", payload);
}

async function list(
  params: {
    kind?: FeedbackKind;
    limit?: number;
    offset?: number;
  } = {},
) {
  return api.get<FeedbackPage>("/feedback", { params });
}

async function update(id: number, payload: FeedbackUpdate) {
  return api.patch<FeedbackSchema>(`/feedback/${id}`, payload);
}

async function remove(id: number) {
  return api.delete(`/feedback/${id}`);
}

export default { create, list, update, remove };
