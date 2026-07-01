import { useEffect, useRef, useState } from "react";
import type { Dispatch, MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent, ReactElement, SetStateAction, WheelEvent as ReactWheelEvent } from "react";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Dialog,
  DialogActions,
  DialogBody,
  DialogContent,
  DialogSurface,
  DialogTitle,
  Field,
  FluentProvider,
  Input,
  MessageBar,
  MessageBarBody,
  Select,
  Spinner,
  Text,
  Textarea,
  Title1,
  Title2,
  Title3,
  Tooltip,
  webLightTheme,
} from "@fluentui/react-components";
import {
  Add24Regular,
  ArrowLeft24Regular,
  ArrowSync24Regular,
  BookOpen24Regular,
  Box24Regular,
  Color24Regular,
  Dismiss24Regular,
  DocumentFolder24Regular,
  DocumentPdf24Regular,
  Delete24Regular,
  FolderSync24Regular,
  Home24Regular,
  Image24Regular,
  LineHorizontal1Regular,
  Maximize16Regular,
  Save24Regular,
  Search24Regular,
  Settings24Regular,
  TextFont24Regular,
} from "@fluentui/react-icons";
import packageJson from "../package.json";
import type {
  Api,
  Collection,
  Copybook,
  GeneratedPost,
  GeneratedPostFile,
  Glyph,
  GlyphOccurrence,
  GlyphGroup,
  Page,
  PageAnalysis,
  PageDetail,
  Preset,
  RuntimeDiagnostics,
  RuntimeLogEntry,
} from "./types";

type View = "home" | "library" | "dictionary" | "collection" | "make" | "practice" | "presets" | "settings";
type CopybookMetadataForm = {
  title: string;
  author: string;
  cover_source_path?: string;
  crop_left_ratio: number;
  crop_right_ratio: number;
  crop_top_ratio: number;
  crop_bottom_ratio: number;
};
type MakerSession = {
  pageId: number;
  copybookId: number;
  copybookTitle: string;
  pageNo: number;
};
type MakerParams = {
  grid_style: "tian" | "mi";
  cell_size_mm: number;
  margin_mm: number;
  dpi: number;
};
type PageCropDraft = {
  leftPercent: number;
  rightPercent: number;
  topPercent: number;
  bottomPercent: number;
  rotationDegrees: number;
};

const APP_VERSION = `v${packageJson.version}`;
const fallbackApi: Api = {
  async get_home_stats() {
    return { copybooks: 0, exported_pages: 0 };
  },
  async list_copybooks() {
    return [];
  },
  async import_copybooks() {
    return [];
  },
  async update_copybook_metadata(_id, metadata) {
    return {
      id: _id,
      title: metadata.title || "",
      author: metadata.author || "",
      style: "",
      source_type: "",
      cover_path: "",
      tags: "",
      notes: "",
      crop_left_ratio: Number(metadata.crop_left_ratio || 0),
      crop_right_ratio: Number(metadata.crop_right_ratio || 0),
      crop_top_ratio: Number(metadata.crop_top_ratio || 0),
      crop_bottom_ratio: Number(metadata.crop_bottom_ratio || 0),
    };
  },
  async list_pages() {
    return [];
  },
  async get_page_detail(page_id) {
    return {
      id: page_id,
      copybook_id: 0,
      page_no: 1,
      copybook_title: "",
      width: 0,
      height: 0,
      crop_left_ratio: 0,
      crop_right_ratio: 0,
      crop_top_ratio: 0,
      crop_bottom_ratio: 0,
      rotation_degrees: 0,
      page_crop_left_ratio: 0,
      page_crop_right_ratio: 0,
      page_crop_top_ratio: 0,
      page_crop_bottom_ratio: 0,
      page_crop_override: 0,
    };
  },
  async update_page_crop(page_id, metadata) {
    return {
      id: page_id,
      copybook_id: 0,
      page_no: 1,
      copybook_title: "",
      width: 0,
      height: 0,
      crop_left_ratio: Number(metadata.crop_left_ratio || 0),
      crop_right_ratio: Number(metadata.crop_right_ratio || 0),
      crop_top_ratio: Number(metadata.crop_top_ratio || 0),
      crop_bottom_ratio: Number(metadata.crop_bottom_ratio || 0),
      rotation_degrees: Number(metadata.rotation_degrees || 0),
      page_crop_left_ratio: Number(metadata.crop_left_ratio || 0),
      page_crop_right_ratio: Number(metadata.crop_right_ratio || 0),
      page_crop_top_ratio: Number(metadata.crop_top_ratio || 0),
      page_crop_bottom_ratio: Number(metadata.crop_bottom_ratio || 0),
      page_crop_override: 1,
    };
  },
  async get_copybook_cover() {
    return "";
  },
  async get_page_thumbnail() {
    return "";
  },
  async get_page_preview() {
    return "";
  },
  async get_page_transform_preview() {
    return "";
  },
  async render_page_previews() {
    return [];
  },
  async analyze_page() {
    return { version: 1, model_id: "fallback", engine: "fallback", status: "needs_ocr", selection_mode: "ocr_groups", image_size: [1, 1], groups: [] };
  },
  async update_page_analysis(_pageId, groups) {
    return {
      version: 1,
      model_id: "fallback",
      engine: "fallback",
      status: "reviewed",
      selection_mode: "ordered_stream",
      image_size: [1, 1],
      groups,
      ocr_groups: [],
    };
  },
  async update_page_ocr_groups(_pageId, groups) {
    return {
      version: 1,
      model_id: "fallback",
      engine: "fallback",
      status: "reviewed",
      selection_mode: "ocr_groups",
      image_size: [1, 1],
      groups,
    };
  },
  async search_glyphs() {
    return { items: [], total: 0 };
  },
  async list_glyph_filters() {
    return { copybooks: [], authors: [] };
  },
  async get_glyph_image() {
    return "";
  },
  async list_collections() {
    return [];
  },
  async create_collection(name) {
    const now = Date.now();
    return { id: now, name, input_text: "", direction: "horizontal", line_capacity: 8, background: "transparent", created_at: now, updated_at: now, items: [] };
  },
  async get_collection(collectionId) {
    const now = Date.now();
    return { id: collectionId, name: "集字方案", input_text: "", direction: "horizontal", line_capacity: 8, background: "transparent", created_at: now, updated_at: now, items: [] };
  },
  async update_collection(collectionId, data) {
    const now = Date.now();
    return {
      id: collectionId,
      name: data.name || "集字方案",
      input_text: data.input_text || "",
      direction: data.direction || "horizontal",
      line_capacity: data.line_capacity || 8,
      background: data.background || "transparent",
      created_at: now,
      updated_at: now,
      items: [],
    };
  },
  async rename_collection(collectionId, name) {
    return this.update_collection(collectionId, { name });
  },
  async delete_collection() {
    return { ok: true };
  },
  async render_collection_preview() {
    return "";
  },
  async export_collection_png() {
    return { output_path: "" };
  },
  async export_page_to_generated_post(page_id, _params, name, outputFormat) {
    return {
      id: Date.now(),
      name,
      original_pdf_path: "",
      output_format: outputFormat || "pdf",
      thumb_path: "",
      page_count: page_id ? 1 : 0,
      result_count: 0,
      sync_status: "local",
      remote_path: "",
      last_synced_at: 0,
      created_at: Date.now(),
      updated_at: Date.now(),
    };
  },
  async add_pages_to_queue() {
    return [];
  },
  async list_queue_items() {
    return [];
  },
  async update_queue_item(item_id, params) {
    return { id: item_id, page_id: 0, copybook_title: "", page_no: 0, params };
  },
  async render_queue_preview() {
    return "";
  },
  async render_queue_previews() {
    return [];
  },
  async analyze_queue_item() {
    return { version: 1, model_id: "fallback", engine: "fallback", status: "needs_ocr", image_size: [1, 1], groups: [] };
  },
  async update_queue_analysis(_itemId, groups) {
    return { version: 1, model_id: "fallback", engine: "fallback", status: "reviewed", image_size: [1, 1], groups };
  },
  async export_queue_to_pdf(queue_item_ids, _presetId, _outputPath, name, outputFormat) {
    return {
      output_path: "",
      page_count: queue_item_ids.length,
      generated_post: name ? {
        id: Date.now(),
        name,
        original_pdf_path: "",
        output_format: outputFormat || "pdf",
        thumb_path: "",
        page_count: queue_item_ids.length,
        result_count: 0,
        sync_status: "local",
        remote_path: "",
        last_synced_at: 0,
        created_at: Date.now(),
        updated_at: Date.now(),
      } : undefined,
    };
  },
  async get_next_generated_post_name() {
    return "卷一";
  },
  async list_generated_posts() {
    return [];
  },
  async get_generated_post_thumbnail() {
    return "";
  },
  async list_generated_post_files() {
    return [];
  },
  async sync_generated_post(post_id) {
    return {
      id: post_id,
      name: "",
      original_pdf_path: "",
      output_format: "pdf",
      thumb_path: "",
      page_count: 0,
      result_count: 0,
      sync_status: "synced",
      remote_path: "",
      last_synced_at: Date.now(),
      created_at: Date.now(),
      updated_at: Date.now(),
    };
  },
  async list_presets() {
    return [];
  },
  async create_preset(data) {
    return { id: Date.now(), name: data.name, background_image: "", ink_color: "#000000", foreground_threshold: 18, mode: "row", column_detection: "gray", params: asParams(data.params) };
  },
  async update_preset(preset_id, data) {
    return { id: preset_id, name: data.name || "", background_image: data.background_image || "", ink_color: data.ink_color || "#000000", foreground_threshold: data.foreground_threshold || 18, mode: data.mode || "row", column_detection: data.column_detection || "gray", params: asParams(data.params) };
  },
  async delete_preset() {
    return { ok: true };
  },
  async get_settings() {
    return {};
  },
  async update_settings(settings) {
    return settings;
  },
  async get_runtime_diagnostics() {
    return {
      status: { operation: "", stage: "idle", message: "", page_id: null, updated_at: 0 },
      entries: [],
      last_id: 0,
      log_path: "",
    };
  },
  async append_runtime_log(level, source, message, details = "") {
    return {
      id: Date.now(),
      timestamp: Date.now() / 1000,
      level: level === "error" ? "error" : level === "warning" ? "warning" : level === "debug" ? "debug" : "info",
      source,
      message,
      details,
    };
  },
  async clear_runtime_logs() {
    return { ok: true };
  },
  async choose_import_files() {
    return [];
  },
  async choose_background_image() {
    return "";
  },
  async choose_cover_image() {
    return "";
  },
  async window_move_by(delta_x, delta_y) {
    window.moveBy(delta_x, delta_y);
  },
  async window_minimize() {},
  async window_toggle_maximize() {},
  async window_close() {},
};

