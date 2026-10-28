export type PdfInfo = { path: string; name: string; size: number; pages: number; subject: string; hasText: boolean; compatible: boolean; warnings: string[]; thumbnail: string };
export type Job = { id: string; name: string; source: string; output: string; subject: string; first_page: number; last_page: number; created_at: string; status: 'done' | 'failed' | 'running'; message: string };
export type Environment = { hancom: boolean; fonts: { name: string; installed: boolean }[]; engine: string; version?: string };
export type UpdateInfo = { currentVersion: string; latestVersion: string; hasUpdate: boolean; downloadUrl: string; assetName?: string; assetSize?: number; releaseUrl: string; notes: string; publishedAt: string };
export type Progress = { stage: string; percent: number; message: string };
export type Settings = { outputDir: string };
