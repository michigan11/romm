/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FeedbackKind } from './FeedbackKind';
export type FeedbackSchema = {
    id: number;
    user_id: (number | null);
    username: string;
    kind: FeedbackKind;
    message: string;
    page_path: string;
    app_version: string;
    platform_id: (number | null);
    platform_name: (string | null);
    game_title: (string | null);
    resolved: boolean;
    created_at: string;
    updated_at: string;
};