function asParams(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function ratioToPercent(value: unknown): number {
  const ratio = Number(value || 0);
  if (!Number.isFinite(ratio)) return 0;
  return Math.round(ratio * 1000) / 10;
}

function percentToCropRatio(value: unknown): number {
  const percent = Number(value || 0);
  if (!Number.isFinite(percent)) return 0;
  return Math.max(0, Math.min(45, percent)) / 100;
}

function normalizeRotation(value: number): number {
  const normalized = ((Number(value || 0) + 180) % 360 + 360) % 360 - 180;
  return Math.abs(normalized) < 0.001 ? 0 : Number(normalized.toFixed(3));
}

function pageCropDraftKey(draft: PageCropDraft): string {
  return [
    draft.leftPercent,
    draft.rightPercent,
    draft.topPercent,
    draft.bottomPercent,
    draft.rotationDegrees,
  ].join(":");
}

function rotateCropDraft(draft: PageCropDraft, delta: 90 | -90): PageCropDraft {
  if (delta === 90) {
    return {
      leftPercent: draft.topPercent,
      rightPercent: draft.bottomPercent,
      topPercent: draft.rightPercent,
      bottomPercent: draft.leftPercent,
      rotationDegrees: normalizeRotation(draft.rotationDegrees + delta),
    };
  }
  return {
    leftPercent: draft.bottomPercent,
    rightPercent: draft.topPercent,
    topPercent: draft.leftPercent,
    bottomPercent: draft.rightPercent,
    rotationDegrees: normalizeRotation(draft.rotationDegrees + delta),
  };
}

function api(): Api {
  return window.pywebview?.api || fallbackApi;
}

function diagnosticLevel(message: string): "warning" | "error" | null {
  if (/(error|exception|traceback|失败|错误|异常|无法)/i.test(message)) return "error";
  if (/(warning|warn|警告|未加载|降级|尚未安装|paddleocr)/i.test(message)) return "warning";
  return null;
}

function formatLogValue(value: unknown): string {
  if (value instanceof Error) return value.stack || `${value.name}: ${value.message}`;
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function appendFrontendLog(level: "warning" | "error", source: string, message: string, details = "") {
  const bridgeApi = window.pywebview?.api;
  if (typeof bridgeApi?.append_runtime_log !== "function") return;
  try {
    void Promise.resolve(bridgeApi.append_runtime_log(level, source, message, details)).catch(() => undefined);
  } catch {
    // Diagnostics must never replace the original frontend error.
  }
}

export function App() {
  const [view, setView] = useState<View>("home");
  const [stats, setStats] = useState({ copybooks: 0, exported_pages: 0 });
  const [message, setMessageState] = useState("");
  const [makerSession, setMakerSession] = useState<MakerSession | null>(null);
  const [runtimeLogOpen, setRuntimeLogOpen] = useState(false);

  function setMessage(value: string) {
    setMessageState(value);
    const level = diagnosticLevel(value);
    if (level) appendFrontendLog(level, "frontend.ui", value);
  }

  async function refreshStats() {
    setStats(await api().get_home_stats());
  }

  useEffect(() => {
    refreshStats().catch((error) => setMessage(String(error)));
  }, []);

  useEffect(() => {
    if (!message) return;
    const timeout = window.setTimeout(() => setMessageState(""), 3600);
    return () => window.clearTimeout(timeout);
  }, [message]);

  useEffect(() => {
    const originalWarn = console.warn;
    const originalError = console.error;
    console.warn = (...values: unknown[]) => {
      originalWarn(...values);
      appendFrontendLog("warning", "frontend.console", values.map(formatLogValue).join(" "));
    };
    console.error = (...values: unknown[]) => {
      originalError(...values);
      appendFrontendLog("error", "frontend.console", values.map(formatLogValue).join(" "));
    };
    const handleError = (event: ErrorEvent) => {
      appendFrontendLog("error", "frontend.window", event.message, event.error?.stack || `${event.filename}:${event.lineno}:${event.colno}`);
    };
    const handleRejection = (event: PromiseRejectionEvent) => {
      const details = formatLogValue(event.reason);
      appendFrontendLog("error", "frontend.promise", "未处理的 Promise 异常", details);
    };
    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);
    return () => {
      console.warn = originalWarn;
      console.error = originalError;
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, []);

  return (
    <FluentProvider theme={webLightTheme}>
      <div className="appShell">
        <TitleBar />
        <aside className="navRail">
          <div className="brandBlock">
            <img className="brandMark" src="/icon-256.png" alt="Linmo" />
            <Text weight="semibold">Linmo</Text>
          </div>
          <NavButton icon={<Home24Regular />} active={view === "home"} onClick={() => setView("home")}>首页</NavButton>
          <NavButton icon={<BookOpen24Regular />} active={view === "library"} onClick={() => setView("library")}>藏帖</NavButton>
          <NavButton icon={<Search24Regular />} active={view === "dictionary"} onClick={() => setView("dictionary")}>字典</NavButton>
          <NavButton icon={<TextFont24Regular />} active={view === "collection"} onClick={() => setView("collection")}>集字</NavButton>
          <NavButton icon={<DocumentPdf24Regular />} active={view === "make"} onClick={() => setView("make")}>制帖</NavButton>
          <NavButton icon={<DocumentFolder24Regular />} active={view === "practice"} onClick={() => setView("practice")}>练帖</NavButton>
          <NavButton icon={<Color24Regular />} active={view === "presets"} onClick={() => setView("presets")}>预设</NavButton>
          <div className="navSpacer" />
          <NavButton icon={<LineHorizontal1Regular />} active={runtimeLogOpen} onClick={() => setRuntimeLogOpen(true)}>运行日志</NavButton>
          <NavButton icon={<Settings24Regular />} active={view === "settings"} onClick={() => setView("settings")}>设置</NavButton>
        </aside>
        <main className="workspace">
          {view === "home" && <Home stats={stats} />}
          {view === "library" && (
            <Library
              setMessage={setMessage}
              refreshStats={refreshStats}
              openMaker={(session) => {
                setMakerSession(session);
                setView("make");
              }}
            />
          )}
          {view === "make" && (
            <Maker
              session={makerSession}
              setMessage={setMessage}
              refreshStats={refreshStats}
              openPractice={() => setView("practice")}
            />
          )}
          {view === "dictionary" && <Dictionary setMessage={setMessage} />}
          {view === "collection" && <CollectionWorkspace setMessage={setMessage} />}
          {view === "practice" && <PracticeShelf setMessage={setMessage} />}
          {view === "presets" && <Presets setMessage={setMessage} />}
          {view === "settings" && <Settings setMessage={setMessage} />}
        </main>
        {message && (
          <div className="toastRegion">
            <MessageBar intent="info" className="messageBar">
              <MessageBarBody>{message}</MessageBarBody>
            </MessageBar>
          </div>
        )}
        <RuntimeLogDialog open={runtimeLogOpen} setMessage={setMessage} onClose={() => setRuntimeLogOpen(false)} />
      </div>
    </FluentProvider>
  );
}

function NavButton({ active, icon, children, onClick }: { active: boolean; icon: ReactElement; children: string; onClick: () => void }) {
  return (
    <Button appearance={active ? "primary" : "subtle"} icon={icon} className="navButton" onClick={onClick}>
      {children}
    </Button>
  );
}

function RuntimeLogDialog({
  open,
  setMessage,
  onClose,
}: {
  open: boolean;
  setMessage: (value: string) => void;
  onClose: () => void;
}) {
  const [diagnostics, setDiagnostics] = useState<RuntimeDiagnostics | null>(null);

  async function refresh() {
    setDiagnostics(await api().get_runtime_diagnostics(0));
  }

  async function clearLogs() {
    await api().clear_runtime_logs();
    await refresh();
    setMessage("运行日志已清空");
  }

  async function copyLogs() {
    if (!diagnostics) return;
    const text = diagnostics.entries.map(formatRuntimeLogEntry).join("\n");
    await navigator.clipboard.writeText(text);
    setMessage("运行日志已复制");
  }

  useEffect(() => {
    if (!open) return;
    refresh().catch((error) => setMessage(String(error)));
    const interval = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 1000);
    return () => window.clearInterval(interval);
  }, [open]);

  if (!open) return null;
  return (
    <Dialog open>
      <DialogSurface className="runtimeLogDialogSurface">
        <DialogBody>
          <DialogTitle>运行日志</DialogTitle>
          <DialogContent className="runtimeLogDialogContent">
            <div className="runtimeLogSummary">
              <Text size={200}>
                当前状态：{diagnostics?.status.message || "空闲"}
              </Text>
              <Text size={200} className="mutedText">
                日志文件：{diagnostics?.log_path || "后端尚未连接"}
              </Text>
            </div>
            <div className="runtimeLogEntries">
              {!diagnostics?.entries.length ? (
                <div className="centerState compact"><Text>暂无日志</Text></div>
              ) : diagnostics.entries.map((entry) => (
                <div key={entry.id} className={`runtimeLogEntry ${entry.level}`}>
                  <div className="runtimeLogEntryHeader">
                    <Text size={100}>{formatRuntimeLogTime(entry.timestamp)}</Text>
                    <Badge appearance="tint" color={entry.level === "error" ? "danger" : entry.level === "warning" ? "warning" : "informative"}>
                      {entry.level.toUpperCase()}
                    </Badge>
                    <Text size={100} weight="semibold">{entry.source}</Text>
                  </div>
                  <Text size={200}>{entry.message}</Text>
                  {entry.details && <pre>{entry.details}</pre>}
                </div>
              ))}
            </div>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => clearLogs().catch((error) => setMessage(String(error)))}>清空</Button>
            <Button disabled={!diagnostics?.entries.length} onClick={() => copyLogs().catch((error) => setMessage(String(error)))}>复制</Button>
            <Button appearance="primary" onClick={onClose}>关闭</Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}

function formatRuntimeLogTime(timestamp: number) {
  return new Date(timestamp * 1000).toLocaleTimeString();
}

function formatRuntimeLogEntry(entry: RuntimeLogEntry) {
  const timestamp = new Date(entry.timestamp * 1000).toLocaleString();
  return `${timestamp} [${entry.level.toUpperCase()}] ${entry.source}: ${entry.message}${entry.details ? `\n${entry.details}` : ""}`;
}

function pageThumbClass(selected: boolean, queued: boolean) {
  return ["pageThumb", selected ? "selected" : "", queued ? "queued" : ""].filter(Boolean).join(" ");
}

function TitleBar() {
  const titleDrag = useRef<{ pointerId: number; screenX: number; screenY: number } | null>(null);

  function startTitleDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    titleDrag.current = {
      pointerId: event.pointerId,
      screenX: event.screenX,
      screenY: event.screenY,
    };
  }

  function moveTitleDrag(event: ReactPointerEvent<HTMLDivElement>) {
    const drag = titleDrag.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.preventDefault();
    const deltaX = Math.round(event.screenX - drag.screenX);
    const deltaY = Math.round(event.screenY - drag.screenY);
    if (deltaX || deltaY) {
      void api().window_move_by(deltaX, deltaY);
      titleDrag.current = { ...drag, screenX: event.screenX, screenY: event.screenY };
    }
  }

  function stopTitleDrag(event: ReactPointerEvent<HTMLDivElement>) {
    if (titleDrag.current?.pointerId === event.pointerId) {
      titleDrag.current = null;
    }
  }

  return (
    <header className="titleBar" onDoubleClick={() => api().window_toggle_maximize()}>
      <div
        className="titleBarDrag"
        onPointerDown={startTitleDrag}
        onPointerMove={moveTitleDrag}
        onPointerUp={stopTitleDrag}
        onPointerCancel={stopTitleDrag}
      >
        <img className="titleBarIcon" src="/icon-256.png" alt="" />
        <span className="titleBarLabel">Linmo</span>
        <span className="titleBarVersion">{APP_VERSION}</span>
      </div>
      <div className="titleBarControls">
        <Button
          appearance="subtle"
          icon={<LineHorizontal1Regular />}
          className="titleBarBtn"
          onClick={() => api().window_minimize()}
          title="最小化"
        />
        <Button
          appearance="subtle"
          icon={<Maximize16Regular />}
          className="titleBarBtn"
          onClick={() => api().window_toggle_maximize()}
          title="最大化"
        />
        <Button
          appearance="subtle"
          icon={<Dismiss24Regular />}
          className="titleBarBtn titleBarBtnClose"
          onClick={() => api().window_close()}
          title="关闭"
        />
      </div>
    </header>
  );
}

function Home({ stats }: { stats: { copybooks: number; exported_pages: number } }) {
  return (
    <section className="homeView">
      <img className="homeMark" src="/icon-512.png" alt="Linmo" />
      <Title1>Linmo</Title1>
      <Text className="homeDescription">本地临摹制帖</Text>
      <div className="homeStats">
        <Badge size="extra-large" appearance="filled">已藏 {stats.copybooks} 帖</Badge>
        <Badge size="extra-large" appearance="tint">已导出 {stats.exported_pages} 页</Badge>
      </div>
    </section>
  );
}

function Library({
  setMessage,
  refreshStats,
  openMaker,
}: {
  setMessage: (value: string) => void;
  refreshStats: () => Promise<void>;
  openMaker: (session: MakerSession) => void;
}) {
  const [copybooks, setCopybooks] = useState<Copybook[]>([]);
  const [selected, setSelected] = useState<Copybook | null>(null);
  const [editing, setEditing] = useState<Copybook | null>(null);
  const [pagesOpen, setPagesOpen] = useState(false);
  const [pagePreviewOpen, setPagePreviewOpen] = useState(false);
  const [pages, setPages] = useState<Page[]>([]);
  const [selectedPageId, setSelectedPageId] = useState<number | null>(null);
  const [pageDetail, setPageDetail] = useState<PageDetail | null>(null);
  const [pagePreviewImage, setPagePreviewImage] = useState("");
  const [covers, setCovers] = useState<Record<number, string>>({});
  const [thumbs, setThumbs] = useState<Record<number, string>>({});
  const [loadingPages, setLoadingPages] = useState(false);
  const [loadingPagePreview, setLoadingPagePreview] = useState(false);
  const [savingPageTransform, setSavingPageTransform] = useState(false);
  const [importing, setImporting] = useState(false);
  const [cropDraft, setCropDraft] = useState<PageCropDraft | null>(null);
  const openRunId = useRef(0);
  const cropSaveRunId = useRef(0);
  const lastSavedCropKey = useRef("");

  async function loadCopybooks() {
    const loaded = await api().list_copybooks();
    setCopybooks(loaded);
    const queue = [...loaded];
    const workers = Array.from({ length: Math.min(6, queue.length) }, async () => {
      while (queue.length) {
        const copybook = queue.shift();
        if (!copybook) return;
        try {
          const cover = await api().get_copybook_cover(copybook.id);
          setCovers((current) => ({ ...current, [copybook.id]: cover }));
        } catch (error) {
          setMessage(String(error));
        }
      }
    });
    void Promise.all(workers);
  }

  async function openCopybook(copybook: Copybook) {
    const runId = ++openRunId.current;
    setSelected(copybook);
    setPagesOpen(true);
    setPagePreviewOpen(false);
    setLoadingPages(true);
    setPages([]);
    setThumbs({});
    setSelectedPageId(null);
    setPageDetail(null);
    setPagePreviewImage("");
    try {
      const loadedPages = await api().list_pages(copybook.id);
      if (openRunId.current !== runId) return;
      setPages(loadedPages);
      setLoadingPages(false);

      const queue = [...loadedPages];
      const workers = Array.from({ length: Math.min(6, queue.length) }, async () => {
        while (queue.length && openRunId.current === runId) {
          const page = queue.shift();
          if (!page) return;
          try {
            const thumbnail = await api().get_page_thumbnail(page.id);
            if (openRunId.current !== runId) return;
            setThumbs((current) => ({ ...current, [page.id]: thumbnail }));
          } catch (error) {
            setMessage(String(error));
          }
        }
      });
      void Promise.all(workers);
    } catch (error) {
      if (openRunId.current === runId) {
        setLoadingPages(false);
        setMessage(String(error));
      }
    }
  }

  async function openPagePreview(page: Page) {
    setSelectedPageId(page.id);
    setPagePreviewOpen(true);
    setLoadingPagePreview(true);
    setPagePreviewImage("");
    try {
      const [detail, preview] = await Promise.all([
        api().get_page_detail(page.id),
        api().get_page_transform_preview(page.id),
      ]);
      setPageDetail(detail);
      const draft = {
        leftPercent: ratioToPercent(detail.crop_left_ratio),
        rightPercent: ratioToPercent(detail.crop_right_ratio),
        topPercent: ratioToPercent(detail.crop_top_ratio),
        bottomPercent: ratioToPercent(detail.crop_bottom_ratio),
        rotationDegrees: Number(detail.rotation_degrees || 0),
      };
      setCropDraft(draft);
      lastSavedCropKey.current = pageCropDraftKey(draft);
      setPagePreviewImage(preview);
    } catch (error) {
      setMessage(String(error));
    } finally {
      setLoadingPagePreview(false);
    }
  }

  async function refreshPageMedia(pageId: number) {
    const [preview, thumbnail] = await Promise.all([
      api().get_page_transform_preview(pageId),
      api().get_page_thumbnail(pageId),
    ]);
    setPagePreviewImage(preview);
    setThumbs((current) => ({ ...current, [pageId]: thumbnail }));
  }

  async function importFiles() {
    const chosen = await api().choose_import_files();
    if (!chosen.length) {
      setMessage("没有选择导入文件");
      return;
    }
    setImporting(true);
    try {
      await api().import_copybooks(chosen);
      await loadCopybooks();
      await refreshStats();
      setMessage("导入完成");
    } catch (error) {
      setMessage(String(error));
    } finally {
      setImporting(false);
    }
  }

  async function saveMetadata(copybook: Copybook, metadata: CopybookMetadataForm) {
    const updated = await api().update_copybook_metadata(copybook.id, metadata);
    setCopybooks((current) => current.map((item) => item.id === updated.id ? updated : item));
    setSelected((current) => current?.id === updated.id ? updated : current);
    setEditing(null);
    const cover = await api().get_copybook_cover(updated.id);
    setCovers((current) => ({ ...current, [updated.id]: cover }));
    setMessage("元数据已保存");
  }

  useEffect(() => {
    loadCopybooks().catch((error) => setMessage(String(error)));
  }, []);

  useEffect(() => {
    if (!pageDetail || !cropDraft) return;
    const cropKey = pageCropDraftKey(cropDraft);
    if (cropKey === lastSavedCropKey.current) return;
    if (cropDraft.leftPercent + cropDraft.rightPercent >= 80) return;
    if (cropDraft.topPercent + cropDraft.bottomPercent >= 80) return;
    const runId = ++cropSaveRunId.current;
    const timeout = window.setTimeout(() => {
      setSavingPageTransform(true);
      api().update_page_crop(pageDetail.id, {
        crop_left_ratio: percentToCropRatio(cropDraft.leftPercent),
        crop_right_ratio: percentToCropRatio(cropDraft.rightPercent),
        crop_top_ratio: percentToCropRatio(cropDraft.topPercent),
        crop_bottom_ratio: percentToCropRatio(cropDraft.bottomPercent),
        rotation_degrees: normalizeRotation(cropDraft.rotationDegrees),
      }).then(async (updated) => {
        if (cropSaveRunId.current !== runId) return;
        setPageDetail(updated);
        lastSavedCropKey.current = cropKey;
        await refreshPageMedia(updated.id);
      }).catch((error) => setMessage(String(error))).finally(() => {
        if (cropSaveRunId.current === runId) {
          setSavingPageTransform(false);
        }
      });
    }, 180);
    return () => window.clearTimeout(timeout);
  }, [
    cropDraft?.leftPercent,
    cropDraft?.rightPercent,
    cropDraft?.topPercent,
    cropDraft?.bottomPercent,
    cropDraft?.rotationDegrees,
    pageDetail?.id,
  ]);

  if (pagePreviewOpen && selected && (!pageDetail || !cropDraft)) {
    return (
      <section className="pagePreviewView">
        <div className="previewTopbar">
          <Button icon={<ArrowLeft24Regular />} appearance="subtle" onClick={() => setPagePreviewOpen(false)}>返回</Button>
          <div className="previewTitle">
            <Title2>{selected.title}</Title2>
            <Text className="mutedText">正在读取单页预览</Text>
          </div>
        </div>
        <div className="centerState"><Spinner label="正在加载裁切预览" /></div>
      </section>
    );
  }

  if (pagePreviewOpen && selected && pageDetail && cropDraft) {
    const horizontalCropTooLarge = cropDraft.leftPercent + cropDraft.rightPercent >= 80;
    const verticalCropTooLarge = cropDraft.topPercent + cropDraft.bottomPercent >= 80;
    const cropTotalTooLarge = horizontalCropTooLarge || verticalCropTooLarge;
    const transformDirty = pageCropDraftKey(cropDraft) !== lastSavedCropKey.current;
    return (
      <section className="pagePreviewView">
        <div className="previewTopbar">
          <Button icon={<ArrowLeft24Regular />} appearance="subtle" onClick={() => setPagePreviewOpen(false)}>返回</Button>
          <div className="previewTitle">
            <Title2>{selected.title}</Title2>
            <Text className="mutedText">第 {pageDetail.page_no} 页 · 先旋转并裁掉框线，再进入 OCR</Text>
          </div>
          <Button
            appearance="primary"
            icon={<DocumentPdf24Regular />}
            disabled={cropTotalTooLarge || transformDirty || savingPageTransform}
            onClick={() => openMaker({
              pageId: pageDetail.id,
              copybookId: pageDetail.copybook_id,
              copybookTitle: pageDetail.copybook_title,
              pageNo: pageDetail.page_no,
            })}
          >
            进入制帖
          </Button>
        </div>
        <Card className="contentCard singlePagePreviewCard">
          <div className="singlePagePreviewLayout">
            <div className="singlePagePreviewPane">
              <VisualCropEditor
                image={pagePreviewImage}
                draft={cropDraft}
                loading={loadingPagePreview || !pagePreviewImage}
                onChange={setCropDraft}
              />
            </div>
            <div className="formStack singlePagePreviewSidebar">
              <Text size={200} className="mutedText">
                拖动图中四条蓝边调整 OCR 范围。旋转和裁剪会保存到当前页，并统一用于识别、选字和导出。
              </Text>
              <Field label="旋转角度（°）" hint="可用 0.5° 微调倾斜。">
                <Input
                  type="number"
                  min={-180}
                  max={180}
                  step={0.5}
                  value={String(cropDraft.rotationDegrees)}
                  onChange={(_, data) => setCropDraft((current) => current ? {
                    ...current,
                    rotationDegrees: normalizeRotation(Number(data.value)),
                  } : current)}
                />
              </Field>
              <div className="rotationButtons">
                <Button onClick={() => setCropDraft((current) => current ? rotateCropDraft(current, -90) : current)}>顺时针 90°</Button>
                <Button onClick={() => setCropDraft((current) => current ? rotateCropDraft(current, 90) : current)}>逆时针 90°</Button>
              </div>
              <div className="formGrid">
                <Field label="左页边预裁切（%）" hint="先裁左边缘。">
                  <Input
                    type="number"
                    min={0}
                    max={45}
                    step={0.5}
                    value={String(cropDraft.leftPercent)}
                    onChange={(_, data) => setCropDraft((current) => current ? { ...current, leftPercent: Number(data.value) } : current)}
                  />
                </Field>
                <Field label="右页边预裁切（%）" hint="先裁右边缘。">
                  <Input
                    type="number"
                    min={0}
                    max={45}
                    step={0.5}
                    value={String(cropDraft.rightPercent)}
                    onChange={(_, data) => setCropDraft((current) => current ? { ...current, rightPercent: Number(data.value) } : current)}
                  />
                </Field>
                <Field label="上页边预裁切（%）" hint="先裁页眉，再识别。">
                  <Input
                    type="number"
                    min={0}
                    max={45}
                    step={0.5}
                    value={String(cropDraft.topPercent)}
                    onChange={(_, data) => setCropDraft((current) => current ? { ...current, topPercent: Number(data.value) } : current)}
                  />
                </Field>
                <Field label="下页边预裁切（%）" hint="先裁页脚，再识别。">
                  <Input
                    type="number"
                    min={0}
                    max={45}
                    step={0.5}
                    value={String(cropDraft.bottomPercent)}
                    onChange={(_, data) => setCropDraft((current) => current ? { ...current, bottomPercent: Number(data.value) } : current)}
                  />
                </Field>
              </div>
              {horizontalCropTooLarge && <Text size={200} className="mutedText">左右预裁切合计需小于 80%。</Text>}
              {verticalCropTooLarge && <Text size={200} className="mutedText">上下预裁切合计需小于 80%。</Text>}
              {(transformDirty || savingPageTransform) && <Text size={200} className="mutedText">正在保存页面变换……</Text>}
            </div>
          </div>
        </Card>
      </section>
    );
  }

  if (pagesOpen && selected) {
    return (
      <section className="pagePreviewView">
        <div className="previewTopbar">
          <Button icon={<ArrowLeft24Regular />} appearance="subtle" onClick={() => setPagesOpen(false)}>返回</Button>
          <div className="previewTitle">
            <Title2>{selected.title}</Title2>
            <Text className="mutedText">{selected.author || "未填写作者"} · {pages.length || selected.page_count || 0} 页</Text>
          </div>
        </div>
        {loadingPages ? (
          <div className="centerState"><Spinner label="正在读取页面" /></div>
        ) : (
          <div className="pageGrid">
            {pages.map((page) => (
              <button
                key={page.id}
                className={pageThumbClass(selectedPageId === page.id, false)}
                onClick={() => setSelectedPageId(page.id)}
                onDoubleClick={() => openPagePreview(page)}
                type="button"
                aria-pressed={selectedPageId === page.id}
              >
                <div className="thumbCanvas">
                  {thumbs[page.id] ? <img src={thumbs[page.id]} alt={`第 ${page.page_no} 页`} /> : <Spinner size="small" />}
                </div>
                <Text size={200}>第 {page.page_no} 页</Text>
              </button>
            ))}
          </div>
        )}
      </section>
    );
  }

  return (
    <section className="libraryView">
      {importing && <BlockingOverlay title="正在导入中" detail="正在复制文件并生成书帖记录" />}
      <div className="sectionHeader">
        <div>
          <Title1>藏帖阁</Title1>
          <Text className="mutedText">双击封面进入页列表，双击单页进入裁切预览</Text>
        </div>
        <Button appearance="primary" icon={<Add24Regular />} onClick={importFiles}>导入</Button>
      </div>
      <div className="copybookShelf">
        {copybooks.map((copybook) => (
          <button
            key={copybook.id}
            className={selected?.id === copybook.id ? "coverTile selected" : "coverTile"}
            onClick={() => setSelected(copybook)}
            onDoubleClick={() => openCopybook(copybook)}
            onContextMenu={(event) => {
              event.preventDefault();
              setSelected(copybook);
              setEditing(copybook);
            }}
            type="button"
          >
            <div className="coverFrame">
              {covers[copybook.id] ? <img src={covers[copybook.id]} alt={copybook.title} /> : <Spinner size="small" />}
            </div>
            <Text weight="semibold" truncate>{copybook.title}</Text>
            <Text size={200} className="mutedText" truncate>{copybook.author || "未填写作者"}</Text>
          </button>
        ))}
      </div>
      {editing && (
        <MetadataDialog
          copybook={editing}
          cover={covers[editing.id] || ""}
          onCancel={() => setEditing(null)}
          onSave={(metadata) => saveMetadata(editing, metadata)}
        />
      )}
    </section>
  );
}

function BlockingOverlay({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="blockingOverlay" role="alert" aria-live="assertive">
      <Card className="blockingCard">
        <Spinner size="extra-large" />
        <Title3>{title}</Title3>
        <Text className="mutedText">{detail}</Text>
      </Card>
    </div>
  );
}

function MetadataDialog({
  copybook,
  cover,
  onCancel,
  onSave,
}: {
  copybook: Copybook;
  cover: string;
  onCancel: () => void;
  onSave: (metadata: CopybookMetadataForm) => Promise<void>;
}) {
  const [form, setForm] = useState({
    title: copybook.title,
    author: copybook.author,
    cover_source_path: "",
    crop_left_percent: ratioToPercent(copybook.crop_left_ratio),
    crop_right_percent: ratioToPercent(copybook.crop_right_ratio),
    crop_top_percent: ratioToPercent(copybook.crop_top_ratio),
    crop_bottom_percent: ratioToPercent(copybook.crop_bottom_ratio),
  });
  const [saving, setSaving] = useState(false);
  useEffect(
    () => setForm({
      title: copybook.title,
      author: copybook.author,
      cover_source_path: "",
      crop_left_percent: ratioToPercent(copybook.crop_left_ratio),
      crop_right_percent: ratioToPercent(copybook.crop_right_ratio),
      crop_top_percent: ratioToPercent(copybook.crop_top_ratio),
      crop_bottom_percent: ratioToPercent(copybook.crop_bottom_ratio),
    }),
    [copybook.id, copybook.title, copybook.author, copybook.crop_left_ratio, copybook.crop_right_ratio, copybook.crop_top_ratio, copybook.crop_bottom_ratio],
  );

  async function chooseCover() {
    const path = await api().choose_cover_image();
    if (path) setForm((current) => ({ ...current, cover_source_path: path }));
  }

  async function save() {
    setSaving(true);
    try {
      await onSave({
        title: form.title,
        author: form.author,
        cover_source_path: form.cover_source_path,
        crop_left_ratio: percentToCropRatio(form.crop_left_percent),
        crop_right_ratio: percentToCropRatio(form.crop_right_percent),
        crop_top_ratio: percentToCropRatio(form.crop_top_percent),
        crop_bottom_ratio: percentToCropRatio(form.crop_bottom_percent),
      });
    } finally {
      setSaving(false);
    }
  }

  const horizontalCropTooLarge = form.crop_left_percent + form.crop_right_percent >= 80;
  const verticalCropTooLarge = form.crop_top_percent + form.crop_bottom_percent >= 80;
  const cropTotalTooLarge = horizontalCropTooLarge || verticalCropTooLarge;

  return (
    <Dialog open>
      <DialogSurface>
        <DialogBody>
          <DialogTitle>编辑书帖信息</DialogTitle>
          <DialogContent>
            <div className="metadataDialog">
              <div className="dialogCoverFrame">
                {cover ? <img src={cover} alt={copybook.title} /> : <BookOpen24Regular />}
              </div>
              <div className="formStack">
                <Field label="名称">
                  <Input value={form.title} onChange={(_, data) => setForm({ ...form, title: data.value })} />
                </Field>
                <Field label="作者">
                  <Input value={form.author} onChange={(_, data) => setForm({ ...form, author: data.value })} />
                </Field>
                <div className="formGrid">
                  <Field label="左页边预裁切（%）" hint="识别和生成前裁掉左边缘。">
                    <Input
                      type="number"
                      min={0}
                      max={45}
                      step={0.5}
                      value={String(form.crop_left_percent)}
                      onChange={(_, data) => setForm({ ...form, crop_left_percent: Number(data.value) })}
                    />
                  </Field>
                  <Field label="右页边预裁切（%）" hint="识别和生成前裁掉右边缘。">
                    <Input
                      type="number"
                      min={0}
                      max={45}
                      step={0.5}
                      value={String(form.crop_right_percent)}
                      onChange={(_, data) => setForm({ ...form, crop_right_percent: Number(data.value) })}
                    />
                  </Field>
                  <Field label="上页边预裁切（%）" hint="识别和生成前裁掉页眉。">
                    <Input
                      type="number"
                      min={0}
                      max={45}
                      step={0.5}
                      value={String(form.crop_top_percent)}
                      onChange={(_, data) => setForm({ ...form, crop_top_percent: Number(data.value) })}
                    />
                  </Field>
                  <Field label="下页边预裁切（%）" hint="识别和生成前裁掉页脚。">
                    <Input
                      type="number"
                      min={0}
                      max={45}
                      step={0.5}
                      value={String(form.crop_bottom_percent)}
                      onChange={(_, data) => setForm({ ...form, crop_bottom_percent: Number(data.value) })}
                    />
                  </Field>
                </div>
                {horizontalCropTooLarge && <Text size={200} className="mutedText">左右预裁切合计需小于 80%。</Text>}
                {verticalCropTooLarge && <Text size={200} className="mutedText">上下预裁切合计需小于 80%。</Text>}
                <Field label="展示封面" hint={form.cover_source_path || "默认使用第一页缩略图"}>
                  <Button icon={<Image24Regular />} onClick={chooseCover}>选择封面</Button>
                </Field>
              </div>
            </div>
          </DialogContent>
          <DialogActions>
            <Button appearance="secondary" onClick={onCancel}>取消</Button>
            <Button appearance="primary" icon={<Save24Regular />} disabled={saving || !form.title.trim() || cropTotalTooLarge} onClick={save}>
              保存
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}

function Maker({
  session,
  setMessage,
  refreshStats,
  openPractice,
}: {
  session: MakerSession | null;
  setMessage: (value: string) => void;
  refreshStats: () => Promise<void>;
  openPractice: () => void;
}) {
  const [params, setParams] = useState<MakerParams>({ grid_style: "tian", cell_size_mm: 15, margin_mm: 15, dpi: 300 });
  const [sourcePreview, setSourcePreview] = useState("");
  const [previewPages, setPreviewPages] = useState<string[]>([]);
  const [previewPage, setPreviewPage] = useState(0);
  const [previewing, setPreviewing] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportName, setExportName] = useState("");
  const [exportFormat, setExportFormat] = useState<"pdf" | "png">("pdf");
  const [exporting, setExporting] = useState(false);
  const [analysis, setAnalysis] = useState<PageAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [ocrProgress, setOcrProgress] = useState("正在初始化模型");
  const [savingAnalysis, setSavingAnalysis] = useState(false);
  const [selectionDirty, setSelectionDirty] = useState(false);
  const [hasSavedSelection, setHasSavedSelection] = useState(false);
  const previewRunId = useRef(0);
  const loadRunId = useRef(0);
  const activePageId = useRef<number | null>(session?.pageId ?? null);
  const saveQueue = useRef<Promise<void>>(Promise.resolve());
  const pendingSaveCount = useRef(0);
  const paramsKey = JSON.stringify(params);
  const canExport = Boolean(
    session
    && hasSavedSelection
    && !selectionDirty
    && !savingAnalysis
  );

  async function loadSessionDefaults(pageId: number) {
    const runId = ++loadRunId.current;
    setAnalyzing(true);
    setOcrProgress("正在初始化模型");
    setAnalysis(null);
    setSelectionDirty(false);
    setHasSavedSelection(false);
    setSourcePreview("");
    try {
      const [settings, savedAnalysis, previewImage] = await Promise.all([
        api().get_settings(),
        api().analyze_page(pageId),
        api().get_page_preview(pageId),
      ]);
      if (loadRunId.current !== runId) return;
      setParams({
        grid_style: "tian",
        cell_size_mm: 15,
        margin_mm: 15,
        dpi: Number(settings.default_dpi || 300),
      });
      setAnalysis(savedAnalysis);
      setHasSavedSelection(analysisHasSelectedGlyphs(savedAnalysis));
      setSourcePreview(previewImage);
      if (savedAnalysis.warning) setMessage(savedAnalysis.warning);
    } finally {
      if (loadRunId.current === runId) {
        setAnalyzing(false);
      }
    }
  }

  async function renderPreview(runId: number) {
    if (!session) return;
    setPreviewing(true);
    try {
      const rendered = await api().render_page_previews(session.pageId, params);
      if (previewRunId.current === runId) {
        setPreviewPages(rendered);
        setPreviewPage(0);
      }
    } finally {
      if (previewRunId.current === runId) {
        setPreviewing(false);
      }
    }
  }

  async function recognizePage(force = false) {
    if (!session) return null;
    setAnalyzing(true);
    setOcrProgress("正在初始化模型");
    try {
      const result = await api().analyze_page(session.pageId, force);
      setAnalysis(result);
      setSelectionDirty(false);
      setHasSavedSelection(analysisHasSelectedGlyphs(result));
      if (result.warning) setMessage(result.warning);
      return result;
    } catch (error) {
      setMessage(String(error));
      return null;
    } finally {
      setAnalyzing(false);
    }
  }

  async function saveAnalysis(groups: GlyphGroup[]): Promise<boolean> {
    if (!session) return false;
    const pageId = session.pageId;
    pendingSaveCount.current += 1;
    setSavingAnalysis(true);
    const saveTask = saveQueue.current.then(async () => {
      await api().update_page_analysis(pageId, groups);
    });
    saveQueue.current = saveTask.catch(() => undefined);
    try {
      await saveTask;
      if (activePageId.current === pageId) {
        setHasSavedSelection(groups.some((group) => group.included && group.glyphs.some((glyph) => glyph.included)));
      }
      return true;
    } catch (error) {
      setMessage(String(error));
      return false;
    } finally {
      pendingSaveCount.current = Math.max(0, pendingSaveCount.current - 1);
      if (!pendingSaveCount.current) {
        setSavingAnalysis(false);
      }
    }
  }

  async function saveOcrGroups(groups: GlyphGroup[]): Promise<boolean> {
    if (!session) return false;
    const pageId = session.pageId;
    pendingSaveCount.current += 1;
    setSavingAnalysis(true);
    const saveTask = saveQueue.current.then(async () => {
      await api().update_page_ocr_groups(pageId, groups);
    });
    saveQueue.current = saveTask.catch(() => undefined);
    try {
      await saveTask;
      return true;
    } catch (error) {
      setMessage(String(error));
      return false;
    } finally {
      pendingSaveCount.current = Math.max(0, pendingSaveCount.current - 1);
      if (!pendingSaveCount.current) {
        setSavingAnalysis(false);
      }
    }
  }

  async function openExportDialog() {
    if (selectionDirty || savingAnalysis) {
      setMessage("正在自动保存当前选字和改字，请稍后导出");
      return;
    }
    const defaultName = await api().get_next_generated_post_name();
    setExportName(defaultName);
    setExportFormat("pdf");
    setExportDialogOpen(true);
  }

  async function exportPost() {
    if (!session) return;
    const name = exportName.trim();
    if (!name) {
      setMessage("名称不能为空");
      return;
    }
    setExporting(true);
    try {
      const post = await api().export_page_to_generated_post(session.pageId, params, name, exportFormat);
      await refreshStats();
      setExportDialogOpen(false);
      setMessage(`已保存 ${post.page_count} 页 ${exportFormat.toUpperCase()} 到练帖阁：${name}`);
      openPractice();
    } catch (error) {
      setMessage(String(error));
    } finally {
      setExporting(false);
    }
  }

  useEffect(() => {
    activePageId.current = session?.pageId ?? null;
    if (!session) {
      setAnalysis(null);
      setSelectionDirty(false);
      setHasSavedSelection(false);
      setPreviewPages([]);
      setSourcePreview("");
      setExportDialogOpen(false);
      return;
    }
    loadSessionDefaults(session.pageId).catch((error) => setMessage(String(error)));
  }, [session?.pageId]);

  useEffect(() => {
    if (!session || !exportDialogOpen) return;
    const runId = ++previewRunId.current;
    setPreviewPages([]);
    setPreviewPage(0);
    renderPreview(runId).catch((error) => setMessage(String(error)));
  }, [session?.pageId, exportDialogOpen, paramsKey]);

  useEffect(() => {
    if (!analyzing || !session) return;
    let active = true;
    async function refreshOcrProgress() {
      const diagnostics = await api().get_runtime_diagnostics(0);
      const status = diagnostics.status;
      if (
        active
        && status.operation === "ocr"
        && status.page_id === session?.pageId
        && status.message
      ) {
        setOcrProgress(status.message);
      }
    }
    refreshOcrProgress().catch(() => undefined);
    const interval = window.setInterval(() => {
      refreshOcrProgress().catch(() => undefined);
    }, 300);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [analyzing, session?.pageId]);

  return (
    <section className="makeWorkbench">
      <div className="makeTopbar">
        <div className="makeTopbarInfo">
          <Title3>{session ? `${session.copybookTitle} · 第 ${session.pageNo} 页` : "单页制帖"}</Title3>
          <Text size={200} className="mutedText">
            {session
              ? (
                savingAnalysis
                  ? "正在自动保存选字和改字。"
                  : selectionDirty
                    ? "修改将在停止操作后自动保存。"
                    : "先选字并改标注；导出时再设置布局并预览。"
              )
              : "从藏帖阁双击单页进入制帖"}
          </Text>
        </div>
        <Button icon={<LineHorizontal1Regular />} disabled={!session || analyzing || savingAnalysis} onClick={() => recognizePage(true)}>
          {analyzing ? ocrProgress : "重新识别"}
        </Button>
        <Button appearance="primary" icon={<DocumentPdf24Regular />} disabled={!session || !canExport} onClick={openExportDialog}>导出</Button>
      </div>

      <div className="makeSelectionStage">
        {!session ? (
          <div className="centerState">
            <Box24Regular />
            <Text>从藏帖阁双击单页进入制帖</Text>
          </div>
        ) : analyzing && !analysis ? (
          <div className="centerState">
            <Spinner label={`${ocrProgress}；首次使用可能需要下载本地 OCR 模型`} />
          </div>
        ) : analysis ? (
          <SelectionWorkspace
            analysis={analysis}
            source={sourcePreview}
            saving={savingAnalysis}
            recognizing={analyzing}
            onRecognizeAgain={() => recognizePage(true)}
            onSave={saveAnalysis}
            onSaveOcrGroups={saveOcrGroups}
            onDirtyChange={setSelectionDirty}
          />
        ) : (
          <div className="centerState compact">
            <Text>当前页暂无识别结果</Text>
          </div>
        )}
      </div>

      {session && (
        <Text size={200} className="mutedText makeHint">
          拖框时起点所在字会成为首字，系统按拖框主轴方向排序；多次拖框会按操作顺序追加到最终字序。
        </Text>
      )}

      <ExportPostDialog
        open={exportDialogOpen}
        name={exportName}
        saving={exporting}
        outputFormat={exportFormat}
        params={params}
        previewPages={previewPages}
        previewPage={previewPage}
        previewing={previewing}
        onNameChange={setExportName}
        onFormatChange={setExportFormat}
        onParamsChange={setParams}
        onPreviewPageChange={setPreviewPage}
        onCancel={() => setExportDialogOpen(false)}
        onSave={exportPost}
      />
    </section>
  );
}

function ExportPostDialog({
  open,
  name,
  saving,
  outputFormat,
  params,
  previewPages,
  previewPage,
  previewing,
  onNameChange,
  onFormatChange,
  onParamsChange,
  onPreviewPageChange,
  onCancel,
  onSave,
}: {
  open: boolean;
  name: string;
  saving: boolean;
  outputFormat: "pdf" | "png";
  params: MakerParams;
  previewPages: string[];
  previewPage: number;
  previewing: boolean;
  onNameChange: (value: string) => void;
  onFormatChange: (value: "pdf" | "png") => void;
  onParamsChange: (value: MakerParams) => void;
  onPreviewPageChange: (value: number) => void;
  onCancel: () => void;
  onSave: () => Promise<void>;
}) {
  if (!open) return null;
  return (
    <Dialog open>
      <DialogSurface className="exportDialogSurface">
        <DialogBody>
          <DialogTitle>保存生成帖</DialogTitle>
          <DialogContent className="exportDialogContent">
            <div className="exportDialogForm">
              <div className="formStack">
                <Field label="名称">
                  <Input value={name} onChange={(_, data) => onNameChange(data.value)} autoFocus />
                </Field>
                <Field label="格式">
                  <Select value={outputFormat} onChange={(event) => onFormatChange(event.target.value === "png" ? "png" : "pdf")}>
                    <option value="pdf">PDF</option>
                    <option value="png">PNG</option>
                  </Select>
                </Field>
              </div>
              <div className="exportDialogLayout">
                <Text weight="semibold">布局参数</Text>
                <Text size={200} className="mutedText">
                  这里只调整版式并预览导出结果。选字内容以主界面已自动保存的结果为准。
                </Text>
                <ParamToolbar params={params} update={onParamsChange} />
              </div>
            </div>
            <div className="exportDialogPreview">
              <PreviewPane
                title={`导出预览 ${previewPages.length > 1 ? `${previewPage + 1}/${previewPages.length}` : ""}`}
                image={previewPages[previewPage] || ""}
                loading={previewing || !previewPages.length}
                large
              />
              {previewPages.length > 1 && (
                <div className="previewPager">
                  <Button size="small" disabled={previewPage === 0} onClick={() => onPreviewPageChange(previewPage - 1)}>上一页</Button>
                  <Text>{previewPage + 1} / {previewPages.length}</Text>
                  <Button size="small" disabled={previewPage === previewPages.length - 1} onClick={() => onPreviewPageChange(previewPage + 1)}>下一页</Button>
                </div>
              )}
            </div>
          </DialogContent>
          <DialogActions>
            <Button appearance="secondary" disabled={saving} onClick={onCancel}>取消</Button>
            <Button appearance="primary" icon={<Save24Regular />} disabled={saving || previewing || !name.trim()} onClick={onSave}>
              导出并保存
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}

function SelectionWorkspace({
  analysis,
  source,
  saving,
  recognizing,
  onRecognizeAgain,
  onSave,
  onSaveOcrGroups,
  onDirtyChange,
}: {
  analysis: PageAnalysis;
  source: string;
  saving: boolean;
  recognizing: boolean;
  onRecognizeAgain: () => Promise<unknown>;
  onSave: (groups: GlyphGroup[]) => Promise<boolean>;
  onSaveOcrGroups: (groups: GlyphGroup[]) => Promise<boolean>;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const initialSourceGroups = cloneGlyphGroups(
    analysis.selection_mode === "ordered_stream" && analysis.ocr_groups?.length
      ? analysis.ocr_groups
      : analysis.groups,
  );
  const [sourceGroups, setSourceGroups] = useState<GlyphGroup[]>(initialSourceGroups);
  const [selectedGlyphs, setSelectedGlyphs] = useState<Glyph[]>(() => selectedStreamFromAnalysis(analysis));
  const [editingGlyph, setEditingGlyph] = useState<Glyph | null>(null);
  const [focusedGlyphId, setFocusedGlyphId] = useState<string | null>(null);
  const [selectionRect, setSelectionRect] = useState<null | { x1: number; y1: number; x2: number; y2: number }>(null);
  const [savedSignature, setSavedSignature] = useState(() => glyphSignature(selectedStreamFromAnalysis(analysis)));
  const [saveFailed, setSaveFailed] = useState(false);
  const [retryVersion, setRetryVersion] = useState(0);
  const autoSaveRunId = useRef(0);
  const onSaveRef = useRef(onSave);
  const glyphClickTimer = useRef<number | null>(null);
  const overlayDrag = useRef<null | {
    pointerId: number;
    startX: number;
    startY: number;
    overlayWidth: number;
    overlayHeight: number;
  }>(null);
  const imageWidth = Math.max(1, analysis.image_size?.[0] || 1);
  const imageHeight = Math.max(1, analysis.image_size?.[1] || 1);
  const initialSignature = glyphSignature(selectedStreamFromAnalysis(analysis));
  const currentSignature = glyphSignature(selectedGlyphs);
  const isDirty = currentSignature !== savedSignature;

  useEffect(() => {
    setSourceGroups(cloneGlyphGroups(
      analysis.selection_mode === "ordered_stream" && analysis.ocr_groups?.length
        ? analysis.ocr_groups
        : analysis.groups,
    ));
    setSelectedGlyphs(selectedStreamFromAnalysis(analysis));
    setSavedSignature(initialSignature);
    setSaveFailed(false);
    setFocusedGlyphId(null);
    setSelectionRect(null);
    setEditingGlyph(null);
  }, [analysis]);

  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

  useEffect(() => () => {
    if (glyphClickTimer.current !== null) {
      window.clearTimeout(glyphClickTimer.current);
    }
  }, []);

  useEffect(() => {
    onDirtyChange(isDirty);
  }, [isDirty, onDirtyChange]);

  const selectedIds = new Set(selectedGlyphs.map((glyph) => glyph.id));
  const cropRect = selectionRect ? normalizeRect(selectionRect) : null;
  const allGlyphs = sourceGroups.flatMap((group) => group.glyphs.filter((glyph) => glyph.included).map((glyph) => ({ groupId: group.id, glyph })));
  const selectedGroups: GlyphGroup[] = selectedGlyphs.length ? [{
    id: "selected-stream-1",
    direction: "horizontal",
    included: true,
    glyphs: selectedGlyphs.map(cloneGlyph),
  }] : [];

  useEffect(() => {
    if (!isDirty || recognizing) return;
    const runId = ++autoSaveRunId.current;
    const submittedSignature = currentSignature;
    const submittedGroups = cloneGlyphGroups(selectedGroups);
    setSaveFailed(false);
    const timeout = window.setTimeout(async () => {
      const saved = await onSaveRef.current(submittedGroups);
      if (autoSaveRunId.current !== runId) return;
      if (saved) {
        setSavedSignature(submittedSignature);
      } else {
        setSaveFailed(true);
      }
    }, 450);
    return () => window.clearTimeout(timeout);
  }, [currentSignature, isDirty, recognizing, retryVersion]);

  function appendGlyph(glyph: Glyph) {
    if (selectedIds.has(glyph.id)) return;
    onDirtyChange(true);
    setSelectedGlyphs((current) => {
      return [...current, cloneGlyph(glyph)];
    });
    setFocusedGlyphId(glyph.id);
  }

  function scheduleAppendGlyph(glyph: Glyph) {
    if (glyphClickTimer.current !== null) {
      window.clearTimeout(glyphClickTimer.current);
    }
    glyphClickTimer.current = window.setTimeout(() => {
      appendGlyph(glyph);
      glyphClickTimer.current = null;
    }, 220);
  }

  function openDetailedEditor(glyph: Glyph) {
    if (glyphClickTimer.current !== null) {
      window.clearTimeout(glyphClickTimer.current);
      glyphClickTimer.current = null;
    }
    setEditingGlyph(cloneGlyph(glyph));
  }

  function removeGlyph(glyphId: string) {
    if (!selectedIds.has(glyphId)) return;
    onDirtyChange(true);
    setSelectedGlyphs((current) => current.filter((glyph) => glyph.id !== glyphId));
    setFocusedGlyphId((current) => current === glyphId ? null : current);
  }

  async function saveDetailedGlyph(updatedGlyph: Glyph) {
    const updatedGroups = sourceGroups.map((group) => ({
      ...group,
      glyphs: group.glyphs.map((glyph) => glyph.id === updatedGlyph.id ? cloneGlyph(updatedGlyph) : cloneGlyph(glyph)),
    }));
    const saved = await onSaveOcrGroups(updatedGroups);
    if (!saved) return;
    setSourceGroups(updatedGroups);
    setSelectedGlyphs((current) => current.map((glyph) => (
      glyph.id === updatedGlyph.id ? cloneGlyph(updatedGlyph) : glyph
    )));
    setFocusedGlyphId(updatedGlyph.id);
    setEditingGlyph(null);
  }

  function commitSelection() {
    const drag = overlayDrag.current;
    if (!drag || !selectionRect) return;
    const batch = selectGlyphBatch(allGlyphs, selectionRect, selectedIds);
    if (batch.length) {
      onDirtyChange(true);
      setSelectedGlyphs((current) => [...current, ...batch.map(cloneGlyph)]);
      setFocusedGlyphId(batch[batch.length - 1].id);
    }
    overlayDrag.current = null;
    setSelectionRect(null);
  }

  return (
    <>
      <div className="analysisWorkspace">
      <div className="analysisWorkspaceContent">
        <div className="analysisCanvas">
          {source ? <img src={source} alt="待选字原图" /> : <Spinner />}
          <div
            className="analysisOverlay"
            onPointerDown={(event) => {
              const overlay = event.currentTarget;
              overlay.setPointerCapture(event.pointerId);
              overlayDrag.current = {
                pointerId: event.pointerId,
                startX: (event.nativeEvent.offsetX / overlay.clientWidth) * imageWidth,
                startY: (event.nativeEvent.offsetY / overlay.clientHeight) * imageHeight,
                overlayWidth: overlay.clientWidth,
                overlayHeight: overlay.clientHeight,
              };
              setSelectionRect({
                x1: (event.nativeEvent.offsetX / overlay.clientWidth) * imageWidth,
                y1: (event.nativeEvent.offsetY / overlay.clientHeight) * imageHeight,
                x2: (event.nativeEvent.offsetX / overlay.clientWidth) * imageWidth,
                y2: (event.nativeEvent.offsetY / overlay.clientHeight) * imageHeight,
              });
            }}
            onPointerMove={(event) => {
              const drag = overlayDrag.current;
              if (!drag || drag.pointerId !== event.pointerId) return;
              setSelectionRect({
                x1: drag.startX,
                y1: drag.startY,
                x2: (event.nativeEvent.offsetX / drag.overlayWidth) * imageWidth,
                y2: (event.nativeEvent.offsetY / drag.overlayHeight) * imageHeight,
              });
            }}
            onPointerUp={(event) => {
              if (overlayDrag.current?.pointerId !== event.pointerId) return;
              commitSelection();
            }}
            onPointerCancel={() => {
              overlayDrag.current = null;
              setSelectionRect(null);
            }}
          >
            {allGlyphs.map(({ glyph }) => {
              const [left, top, right, bottom] = glyph.bbox;
              const isSelected = selectedIds.has(glyph.id);
              const selectedIndex = selectedGlyphs.findIndex((item) => item.id === glyph.id);
              const selectedGlyph = selectedGlyphs.find((item) => item.id === glyph.id) || glyph;
              return (
                <div
                  key={glyph.id}
                  title={`${selectedGlyph.text} · ${Math.round(glyph.confidence * 100)}%`}
                  className={[
                    "glyphBox",
                    glyph.confidence < 0.75 ? "lowConfidence" : "",
                    isSelected ? "selected" : "",
                    focusedGlyphId === glyph.id ? "focused" : "",
                  ].filter(Boolean).join(" ")}
                  style={{
                    left: `${left / imageWidth * 100}%`,
                    top: `${top / imageHeight * 100}%`,
                    width: `${Math.max(0.3, (right - left) / imageWidth * 100)}%`,
                    height: `${Math.max(0.3, (bottom - top) / imageHeight * 100)}%`,
                  }}
                  onDoubleClick={(event) => {
                    event.stopPropagation();
                    openDetailedEditor(selectedGlyph);
                  }}
                >
                  {!isSelected ? (
                    <button
                      type="button"
                      className="glyphBoxButton"
                      aria-label={`选择识别字 ${glyph.text}`}
                      onPointerDown={(event) => event.stopPropagation()}
                      onClick={(event) => {
                        event.stopPropagation();
                        scheduleAppendGlyph(glyph);
                      }}
                    >
                      <span className="glyphStatusBadge recognized">{glyph.text}</span>
                    </button>
                  ) : (
                    <div className="glyphBoxSelected" onPointerDown={(event) => event.stopPropagation()}>
                      <span className="glyphStatusBadge selected" aria-label={`已选择 ${selectedGlyph.text}`}>✓</span>
                      <button
                        type="button"
                        className="glyphDeleteButton"
                        aria-label="删除字符"
                        onClick={(event) => {
                          event.stopPropagation();
                          removeGlyph(glyph.id);
                        }}
                      >
                        ×
                      </button>
                      <span className="glyphOrderBadge">{selectedIndex + 1}</span>
                    </div>
                  )}
                </div>
              );
            })}
            {cropRect && (
              <div
                className="selectionRect"
                style={{
                  left: `${cropRect.left / imageWidth * 100}%`,
                  top: `${cropRect.top / imageHeight * 100}%`,
                  width: `${Math.max(0.3, (cropRect.right - cropRect.left) / imageWidth * 100)}%`,
                  height: `${Math.max(0.3, (cropRect.bottom - cropRect.top) / imageHeight * 100)}%`,
                }}
              />
            )}
          </div>
        </div>
        <div className="analysisList">
          <Text size={200} className="mutedText">
            {analysis.model_id} · {analysis.engine === "fallback" ? "降级定位" : "本地 OCR"} · 点击可追加单字，拖框会按起点和主轴方向自动排序。
          </Text>
          <Text size={200} className="mutedText">
            已选 {selectedGlyphs.length} 字。双击任意识别框可放大编辑文字和边界；右上角可删除已选字。
          </Text>
          <Text size={200} className="mutedText">
            {saveFailed
              ? "自动保存失败，修改仍保留在当前页面。"
              : saving
                ? "正在自动保存……"
                : isDirty
                  ? "等待自动保存……"
                  : "当前修改已自动保存。"}
          </Text>
          {!selectedGlyphs.length && (
            <div className="centerState compact">
              <Text>先点击或拖框选择要制帖的字</Text>
            </div>
          )}
        </div>
      </div>
      <div className="analysisWorkspaceActions">
        <Button disabled={saving || recognizing} onClick={onRecognizeAgain}>重新识别</Button>
        {saveFailed && (
          <Button appearance="primary" disabled={saving || recognizing} onClick={() => setRetryVersion((value) => value + 1)}>
            重试保存
          </Button>
        )}
      </div>
      </div>
      {editingGlyph && (
        <GlyphRegionEditor
          source={source}
          imageWidth={imageWidth}
          imageHeight={imageHeight}
          glyph={editingGlyph}
          saving={saving}
          onCancel={() => setEditingGlyph(null)}
          onSave={saveDetailedGlyph}
        />
      )}
    </>
  );
}

function GlyphRegionEditor({
  source,
  imageWidth,
  imageHeight,
  glyph,
  saving,
  onCancel,
  onSave,
}: {
  source: string;
  imageWidth: number;
  imageHeight: number;
  glyph: Glyph;
  saving: boolean;
  onCancel: () => void;
  onSave: (glyph: Glyph) => Promise<void>;
}) {
  type BoxEdge = "left" | "right" | "top" | "bottom";
  const [draft, setDraft] = useState<Glyph>(() => cloneGlyph(glyph));
  const drag = useRef<null | {
    edge: BoxEdge;
    pointerId: number;
    rect: DOMRect;
  }>(null);
  const [left, top, right, bottom] = glyph.bbox;
  const glyphWidth = Math.max(1, right - left);
  const glyphHeight = Math.max(1, bottom - top);
  const padding = Math.max(24, Math.max(glyphWidth, glyphHeight) * 1.35);
  const focusLeft = Math.max(0, left - padding);
  const focusTop = Math.max(0, top - padding);
  const focusRight = Math.min(imageWidth, right + padding);
  const focusBottom = Math.min(imageHeight, bottom + padding);
  const focusWidth = Math.max(1, focusRight - focusLeft);
  const focusHeight = Math.max(1, focusBottom - focusTop);

  useEffect(() => {
    setDraft(cloneGlyph(glyph));
  }, [glyph]);

  function beginDrag(edge: BoxEdge, event: ReactPointerEvent<HTMLButtonElement>) {
    const canvas = event.currentTarget.closest(".glyphRegionCanvas");
    if (!(canvas instanceof HTMLElement)) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = {
      edge,
      pointerId: event.pointerId,
      rect: canvas.getBoundingClientRect(),
    };
  }

  function moveDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    const current = drag.current;
    if (!current || current.pointerId !== event.pointerId) return;
    const x = focusLeft + Math.max(0, Math.min(1, (event.clientX - current.rect.left) / Math.max(1, current.rect.width))) * focusWidth;
    const y = focusTop + Math.max(0, Math.min(1, (event.clientY - current.rect.top) / Math.max(1, current.rect.height))) * focusHeight;
    setDraft((value) => {
      const bbox = [...value.bbox] as [number, number, number, number];
      if (current.edge === "left") bbox[0] = Math.max(focusLeft, Math.min(Math.round(x), bbox[2] - 1));
      if (current.edge === "right") bbox[2] = Math.min(focusRight, Math.max(Math.round(x), bbox[0] + 1));
      if (current.edge === "top") bbox[1] = Math.max(focusTop, Math.min(Math.round(y), bbox[3] - 1));
      if (current.edge === "bottom") bbox[3] = Math.min(focusBottom, Math.max(Math.round(y), bbox[1] + 1));
      return { ...value, bbox };
    });
  }

  function endDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    if (drag.current?.pointerId === event.pointerId) {
      drag.current = null;
    }
  }

  async function save() {
    const [draftLeft, draftTop, draftRight, draftBottom] = draft.bbox;
    await onSave({
      ...cloneGlyph(draft),
      text: draft.text.trim(),
      kind: /^[\p{P}]+$/u.test(draft.text.trim()) ? "punctuation" : "character",
      polygon: [
        [draftLeft, draftTop],
        [draftRight, draftTop],
        [draftRight, draftBottom],
        [draftLeft, draftBottom],
      ],
    });
  }

  return (
    <Dialog open>
      <DialogSurface className="glyphRegionDialogSurface">
        <DialogBody>
          <DialogTitle>编辑识别字框</DialogTitle>
          <DialogContent className="glyphRegionDialogContent">
            <Field label="识别文字">
              <Input
                value={draft.text}
                autoFocus
                onChange={(_, data) => setDraft((value) => ({ ...value, text: data.value }))}
              />
            </Field>
            <Text size={200} className="mutedText">拖动蓝框的四条边调整识别范围，画面已聚焦到当前字周围。</Text>
            <div className="glyphRegionViewport">
              {source ? (
                <div
                  className="glyphRegionCanvas"
                  style={{ aspectRatio: `${focusWidth} / ${focusHeight}` }}
                >
                  <img
                    src={source}
                    alt="当前识别字周围区域"
                    draggable={false}
                    style={{
                      width: `${imageWidth / focusWidth * 100}%`,
                      height: `${imageHeight / focusHeight * 100}%`,
                      left: `${-focusLeft / focusWidth * 100}%`,
                      top: `${-focusTop / focusHeight * 100}%`,
                    }}
                  />
                  <div
                    className="glyphRegionBox"
                    style={{
                      left: `${(draft.bbox[0] - focusLeft) / focusWidth * 100}%`,
                      top: `${(draft.bbox[1] - focusTop) / focusHeight * 100}%`,
                      width: `${(draft.bbox[2] - draft.bbox[0]) / focusWidth * 100}%`,
                      height: `${(draft.bbox[3] - draft.bbox[1]) / focusHeight * 100}%`,
                    }}
                  >
                    {(["left", "right", "top", "bottom"] as BoxEdge[]).map((edge) => (
                      <button
                        key={edge}
                        type="button"
                        aria-label={`拖动${edge}字框边`}
                        className={`glyphRegionHandle ${edge}`}
                        onPointerDown={(event) => beginDrag(edge, event)}
                        onPointerMove={moveDrag}
                        onPointerUp={endDrag}
                        onPointerCancel={endDrag}
                      />
                    ))}
                  </div>
                </div>
              ) : <Spinner label="正在加载页面图像" />}
            </div>
            <Text size={100} className="mutedText">
              坐标：{draft.bbox.join(", ")}
            </Text>
          </DialogContent>
          <DialogActions>
            <Button disabled={saving} onClick={onCancel}>取消</Button>
            <Button appearance="primary" disabled={saving || !draft.text.trim()} onClick={() => save().catch(() => undefined)}>
              {saving ? "保存中" : "保存"}
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}

function VisualCropEditor({
  image,
  draft,
  loading,
  onChange,
}: {
  image: string;
  draft: PageCropDraft;
  loading: boolean;
  onChange: (value: PageCropDraft) => void;
}) {
  type CropEdge = "left" | "right" | "top" | "bottom";
  const drag = useRef<null | {
    edge: CropEdge;
    pointerId: number;
    rect: DOMRect;
  }>(null);

  function beginDrag(edge: CropEdge, event: ReactPointerEvent<HTMLButtonElement>) {
    const canvas = event.currentTarget.closest(".visualCropCanvas");
    if (!(canvas instanceof HTMLElement)) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = {
      edge,
      pointerId: event.pointerId,
      rect: canvas.getBoundingClientRect(),
    };
  }

  function moveDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    const current = drag.current;
    if (!current || current.pointerId !== event.pointerId) return;
    const x = Math.max(0, Math.min(1, (event.clientX - current.rect.left) / Math.max(1, current.rect.width)));
    const y = Math.max(0, Math.min(1, (event.clientY - current.rect.top) / Math.max(1, current.rect.height)));
    const next = { ...draft };
    if (current.edge === "left") {
      next.leftPercent = Math.min(45, Math.max(0, x * 100), 79.5 - draft.rightPercent);
    } else if (current.edge === "right") {
      next.rightPercent = Math.min(45, Math.max(0, (1 - x) * 100), 79.5 - draft.leftPercent);
    } else if (current.edge === "top") {
      next.topPercent = Math.min(45, Math.max(0, y * 100), 79.5 - draft.bottomPercent);
    } else {
      next.bottomPercent = Math.min(45, Math.max(0, (1 - y) * 100), 79.5 - draft.topPercent);
    }
    next.leftPercent = Number(next.leftPercent.toFixed(2));
    next.rightPercent = Number(next.rightPercent.toFixed(2));
    next.topPercent = Number(next.topPercent.toFixed(2));
    next.bottomPercent = Number(next.bottomPercent.toFixed(2));
    onChange(next);
  }

  function endDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    if (drag.current?.pointerId === event.pointerId) {
      drag.current = null;
    }
  }

  if (loading) {
    return <div className="visualCropLoading"><Spinner label="正在加载旋转前裁剪预览" /></div>;
  }
  return (
    <div className="visualCropEditor">
      <Text size={200} weight="semibold">OCR 预裁剪范围</Text>
      <div className="visualCropViewport">
        <div className="visualCropCanvas">
          <img src={image} alt="待旋转和裁剪的页面" draggable={false} />
          <div
            className="visualCropSelection"
            style={{
              left: `${draft.leftPercent}%`,
              right: `${draft.rightPercent}%`,
              top: `${draft.topPercent}%`,
              bottom: `${draft.bottomPercent}%`,
            }}
          >
            {(["left", "right", "top", "bottom"] as CropEdge[]).map((edge) => (
              <button
                key={edge}
                type="button"
                aria-label={`拖动${edge}裁剪边`}
                className={`visualCropHandle ${edge}`}
                onPointerDown={(event) => beginDrag(edge, event)}
                onPointerMove={moveDrag}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function PreviewPane({ title, image, loading, large = false }: { title: string; image: string; loading: boolean; large?: boolean }) {
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragStart = useRef<{ pointerX: number; pointerY: number; offsetX: number; offsetY: number } | null>(null);

  useEffect(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
    dragStart.current = null;
  }, [image]);

  function handleWheel(event: ReactWheelEvent<HTMLDivElement>) {
    if (loading || !image) return;
    event.preventDefault();
    const delta = event.deltaY < 0 ? 0.12 : -0.12;
    setScale((current) => Math.max(1, Math.min(4, Number((current + delta).toFixed(2)))));
  }

  function handleMouseDown(event: ReactMouseEvent<HTMLDivElement>) {
    if (loading || !image) return;
    dragStart.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      offsetX: offset.x,
      offsetY: offset.y,
    };
  }

  function handleMouseMove(event: ReactMouseEvent<HTMLDivElement>) {
    const start = dragStart.current;
    if (!start) return;
    setOffset({
      x: start.offsetX + event.clientX - start.pointerX,
      y: start.offsetY + event.clientY - start.pointerY,
    });
  }

  function stopDragging() {
    dragStart.current = null;
  }

  function resetView() {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  }

  return (
    <div className={large ? "previewPane large" : "previewPane"}>
      <Text size={200} weight="semibold" className="previewPaneTitle">{title}</Text>
      <div
        className={scale > 1 ? "previewPaneCanvas draggable" : "previewPaneCanvas"}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={stopDragging}
        onMouseLeave={stopDragging}
        onDoubleClick={resetView}
      >
        {loading ? (
          <Spinner label={title === "原图" ? "正在加载原图" : "正在渲染预览"} />
        ) : (
          <div className="previewZoomSurface">
            <img
              className="previewImage"
              src={image}
              alt={title}
              draggable={false}
              style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function ParamToolbar({ params, update }: { params: MakerParams; update: (value: MakerParams) => void }) {
  return (
    <div className="paramToolbar">
      <Field label="格子" size="small">
        <Select size="small" value={params.grid_style} onChange={(event) => update({ ...params, grid_style: event.target.value === "mi" ? "mi" : "tian" })}>
          <option value="tian">田字格</option>
          <option value="mi">米字格</option>
        </Select>
      </Field>
      <Field label="格宽 mm" size="small"><Input size="small" type="number" min={10} max={30} step="0.5" value={String(params.cell_size_mm)} onChange={(_, data) => update({ ...params, cell_size_mm: Number(data.value) })} /></Field>
      <Field label="边距 mm" size="small"><Input size="small" type="number" min={5} max={30} step="0.5" value={String(params.margin_mm)} onChange={(_, data) => update({ ...params, margin_mm: Number(data.value) })} /></Field>
    </div>
  );
}

function cloneGlyph(glyph: Glyph): Glyph {
  return {
    ...glyph,
    bbox: [...glyph.bbox] as [number, number, number, number],
    polygon: glyph.polygon ? glyph.polygon.map((point) => [...point]) : undefined,
  };
}

function cloneGlyphGroups(groups: GlyphGroup[]): GlyphGroup[] {
  return JSON.parse(JSON.stringify(groups)) as GlyphGroup[];
}

function glyphSignature(glyphs: Glyph[]) {
  return JSON.stringify(glyphs.map((glyph) => ({
    id: glyph.id,
    text: glyph.text,
    kind: glyph.kind,
    included: glyph.included,
  })));
}

function analysisHasSelectedGlyphs(analysis: PageAnalysis) {
  return (
    analysis.selection_mode === "ordered_stream"
    && analysis.groups.some((group) => group.included && group.glyphs.some((glyph) => glyph.included))
  );
}

function selectedStreamFromAnalysis(analysis: PageAnalysis): Glyph[] {
  if (analysis.selection_mode !== "ordered_stream") return [];
  return analysis.groups.flatMap((group) => group.glyphs.filter((glyph) => glyph.included).map(cloneGlyph));
}

function normalizeRect(rect: { x1: number; y1: number; x2: number; y2: number }) {
  return {
    left: Math.min(rect.x1, rect.x2),
    right: Math.max(rect.x1, rect.x2),
    top: Math.min(rect.y1, rect.y2),
    bottom: Math.max(rect.y1, rect.y2),
  };
}

function selectGlyphBatch(
  allGlyphs: Array<{ groupId: string; glyph: Glyph }>,
  dragRect: { x1: number; y1: number; x2: number; y2: number },
  selectedIds: Set<string>,
): Glyph[] {
  const rect = normalizeRect(dragRect);
  const dx = dragRect.x2 - dragRect.x1;
  const dy = dragRect.y2 - dragRect.y1;
  const horizontal = Math.abs(dx) >= Math.abs(dy);
  const direction = horizontal ? (dx >= 0 ? 1 : -1) : (dy >= 0 ? 1 : -1);
  const candidates = allGlyphs
    .filter(({ glyph }) => {
      const center = glyphCenter(glyph);
      return (
        center.x >= rect.left
        && center.x <= rect.right
        && center.y >= rect.top
        && center.y <= rect.bottom
        && !selectedIds.has(glyph.id)
      );
    })
    .map(({ glyph }) => glyph);
  if (!candidates.length) return [];

  const startGlyph = candidates.find((glyph) => pointInBBox(dragRect.x1, dragRect.y1, glyph.bbox))
    || candidates.slice().sort((a, b) => distanceToPoint(glyphCenter(a), dragRect.x1, dragRect.y1) - distanceToPoint(glyphCenter(b), dragRect.x1, dragRect.y1))[0];
  const sorted = candidates.slice().sort((a, b) => {
    const aCenter = glyphCenter(a);
    const bCenter = glyphCenter(b);
    const primary = horizontal ? (aCenter.x - bCenter.x) : (aCenter.y - bCenter.y);
    if (Math.abs(primary) > 1) return primary * direction;
    const secondary = horizontal ? (aCenter.y - bCenter.y) : (aCenter.x - bCenter.x);
    return secondary;
  });
  return [startGlyph, ...sorted.filter((glyph) => glyph.id !== startGlyph.id)];
}

function glyphCenter(glyph: Glyph) {
  const [left, top, right, bottom] = glyph.bbox;
  return {
    x: (left + right) / 2,
    y: (top + bottom) / 2,
  };
}

function pointInBBox(x: number, y: number, bbox: [number, number, number, number]) {
  return x >= bbox[0] && x <= bbox[2] && y >= bbox[1] && y <= bbox[3];
}

function distanceToPoint(point: { x: number; y: number }, x: number, y: number) {
  return Math.hypot(point.x - x, point.y - y);
}

function Dictionary({ setMessage }: { setMessage: (value: string) => void }) {
  const [query, setQuery] = useState("");
  const [copybookId, setCopybookId] = useState("");
  const [author, setAuthor] = useState("");
  const [results, setResults] = useState<GlyphOccurrence[]>([]);
  const [total, setTotal] = useState(0);
  const [images, setImages] = useState<Record<number, string>>({});
  const [filters, setFilters] = useState<{
    copybooks: Array<{ id: number; title: string; author: string; glyph_count: number }>;
    authors: Array<{ author: string; glyph_count: number }>;
  }>({ copybooks: [], authors: [] });
  const [loading, setLoading] = useState(false);

  async function runSearch(append = false) {
    const character = Array.from(query.trim());
    if (character.length !== 1 || !isHanCharacter(character[0])) {
      setMessage("请输入一个汉字");
      return;
    }
    setLoading(true);
    try {
      const offset = append ? results.length : 0;
      const [response, availableFilters] = await Promise.all([
        api().search_glyphs(
          character[0],
          copybookId ? Number(copybookId) : null,
          author,
          60,
          offset,
        ),
        append ? Promise.resolve(filters) : api().list_glyph_filters(character[0]),
      ]);
      setResults((current) => append ? [...current, ...response.items] : response.items);
      setTotal(response.total);
      if (!append) setFilters(availableFilters);
      void loadGlyphImages(response.items, setImages);
    } catch (error) {
      setMessage(String(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (results.length) void runSearch(false);
  }, [copybookId, author]);

  return (
    <section className="featurePage">
      <div className="sectionHeader">
        <div>
          <Title1>字典</Title1>
          <Text>检索已经识别的书帖单字，人工校对结果会优先显示。</Text>
        </div>
      </div>
      <div className="dictionaryToolbar">
        <Field label="单字">
          <Input
            value={query}
            placeholder="输入一个汉字"
            onChange={(_, data) => setQuery(Array.from(data.value).slice(0, 1).join(""))}
            onKeyDown={(event) => {
              if (event.key === "Enter") void runSearch(false);
            }}
          />
        </Field>
        <Field label="书帖">
          <Select value={copybookId} onChange={(_, data) => setCopybookId(data.value)}>
            <option value="">全部书帖</option>
            {filters.copybooks.map((copybook) => (
              <option key={copybook.id} value={String(copybook.id)}>
                {copybook.title}（{copybook.glyph_count}）
              </option>
            ))}
          </Select>
        </Field>
        <Field label="作者">
          <Select value={author} onChange={(_, data) => setAuthor(data.value)}>
            <option value="">全部作者</option>
            {filters.authors.map((item) => (
              <option key={item.author} value={item.author}>{item.author}（{item.glyph_count}）</option>
            ))}
          </Select>
        </Field>
        <Button appearance="primary" icon={<Search24Regular />} onClick={() => void runSearch(false)} disabled={loading}>
          搜索
        </Button>
      </div>
      <div className="resultSummary">
        <Text>{total ? `共找到 ${total} 个字样` : "输入单字开始搜索"}</Text>
        {loading && <Spinner size="tiny" />}
      </div>
      <div className="glyphResultGrid">
        {results.map((glyph) => (
          <GlyphResultCard key={glyph.id} glyph={glyph} image={images[glyph.id]} />
        ))}
      </div>
      {results.length < total && (
        <Button onClick={() => void runSearch(true)} disabled={loading}>加载更多</Button>
      )}
    </section>
  );
}

function GlyphResultCard({
  glyph,
  image,
  onClick,
  selected = false,
}: {
  glyph: GlyphOccurrence;
  image?: string;
  onClick?: () => void;
  selected?: boolean;
}) {
  return (
    <Card
      className={`glyphResultCard ${selected ? "selected" : ""} ${onClick ? "clickable" : ""}`}
      onClick={onClick}
    >
      <div className="glyphResultImage">
        {image ? <img src={image} alt={glyph.text} /> : <Spinner size="tiny" />}
      </div>
      <Text weight="semibold">{glyph.copybook_title}</Text>
      <Text size={200}>{glyph.copybook_author || "佚名"} · 第 {glyph.page_no} 页</Text>
      <Text size={200}>置信度 {Math.round(glyph.confidence * 100)}%</Text>
    </Card>
  );
}

function CollectionWorkspace({ setMessage }: { setMessage: (value: string) => void }) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Collection | null>(null);
  const [newName, setNewName] = useState("");
  const [preview, setPreview] = useState("");
  const [slotImages, setSlotImages] = useState<Record<number, string>>({});
  const [candidatePosition, setCandidatePosition] = useState<number | null>(null);
  const [candidates, setCandidates] = useState<GlyphOccurrence[]>([]);
  const [candidateImages, setCandidateImages] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState(false);
  const savedSignature = useRef("");

  async function loadCollections(preferredId?: number) {
    const loaded = await api().list_collections();
    setCollections(loaded);
    const target = preferredId ?? selectedId ?? loaded[0]?.id;
    if (target) await openCollection(target);
  }

  async function openCollection(collectionId: number) {
    const loaded = await api().get_collection(collectionId);
    setSelectedId(collectionId);
    setDraft(loaded);
    savedSignature.current = collectionSignature(loaded);
    setSlotImages({});
    void loadCollectionImages(loaded, setSlotImages);
    try {
      setPreview(await api().render_collection_preview(collectionId));
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function createCollection() {
    if (!newName.trim()) {
      setMessage("集字方案名称不能为空");
      return;
    }
    try {
      const created = await api().create_collection(newName.trim());
      setNewName("");
      await loadCollections(created.id);
    } catch (error) {
      setMessage(String(error));
    }
  }

  useEffect(() => {
    loadCollections().catch((error) => setMessage(String(error)));
  }, []);

  useEffect(() => {
    if (!draft || collectionSignature(draft) === savedSignature.current) return;
    const timeout = window.setTimeout(async () => {
      setSaving(true);
      try {
        const updated = await api().update_collection(draft.id, {
          name: draft.name,
          input_text: draft.input_text,
          direction: draft.direction,
          line_capacity: draft.line_capacity,
          background: draft.background,
        });
        savedSignature.current = collectionSignature(updated);
        setDraft(updated);
        setCollections((current) => current.map((item) => item.id === updated.id ? updated : item));
        setSlotImages({});
        void loadCollectionImages(updated, setSlotImages);
        setPreview(await api().render_collection_preview(updated.id));
      } catch (error) {
        setMessage(String(error));
      } finally {
        setSaving(false);
      }
    }, 600);
    return () => window.clearTimeout(timeout);
  }, [draft?.name, draft?.input_text, draft?.direction, draft?.line_capacity, draft?.background]);

  async function removeCollection() {
    if (!draft || !window.confirm(`删除集字方案“${draft.name}”？`)) return;
    try {
      await api().delete_collection(draft.id);
      setDraft(null);
      setSelectedId(null);
      setPreview("");
      await loadCollections();
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function openCandidates(position: number, character: string) {
    try {
      const response = await api().search_glyphs(character, null, "", 200, 0);
      setCandidatePosition(position);
      setCandidates(response.items);
      setCandidateImages({});
      void loadGlyphImages(response.items, setCandidateImages);
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function chooseCandidate(occurrenceId: number) {
    if (!draft || candidatePosition === null) return;
    setSaving(true);
    try {
      const updated = await api().update_collection(draft.id, {
        selections: [{ position: candidatePosition, occurrence_id: occurrenceId }],
      });
      savedSignature.current = collectionSignature(updated);
      setDraft(updated);
      setCandidatePosition(null);
      setSlotImages({});
      void loadCollectionImages(updated, setSlotImages);
      setPreview(await api().render_collection_preview(updated.id));
    } catch (error) {
      setMessage(String(error));
    } finally {
      setSaving(false);
    }
  }

  async function exportPng() {
    if (!draft) return;
    try {
      const result = await api().export_collection_png(draft.id);
      setMessage(`已导出：${result.output_path}`);
    } catch (error) {
      setMessage(String(error));
    }
  }

  return (
    <section className="featurePage collectionPage">
      <div className="sectionHeader">
        <div>
          <Title1>集字</Title1>
          <Text>输入文字后自动匹配字样，点击单字可更换来源。</Text>
        </div>
        {saving && <Spinner size="tiny" label="正在保存" />}
      </div>
      <div className="collectionWorkspace">
        <aside className="collectionSidebar">
          <div className="collectionCreate">
            <Input value={newName} placeholder="新方案名称" onChange={(_, data) => setNewName(data.value)} />
            <Button appearance="primary" icon={<Add24Regular />} onClick={() => void createCollection()}>新建</Button>
          </div>
          <div className="collectionList">
            {collections.map((collection) => (
              <button
                key={collection.id}
                type="button"
                className={`collectionListItem ${selectedId === collection.id ? "selected" : ""}`}
                onClick={() => void openCollection(collection.id)}
              >
                <span>{collection.name}</span>
                <small>{collection.input_text.slice(0, 18) || "尚未输入文字"}</small>
              </button>
            ))}
          </div>
        </aside>
        {draft ? (
          <div className="collectionEditor">
            <div className="collectionControls">
              <Field label="方案名称">
                <Input value={draft.name} onChange={(_, data) => setDraft({ ...draft, name: data.value })} />
              </Field>
              <Field label="排版方向">
                <Select value={draft.direction} onChange={(_, data) => setDraft({ ...draft, direction: data.value as Collection["direction"] })}>
                  <option value="horizontal">横排</option>
                  <option value="vertical">竖排</option>
                </Select>
              </Field>
              <Field label={draft.direction === "horizontal" ? "每行字数" : "每列字数"}>
                <Input
                  type="number"
                  min={1}
                  max={50}
                  value={String(draft.line_capacity)}
                  onChange={(_, data) => setDraft({ ...draft, line_capacity: Math.max(1, Math.min(50, Number(data.value) || 1)) })}
                />
              </Field>
              <Field label="图片背景">
                <Select value={draft.background} onChange={(_, data) => setDraft({ ...draft, background: data.value as Collection["background"] })}>
                  <option value="transparent">透明</option>
                  <option value="white">白色</option>
                </Select>
              </Field>
              <Button icon={<Delete24Regular />} onClick={() => void removeCollection()}>删除</Button>
              <Button appearance="primary" icon={<Image24Regular />} onClick={() => void exportPng()}>导出 PNG</Button>
            </div>
            <Field label="集字内容">
              <Textarea
                resize="vertical"
                rows={4}
                value={draft.input_text}
                placeholder="输入要集字的文字；换行会保留在排版中"
                onChange={(_, data) => setDraft({ ...draft, input_text: data.value })}
              />
            </Field>
            <div className="collectionContent">
              <div>
                <Text weight="semibold">逐字选择</Text>
                <div className="collectionSlots">
                  {Array.from(draft.input_text).map((character, position) => {
                    if (character === "\n") return <div className="collectionLineBreak" key={`break-${position}`} />;
                    const item = draft.items?.find((candidate) => candidate.position === position);
                    const selectable = isHanCharacter(character);
                    return (
                      <button
                        type="button"
                        key={`${position}-${character}`}
                        className={`collectionSlot ${selectable ? "selectable" : ""} ${selectable && !item?.occurrence_id ? "missing" : ""}`}
                        disabled={!selectable}
                        onClick={() => void openCandidates(position, character)}
                      >
                        {item?.occurrence_id && slotImages[item.occurrence_id]
                          ? <img src={slotImages[item.occurrence_id]} alt={character} />
                          : <span>{character === " " ? "空格" : character}</span>}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className={`collectionPreview ${draft.background}`}>
                {preview ? <img src={preview} alt={`${draft.name}预览`} /> : <Spinner label="正在生成预览" />}
              </div>
            </div>
          </div>
        ) : (
          <div className="emptyState"><Text>新建或选择一个集字方案</Text></div>
        )}
      </div>
      <Dialog open={candidatePosition !== null} onOpenChange={(_, data) => !data.open && setCandidatePosition(null)}>
        <DialogSurface className="candidateDialog">
          <DialogBody>
            <DialogTitle>选择字样</DialogTitle>
            <DialogContent>
              <div className="glyphResultGrid">
                {candidates.map((glyph) => (
                  <GlyphResultCard
                    key={glyph.id}
                    glyph={glyph}
                    image={candidateImages[glyph.id]}
                    selected={draft?.items?.some((item) => item.position === candidatePosition && item.occurrence_id === glyph.id)}
                    onClick={() => void chooseCandidate(glyph.id)}
                  />
                ))}
              </div>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setCandidatePosition(null)}>关闭</Button>
            </DialogActions>
          </DialogBody>
        </DialogSurface>
      </Dialog>
    </section>
  );
}

async function loadGlyphImages(
  glyphs: GlyphOccurrence[],
  setter: Dispatch<SetStateAction<Record<number, string>>>,
) {
  const queue = [...glyphs];
  const workers = Array.from({ length: Math.min(6, queue.length) }, async () => {
    while (queue.length) {
      const glyph = queue.shift();
      if (!glyph) return;
      try {
        const image = await api().get_glyph_image(glyph.id);
        setter((current) => ({ ...current, [glyph.id]: image }));
      } catch {
        // A stale candidate can disappear after its source page is reprocessed.
      }
    }
  });
  await Promise.all(workers);
}

async function loadCollectionImages(
  collection: Collection,
  setter: Dispatch<SetStateAction<Record<number, string>>>,
) {
  const ids = [...new Set((collection.items || []).map((item) => item.occurrence_id).filter((id): id is number => id !== null))];
  await Promise.all(ids.map(async (id) => {
    try {
      const image = await api().get_glyph_image(id);
      setter((current) => ({ ...current, [id]: image }));
    } catch {
      // The next save resolves stale selections.
    }
  }));
}

function collectionSignature(collection: Collection) {
  return JSON.stringify({
    name: collection.name,
    input_text: collection.input_text,
    direction: collection.direction,
    line_capacity: collection.line_capacity,
    background: collection.background,
  });
}

function isHanCharacter(value: string) {
  if (Array.from(value).length !== 1) return false;
  const codepoint = value.codePointAt(0) || 0;
  return (
    (codepoint >= 0x3400 && codepoint <= 0x4dbf)
    || (codepoint >= 0x4e00 && codepoint <= 0x9fff)
    || (codepoint >= 0xf900 && codepoint <= 0xfaff)
    || (codepoint >= 0x20000 && codepoint <= 0x323af)
  );
}

function PracticeShelf({ setMessage }: { setMessage: (value: string) => void }) {
  const [posts, setPosts] = useState<GeneratedPost[]>([]);
  const [selected, setSelected] = useState<GeneratedPost | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [thumbs, setThumbs] = useState<Record<number, string>>({});
  const [files, setFiles] = useState<GeneratedPostFile[]>([]);
  const [syncingId, setSyncingId] = useState<number | null>(null);

  async function loadPosts() {
    const loaded = await api().list_generated_posts();
    setPosts(loaded);
    const queue = [...loaded];
    const workers = Array.from({ length: Math.min(6, queue.length) }, async () => {
      while (queue.length) {
        const post = queue.shift();
        if (!post) return;
        try {
          const thumbnail = await api().get_generated_post_thumbnail(post.id);
          setThumbs((current) => ({ ...current, [post.id]: thumbnail }));
        } catch (error) {
          setMessage(String(error));
        }
      }
    });
    void Promise.all(workers);
  }

  async function openPost(post: GeneratedPost) {
    setSelected(post);
    setPreviewing(true);
    setFiles(await api().list_generated_post_files(post.id));
  }

  async function syncPost(post: GeneratedPost) {
    setSyncingId(post.id);
    try {
      const updated = await api().sync_generated_post(post.id);
      setPosts((current) => current.map((item) => item.id === updated.id ? updated : item));
      setSelected((current) => current?.id === updated.id ? updated : current);
      const thumbnail = await api().get_generated_post_thumbnail(updated.id);
      setThumbs((current) => ({ ...current, [updated.id]: thumbnail }));
      if (selected?.id === updated.id) {
        setFiles(await api().list_generated_post_files(updated.id));
      }
      setMessage(`已同步：${updated.name}`);
    } catch (error) {
      setMessage(String(error));
      await loadPosts();
    } finally {
      setSyncingId(null);
    }
  }

  useEffect(() => {
    loadPosts().catch((error) => setMessage(String(error)));
  }, []);

  if (previewing && selected) {
    return (
      <section className="pagePreviewView">
        <div className="previewTopbar">
          <Button icon={<ArrowLeft24Regular />} appearance="subtle" onClick={() => setPreviewing(false)}>返回</Button>
          <div className="previewTitle">
            <Title2>{selected.name}</Title2>
            <Text className="mutedText">{selected.page_count} 页 · 结果 {selected.result_count} 份</Text>
          </div>
          <Button appearance="primary" icon={<ArrowSync24Regular />} disabled={syncingId === selected.id} onClick={() => syncPost(selected)}>
            同步
          </Button>
        </div>
        <Card className="contentCard">
          <div className="generatedFileList">
            {files.map((file) => (
              <div className="generatedFileRow" key={`${file.kind}-${file.path}`}>
                  {file.name.toLowerCase().endsWith(".png") ? <Image24Regular /> : <DocumentPdf24Regular />}
                <div>
                  <Text weight="semibold">{file.kind === "original" ? "原帖" : "练习结果"} · {file.name}</Text>
                  <Text size={200} className="mutedText" truncate>{file.path}</Text>
                </div>
                <Text size={200} className="mutedText">{formatFileSize(file.size)}</Text>
              </div>
            ))}
            {!files.length && <div className="centerState"><Text>还没有可显示的 PDF</Text></div>}
          </div>
        </Card>
      </section>
    );
  }

  return (
    <section className="libraryView">
      <div className="sectionHeader">
        <div>
          <Title1>练帖阁</Title1>
          <Text className="mutedText">保存生成帖，并通过 WebDAV 同步原帖和练习结果</Text>
        </div>
      </div>
      <div className="copybookShelf">
        {posts.map((post) => (
          <div
            key={post.id}
            className={selected?.id === post.id ? "coverTile selected" : "coverTile"}
            onClick={() => setSelected(post)}
            onDoubleClick={() => openPost(post)}
            onKeyDown={(event) => {
              if (event.key === "Enter") openPost(post);
            }}
            role="button"
            tabIndex={0}
          >
            <div className="coverFrame generatedCoverFrame">
              {thumbs[post.id] ? <img src={thumbs[post.id]} alt={post.name} /> : <Spinner size="small" />}
              <Tooltip content={syncingId === post.id ? "正在同步" : "同步"} relationship="label">
                <Button
                  appearance="primary"
                  icon={<FolderSync24Regular />}
                  className="generatedSyncButton"
                  disabled={syncingId === post.id}
                  onClick={(event) => {
                    event.stopPropagation();
                    syncPost(post).catch((error) => setMessage(String(error)));
                  }}
                />
              </Tooltip>
            </div>
            <Text weight="semibold" truncate>{post.name}</Text>
            <Text size={200} className="mutedText" truncate>{post.output_format.toUpperCase()} · {post.page_count} 页 · 结果 {post.result_count} 份 · {syncStatusText(post.sync_status)}</Text>
          </div>
        ))}
      </div>
    </section>
  );
}

function syncStatusText(status: string) {
  if (status === "synced") return "已同步";
  if (status === "syncing") return "同步中";
  if (status === "error") return "同步失败";
  return "本地";
}

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function Presets({ setMessage }: { setMessage: (value: string) => void }) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [form, setForm] = useState({ name: "", grid_style: "tian", cell_size_mm: 15, margin_mm: 15 });

  async function load() {
    setPresets(await api().list_presets());
  }

  async function create() {
    if (!form.name.trim()) {
      setMessage("预设需要名称");
      return;
    }
    await api().create_preset({ name: form.name, params: { grid_style: form.grid_style, cell_size_mm: form.cell_size_mm, margin_mm: form.margin_mm } });
    setForm({ ...form, name: "" });
    await load();
  }

  useEffect(() => {
    load().catch((error) => setMessage(String(error)));
  }, []);

  return (
    <section className="singleColumnView">
      <div className="sectionHeader">
        <div>
          <Title1>预设</Title1>
          <Text className="mutedText">管理田字格、米字格和页面尺寸</Text>
        </div>
        <Button appearance="primary" icon={<Save24Regular />} onClick={create}>保存预设</Button>
      </div>
      <Card className="contentCard">
        <div className="formGrid">
          <Field label="名称"><Input value={form.name} onChange={(_, data) => setForm({ ...form, name: data.value })} /></Field>
          <Field label="格子">
            <Select value={form.grid_style} onChange={(event) => setForm({ ...form, grid_style: event.target.value })}>
              <option value="tian">田字格</option>
              <option value="mi">米字格</option>
            </Select>
          </Field>
          <Field label="格宽（mm）"><Input type="number" min={10} max={30} step="0.5" value={String(form.cell_size_mm)} onChange={(_, data) => setForm({ ...form, cell_size_mm: Number(data.value) })} /></Field>
          <Field label="边距（mm）"><Input type="number" min={5} max={30} step="0.5" value={String(form.margin_mm)} onChange={(_, data) => setForm({ ...form, margin_mm: Number(data.value) })} /></Field>
        </div>
      </Card>
      <div className="presetGrid">
        {presets.map((preset) => (
          <Card key={preset.id} className="presetCard">
            <CardHeader header={<Text weight="semibold">{preset.name}</Text>} description={<Text size={200}>{preset.params?.grid_style === "mi" ? "米字格" : "田字格"}</Text>} />
            <Text size={200}>{String(preset.params?.cell_size_mm || 15)} mm · 边距 {String(preset.params?.margin_mm || 15)} mm</Text>
          </Card>
        ))}
      </div>
    </section>
  );
}

function Settings({ setMessage }: { setMessage: (value: string) => void }) {
  const [settings, setSettings] = useState<Record<string, string>>({});
  useEffect(() => {
    api().get_settings().then(setSettings).catch((error) => setMessage(String(error)));
  }, []);
  async function save() {
    setSettings(await api().update_settings(settings));
    setMessage("设置已保存");
  }
  return (
    <section className="singleColumnView">
      <div className="sectionHeader">
        <div>
          <Title1>设置</Title1>
          <Text className="mutedText">配置本地数据目录和 A4 导出行为</Text>
        </div>
        <Button appearance="primary" icon={<Save24Regular />} onClick={save}>保存</Button>
      </div>
      <Card className="contentCard">
        <div className="formGrid">
          <Field label="数据目录"><Input value={settings.data_dir || ""} onChange={(_, data) => setSettings({ ...settings, data_dir: data.value })} /></Field>
          <Field label="默认 DPI"><Input value={settings.default_dpi || "300"} onChange={(_, data) => setSettings({ ...settings, default_dpi: data.value })} /></Field>
          <Field label="默认导出目录"><Input value={settings.default_export_dir || ""} onChange={(_, data) => setSettings({ ...settings, default_export_dir: data.value })} /></Field>
          <Field label="WebDAV 地址"><Input value={settings.webdav_url || ""} onChange={(_, data) => setSettings({ ...settings, webdav_url: data.value })} /></Field>
          <Field label="WebDAV 用户名"><Input value={settings.webdav_username || ""} onChange={(_, data) => setSettings({ ...settings, webdav_username: data.value })} /></Field>
          <Field label="WebDAV 应用密码"><Input type="password" value={settings.webdav_password || ""} onChange={(_, data) => setSettings({ ...settings, webdav_password: data.value })} /></Field>
          <Field label="WebDAV 远端根目录"><Input value={settings.webdav_remote_root || "Linmo"} onChange={(_, data) => setSettings({ ...settings, webdav_remote_root: data.value })} /></Field>
        </div>
      </Card>
    </section>
  );
}
