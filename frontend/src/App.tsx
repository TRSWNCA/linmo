import { useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent, ReactElement, WheelEvent as ReactWheelEvent } from "react";
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
  FolderSync24Regular,
  Home24Regular,
  Image24Regular,
  LineHorizontal1Regular,
  Maximize16Regular,
  Save24Regular,
  Settings24Regular,
} from "@fluentui/react-icons";
import packageJson from "../package.json";
import type {
  Api,
  Copybook,
  GeneratedPost,
  GeneratedPostFile,
  Glyph,
  GlyphGroup,
  Page,
  PageAnalysis,
  PageDetail,
  Preset,
  RuntimeDiagnostics,
  RuntimeLogEntry,
} from "./types";

type View = "home" | "library" | "make" | "practice" | "presets" | "settings";
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
  void api().append_runtime_log(level, source, message, details).catch(() => undefined);
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
  const [importing, setImporting] = useState(false);
  const [cropDraft, setCropDraft] = useState<{ leftPercent: number; rightPercent: number; topPercent: number; bottomPercent: number } | null>(null);
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
        api().get_page_preview(page.id),
      ]);
      setPageDetail(detail);
      setCropDraft({
        leftPercent: ratioToPercent(detail.crop_left_ratio),
        rightPercent: ratioToPercent(detail.crop_right_ratio),
        topPercent: ratioToPercent(detail.crop_top_ratio),
        bottomPercent: ratioToPercent(detail.crop_bottom_ratio),
      });
      lastSavedCropKey.current = `${ratioToPercent(detail.crop_left_ratio)}:${ratioToPercent(detail.crop_right_ratio)}:${ratioToPercent(detail.crop_top_ratio)}:${ratioToPercent(detail.crop_bottom_ratio)}`;
      setPagePreviewImage(preview);
    } catch (error) {
      setMessage(String(error));
    } finally {
      setLoadingPagePreview(false);
    }
  }

  async function refreshPageMedia(pageId: number) {
    const [preview, thumbnail] = await Promise.all([
      api().get_page_preview(pageId),
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
    const cropKey = `${cropDraft.leftPercent}:${cropDraft.rightPercent}:${cropDraft.topPercent}:${cropDraft.bottomPercent}`;
    if (cropKey === lastSavedCropKey.current) return;
    if (cropDraft.leftPercent + cropDraft.rightPercent >= 80) return;
    if (cropDraft.topPercent + cropDraft.bottomPercent >= 80) return;
    const runId = ++cropSaveRunId.current;
    const timeout = window.setTimeout(() => {
      api().update_page_crop(pageDetail.id, {
        crop_left_ratio: percentToCropRatio(cropDraft.leftPercent),
        crop_right_ratio: percentToCropRatio(cropDraft.rightPercent),
        crop_top_ratio: percentToCropRatio(cropDraft.topPercent),
        crop_bottom_ratio: percentToCropRatio(cropDraft.bottomPercent),
      }).then(async (updated) => {
        if (cropSaveRunId.current !== runId) return;
        setPageDetail(updated);
        lastSavedCropKey.current = cropKey;
        await refreshPageMedia(updated.id);
      }).catch((error) => setMessage(String(error)));
    }, 180);
    return () => window.clearTimeout(timeout);
  }, [cropDraft?.leftPercent, cropDraft?.rightPercent, cropDraft?.topPercent, cropDraft?.bottomPercent, pageDetail?.id]);

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
    return (
      <section className="pagePreviewView">
        <div className="previewTopbar">
          <Button icon={<ArrowLeft24Regular />} appearance="subtle" onClick={() => setPagePreviewOpen(false)}>返回</Button>
          <div className="previewTitle">
            <Title2>{selected.title}</Title2>
            <Text className="mutedText">第 {pageDetail.page_no} 页 · 预览页级裁切后进入制帖</Text>
          </div>
          <Button
            appearance="primary"
            icon={<DocumentPdf24Regular />}
            disabled={cropTotalTooLarge}
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
              <PreviewPane title="裁切预览" image={pagePreviewImage} loading={loadingPagePreview || !pagePreviewImage} large />
            </div>
            <div className="formStack singlePagePreviewSidebar">
              <Text size={200} className="mutedText">保存到当前页，下次进入该页会直接复用这组裁切。</Text>
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
  onDirtyChange,
}: {
  analysis: PageAnalysis;
  source: string;
  saving: boolean;
  recognizing: boolean;
  onRecognizeAgain: () => Promise<unknown>;
  onSave: (groups: GlyphGroup[]) => Promise<boolean>;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const sourceGroups = cloneGlyphGroups(
    analysis.selection_mode === "ordered_stream" && analysis.ocr_groups?.length
      ? analysis.ocr_groups
      : analysis.groups,
  );
  const [selectedGlyphs, setSelectedGlyphs] = useState<Glyph[]>(() => selectedStreamFromAnalysis(analysis));
  const [focusedGlyphId, setFocusedGlyphId] = useState<string | null>(null);
  const [selectionRect, setSelectionRect] = useState<null | { x1: number; y1: number; x2: number; y2: number }>(null);
  const [savedSignature, setSavedSignature] = useState(() => glyphSignature(selectedStreamFromAnalysis(analysis)));
  const [saveFailed, setSaveFailed] = useState(false);
  const [retryVersion, setRetryVersion] = useState(0);
  const autoSaveRunId = useRef(0);
  const onSaveRef = useRef(onSave);
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
    setSelectedGlyphs(selectedStreamFromAnalysis(analysis));
    setSavedSignature(initialSignature);
    setSaveFailed(false);
    setFocusedGlyphId(null);
    setSelectionRect(null);
  }, [analysis]);

  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

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

  function removeGlyph(glyphId: string) {
    if (!selectedIds.has(glyphId)) return;
    onDirtyChange(true);
    setSelectedGlyphs((current) => current.filter((glyph) => glyph.id !== glyphId));
    setFocusedGlyphId((current) => current === glyphId ? null : current);
  }

  function updateGlyph(glyphId: string, change: Partial<Glyph>) {
    onDirtyChange(true);
    setSelectedGlyphs((current) => current.map((glyph) => glyph.id === glyphId ? { ...glyph, ...change } : glyph));
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
                >
                  {!isSelected ? (
                    <button
                      type="button"
                      className="glyphBoxButton"
                      onPointerDown={(event) => event.stopPropagation()}
                      onClick={(event) => {
                        event.stopPropagation();
                        appendGlyph(glyph);
                      }}
                    >
                      <span>{glyph.text}</span>
                    </button>
                  ) : (
                    <div className="glyphBoxEditor" onPointerDown={(event) => event.stopPropagation()}>
                      <Input
                        size="small"
                        appearance="filled-lighter"
                        value={selectedGlyph.text}
                        onFocus={() => setFocusedGlyphId(glyph.id)}
                        onChange={(_, data) => updateGlyph(glyph.id, {
                          text: data.value,
                          kind: /^[\p{P}]+$/u.test(data.value) ? "punctuation" : "character",
                        })}
                      />
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
            已选 {selectedGlyphs.length} 字。选中后的字会直接在页面框内显示输入框，可原位改字；右上角可删除。
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
