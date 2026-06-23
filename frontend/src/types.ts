export type Copybook = {
  id: number;
  title: string;
  author: string;
  style: string;
  source_type: string;
  cover_path: string;
  tags: string;
  notes: string;
  page_count?: number;
};

export type Page = {
  id: number;
  copybook_id: number;
  page_no: number;
  width: number;
  height: number;
};

export type QueueItem = {
  id: number;
  page_id: number;
  copybook_title: string;
  page_no: number;
  params: Record<string, unknown>;
};

export type Preset = {
  id: number;
  name: string;
  background_image: string;
  ink_color: string;
  foreground_threshold: number;
  mode: string;
  column_detection: string;
  params: Record<string, unknown>;
};

export type GeneratedPost = {
  id: number;
  name: string;
  original_pdf_path: string;
  output_format: string;
  thumb_path: string;
  page_count: number;
  result_count: number;
  sync_status: string;
  remote_path: string;
  last_synced_at: number;
  created_at: number;
  updated_at: number;
};

export type GeneratedPostFile = {
  kind: "original" | "result";
  name: string;
  path: string;
  size: number;
};

export type Api = {
  get_home_stats(): Promise<{ copybooks: number; exported_pages: number }>;
  list_copybooks(): Promise<Copybook[]>;
  import_copybooks(paths: string[]): Promise<Copybook[]>;
  update_copybook_metadata(copybook_id: number, metadata: Partial<Copybook> & { cover_source_path?: string }): Promise<Copybook>;
  list_pages(copybook_id: number): Promise<Page[]>;
  get_copybook_cover(copybook_id: number): Promise<string>;
  get_page_thumbnail(page_id: number): Promise<string>;
  get_page_preview(page_id: number): Promise<string>;
  add_pages_to_queue(page_ids: number[]): Promise<QueueItem[]>;
  list_queue_items(): Promise<QueueItem[]>;
  update_queue_item(item_id: number, params: Record<string, unknown>): Promise<QueueItem>;
  render_queue_preview(item_id: number): Promise<string>;
  export_queue_to_pdf(queue_item_ids: number[], preset_id?: number | null, output_path?: string | null, name?: string | null, output_format?: string | null): Promise<{ output_path: string; page_count: number; generated_post?: GeneratedPost }>;
  get_next_generated_post_name(): Promise<string>;
  list_generated_posts(): Promise<GeneratedPost[]>;
  get_generated_post_thumbnail(post_id: number): Promise<string>;
  list_generated_post_files(post_id: number): Promise<GeneratedPostFile[]>;
  sync_generated_post(post_id: number): Promise<GeneratedPost>;
  list_presets(): Promise<Preset[]>;
  create_preset(data: Record<string, unknown> & { name: string }): Promise<Preset>;
  update_preset(preset_id: number, data: Partial<Preset>): Promise<Preset>;
  delete_preset(preset_id: number): Promise<{ ok: boolean }>;
  get_settings(): Promise<Record<string, string>>;
  update_settings(settings: Record<string, string>): Promise<Record<string, string>>;
  choose_import_files(): Promise<string[]>;
  choose_background_image(): Promise<string>;
  choose_cover_image(): Promise<string>;
  window_move_by(delta_x: number, delta_y: number): Promise<void>;
  window_minimize(): Promise<void>;
  window_toggle_maximize(): Promise<void>;
  window_close(): Promise<void>;
};

declare global {
  interface Window {
    pywebview?: {
      api: Api;
    };
  }
}
