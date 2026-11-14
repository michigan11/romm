/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FeedbackKind } from './FeedbackKind';
export type FeedbackCreate = {
    kind: FeedbackKind;
    message: string;
    page_path: string;
    app_version?: string;
    platform_id?: (number | null);
    game_title?: (string | null);
};

