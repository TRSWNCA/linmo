import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent, ReactElement, WheelEvent as ReactWheelEvent } from "react";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Checkbox,
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
import type { Api, Copybook, GeneratedPost, GeneratedPostFile, GlyphGroup, Page, PageAnalysis, Preset, QueueItem } from "./types";

type View = "home" | "library" | "make" | "practice" | "presets" | "settings";

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
    return { id: _id, title: metadata.title || "", author: metadata.author || "", style: "", source_type: "", cover_path: "", tags: "", notes: "" };
  },
  async list_pages() {
    return [];
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

function api(): Api {
  return window.pywebview?.api || fallbackApi;
}

export function App() {
  const [view, setView] = useState<View>("home");
  const [stats, setStats] = useState({ copybooks: 0, exported_pages: 0 });
  const [message, setMessage] = useState("");

  async function refreshStats() {
    setStats(await api().get_home_stats());
  }

  useEffect(() => {
    refreshStats().catch((error) => setMessage(String(error)));
  }, []);

  useEffect(() => {
    if (!message) return;
    const timeout = window.setTimeout(() => setMessage(""), 3600);
    return () => window.clearTimeout(timeout);
  }, [message]);

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
          <NavButton icon={<Settings24Regular />} active={view === "settings"} onClick={() => setView("settings")}>设置</NavButton>
        </aside>
        <main className="workspace">
          {view === "home" && <Home stats={stats} />}
          {view === "library" && <Library setMessage={setMessage} refreshStats={refreshStats} />}
          {view === "make" && <Maker setMessage={setMessage} refreshStats={refreshStats} openPractice={() => setView("practice")} />}
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

function Library({ setMessage, refreshStats }: { setMessage: (value: string) => void; refreshStats: () => Promise<void> }) {
  const [copybooks, setCopybooks] = useState<Copybook[]>([]);
  const [selected, setSelected] = useState<Copybook | null>(null);
  const [editing, setEditing] = useState<Copybook | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [pages, setPages] = useState<Page[]>([]);
  const [covers, setCovers] = useState<Record<number, string>>({});
  const [thumbs, setThumbs] = useState<Record<number, string>>({});
  const [selectedPages, setSelectedPages] = useState<number[]>([]);
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [loadingPages, setLoadingPages] = useState(false);
  const [importing, setImporting] = useState(false);
  const openRunId = useRef(0);
  const queueIndexByPageId = useMemo(() => {
    const indexByPageId: Record<number, number> = {};
    queueItems.forEach((item, index) => {
      if (indexByPageId[item.page_id] === undefined) {
        indexByPageId[item.page_id] = index + 1;
      }
    });
    return indexByPageId;
  }, [queueItems]);
  const selectedNewPageCount = selectedPages.filter((pageId) => queueIndexByPageId[pageId] === undefined).length;

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
    setPreviewing(true);
    setLoadingPages(true);
    setPages([]);
    setThumbs({});
    setSelectedPages([]);

    try {
      const loadedPages = await api().list_pages(copybook.id);
      if (openRunId.current !== runId) return;
      setPages(loadedPages);
      setLoadingPages(false);
      await refreshQueueItems();

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

  async function saveMetadata(copybook: Copybook, metadata: { title: string; author: string; cover_source_path?: string }) {
    const updated = await api().update_copybook_metadata(copybook.id, metadata);
    setCopybooks((current) => current.map((item) => item.id === updated.id ? updated : item));
    setSelected((current) => current?.id === updated.id ? updated : current);
    setEditing(null);
    const cover = await api().get_copybook_cover(updated.id);
    setCovers((current) => ({ ...current, [updated.id]: cover }));
    setMessage("元数据已保存");
  }

  async function addToQueue() {
    const pageIds = selectedPages.filter((pageId) => queueIndexByPageId[pageId] === undefined);
    if (!pageIds.length) {
      setSelectedPages([]);
      setMessage("选中的页面已在制作队列中");
      return;
    }

    const previousPageIds = new Set(queueItems.map((item) => item.page_id));
    await api().add_pages_to_queue(pageIds);
    const updatedItems = await refreshQueueItems();
    const addedCount = updatedItems.filter((item) => pageIds.includes(item.page_id) && !previousPageIds.has(item.page_id)).length;
    setSelectedPages((current) => current.filter((pageId) => queueIndexByPageId[pageId] === undefined && !pageIds.includes(pageId)));
    setMessage(addedCount ? `已加入 ${addedCount} 页到制作队列` : "选中的页面已在制作队列中");
  }

  function togglePage(pageId: number) {
    if (queueIndexByPageId[pageId] !== undefined) return;
    setSelectedPages((current) => current.includes(pageId) ? current.filter((id) => id !== pageId) : [...current, pageId]);
  }

  async function refreshQueueItems() {
    const loadedItems = await api().list_queue_items();
    const queuedPageIds = new Set(loadedItems.map((item) => item.page_id));
    setQueueItems(loadedItems);
    setSelectedPages((current) => current.filter((pageId) => !queuedPageIds.has(pageId)));
    return loadedItems;
  }

  useEffect(() => {
    loadCopybooks().catch((error) => setMessage(String(error)));
  }, []);

  if (previewing && selected) {
    return (
      <section className="pagePreviewView">
        <div className="previewTopbar">
          <Button icon={<ArrowLeft24Regular />} appearance="subtle" onClick={() => setPreviewing(false)}>返回</Button>
          <div className="previewTitle">
            <Title2>{selected.title}</Title2>
            <Text className="mutedText">{selected.author || "未填写作者"} · {pages.length || selected.page_count || 0} 页</Text>
          </div>
          <Button appearance="primary" icon={<Add24Regular />} disabled={!selectedNewPageCount} onClick={addToQueue}>
            加入制作队列
          </Button>
        </div>
        {loadingPages ? (
          <div className="centerState"><Spinner label="正在读取页面" /></div>
        ) : (
          <div className="pageGrid">
            {pages.map((page) => {
              const queueIndex = queueIndexByPageId[page.id];
              const isQueued = queueIndex !== undefined;
              const isSelected = selectedPages.includes(page.id);
              return (
                <button
                  key={page.id}
                  className={pageThumbClass(isSelected, isQueued)}
                  onClick={() => togglePage(page.id)}
                  type="button"
                  aria-pressed={isSelected || isQueued}
                >
                  <div className="thumbCanvas">
                    {thumbs[page.id] ? <img src={thumbs[page.id]} alt={`第 ${page.page_no} 页`} /> : <Spinner size="small" />}
                    {isQueued && <span className="pageQueueBadge">{queueIndex}</span>}
                    {!isQueued && isSelected && <span className="pageSelectBadge">待加</span>}
                  </div>
                  <Text size={200}>第 {page.page_no} 页</Text>
                </button>
              );
            })}
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
          <Text className="mutedText">双击封面进入预览，右键封面编辑元数据</Text>
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
  onSave: (metadata: { title: string; author: string; cover_source_path?: string }) => Promise<void>;
}) {
  const [form, setForm] = useState({ title: copybook.title, author: copybook.author, cover_source_path: "" });
  const [saving, setSaving] = useState(false);
  useEffect(() => setForm({ title: copybook.title, author: copybook.author, cover_source_path: "" }), [copybook.id]);

  async function chooseCover() {
    const path = await api().choose_cover_image();
    if (path) setForm((current) => ({ ...current, cover_source_path: path }));
  }

  async function save() {
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  }

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
                <Field label="展示封面" hint={form.cover_source_path || "默认使用第一页缩略图"}>
                  <Button icon={<Image24Regular />} onClick={chooseCover}>选择封面</Button>
                </Field>
              </div>
            </div>
          </DialogContent>
          <DialogActions>
            <Button appearance="secondary" onClick={onCancel}>取消</Button>
            <Button appearance="primary" icon={<Save24Regular />} disabled={saving || !form.title.trim()} onClick={save}>
              保存
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}

function Maker({
  setMessage,
  refreshStats,
  openPractice,
}: {
  setMessage: (value: string) => void;
  refreshStats: () => Promise<void>;
  openPractice: () => void;
}) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [previewPages, setPreviewPages] = useState<string[]>([]);
  const [previewPage, setPreviewPage] = useState(0);
  const [sourcePreview, setSourcePreview] = useState("");
  const [queueThumbs, setQueueThumbs] = useState<Record<number, string>>({});
  const [comparePreview, setComparePreview] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportName, setExportName] = useState("");
  const [exportFormat, setExportFormat] = useState<"pdf" | "png">("pdf");
  const [exporting, setExporting] = useState(false);
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<PageAnalysis | null>(null);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const previewRunId = useRef(0);
  const active = useMemo(() => items.find((item) => item.id === activeId) || null, [items, activeId]);
  const activeParamsKey = active ? JSON.stringify(active.params) : "";

  async function load() {
    const loaded = await api().list_queue_items();
    setItems(loaded);
    if (!activeId && loaded.length) setActiveId(loaded[0].id);
  }

  async function updateActive(params: Record<string, unknown>) {
    if (!active) return;
    const updated = await api().update_queue_item(active.id, params);
    setItems((current) => current.map((item) => item.id === updated.id ? updated : item));
  }

  async function renderPreview(runId: number) {
    if (!active) return;
    setPreviewing(true);
    try {
      const rendered = await api().render_queue_previews(active.id);
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

  async function openAnalysis(force = false) {
    if (!active) return;
    setAnalyzing(true);
    try {
      const result = await api().analyze_queue_item(active.id, force);
      setAnalysis(result);
      setAnalysisOpen(true);
      if (result.warning) setMessage(result.warning);
    } catch (error) {
      setMessage(String(error));
    } finally {
      setAnalyzing(false);
    }
  }

  async function saveAnalysis(groups: GlyphGroup[]) {
    if (!active) return;
    const saved = await api().update_queue_analysis(active.id, groups);
    setAnalysis(saved);
    setAnalysisOpen(false);
    const runId = ++previewRunId.current;
    await renderPreview(runId);
  }

  async function openExportDialog() {
    const defaultName = await api().get_next_generated_post_name();
    setExportName(defaultName);
    setExportFormat("pdf");
    setExportDialogOpen(true);
  }

  async function exportPdf() {
    const name = exportName.trim();
    if (!name) {
      setMessage("名称不能为空");
      return;
    }
    setExporting(true);
    try {
      const result = await api().export_queue_to_pdf(items.map((item) => item.id), null, null, name, exportFormat);
      await refreshStats();
      setExportDialogOpen(false);
      setMessage(`已保存 ${result.page_count} 页 ${exportFormat.toUpperCase()} 到练帖阁：${name}`);
      openPractice();
    } catch (error) {
      setMessage(String(error));
    } finally {
      setExporting(false);
    }
  }

  function moveQueueItem(targetId: number) {
    if (draggingId === null || draggingId === targetId) return;
    setItems((current) => {
      const from = current.findIndex((item) => item.id === draggingId);
      const to = current.findIndex((item) => item.id === targetId);
      if (from < 0 || to < 0) return current;
      const next = [...current];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  }

  function handleQueuePointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (draggingId === null) return;
    event.preventDefault();
    const element = document.elementFromPoint(event.clientX, event.clientY);
    const target = element?.closest("[data-queue-id]") as HTMLElement | null;
    const targetId = Number(target?.dataset.queueId || "");
    if (Number.isFinite(targetId)) moveQueueItem(targetId);
  }

  useEffect(() => {
    load().catch((error) => setMessage(String(error)));
  }, []);

  useEffect(() => {
    if (!items.length) return;
    const missing = items.filter((item) => !queueThumbs[item.page_id]);
    const queue = [...missing];
    const workers = Array.from({ length: Math.min(4, queue.length) }, async () => {
      while (queue.length) {
        const item = queue.shift();
        if (!item) return;
        try {
          const thumbnail = await api().get_page_thumbnail(item.page_id);
          setQueueThumbs((current) => ({ ...current, [item.page_id]: thumbnail }));
        } catch (error) {
          setMessage(String(error));
        }
      }
    });
    void Promise.all(workers);
  }, [items]);

  useEffect(() => {
    if (!active) {
      setPreviewPages([]);
      setSourcePreview("");
      return;
    }

    const runId = ++previewRunId.current;
    setPreviewPages([]);
    setSourcePreview("");
    renderPreview(runId).catch((error) => setMessage(String(error)));
    if (comparePreview) {
      api().get_page_preview(active.page_id).then((image) => {
        if (previewRunId.current === runId) {
          setSourcePreview(image);
        }
      }).catch((error) => setMessage(String(error)));
    }
  }, [active?.id, activeParamsKey, comparePreview]);

  return (
    <section className="makeWorkbench">
      <div className="makeTopbar">
        {active ? <ParamToolbar item={active} update={updateActive} /> : <div className="paramToolbarPlaceholder" />}
        <Button icon={<LineHorizontal1Regular />} disabled={!active || analyzing} onClick={() => openAnalysis(false)}>
          {analyzing ? "识别中" : "识别校对"}
        </Button>
        <Checkbox checked={comparePreview} onChange={(_, data) => setComparePreview(Boolean(data.checked))} label="对照预览" />
        <Button appearance="primary" icon={<DocumentPdf24Regular />} disabled={!items.length} onClick={openExportDialog}>导出</Button>
      </div>

      <div className={comparePreview ? "makeStage compare" : "makeStage single"}>
        {!active ? (
          <div className="centerState">
            <Box24Regular />
            <Text>从藏帖阁选择页面加入制作队列</Text>
          </div>
        ) : comparePreview ? (
          <>
            <PreviewPane title="原图" image={sourcePreview} loading={!sourcePreview} />
            <PreviewPane title={`预览 ${previewPages.length > 1 ? `${previewPage + 1}/${previewPages.length}` : ""}`} image={previewPages[previewPage] || ""} loading={previewing || !previewPages.length} />
          </>
        ) : (
          <PreviewPane title={`预览 ${previewPages.length > 1 ? `${previewPage + 1}/${previewPages.length}` : ""}`} image={previewPages[previewPage] || ""} loading={previewing || !previewPages.length} large />
        )}
        {previewPages.length > 1 && (
          <div className="previewPager">
            <Button size="small" disabled={previewPage === 0} onClick={() => setPreviewPage((value) => value - 1)}>上一页</Button>
            <Text>{previewPage + 1} / {previewPages.length}</Text>
            <Button size="small" disabled={previewPage === previewPages.length - 1} onClick={() => setPreviewPage((value) => value + 1)}>下一页</Button>
          </div>
        )}
      </div>

      <div
        className={draggingId === null ? "queueStrip" : "queueStrip sorting"}
        aria-label="制作队列缩略图"
        onPointerMove={handleQueuePointerMove}
        onPointerUp={() => setDraggingId(null)}
        onPointerCancel={() => setDraggingId(null)}
      >
        {items.map((item) => (
          <button
            key={item.id}
            className={["queueThumb", item.id === activeId ? "active" : "", item.id === draggingId ? "sorting" : ""].filter(Boolean).join(" ")}
            data-queue-id={item.id}
            onPointerDown={(event) => {
              if (event.button !== 0) return;
              event.preventDefault();
              event.currentTarget.setPointerCapture(event.pointerId);
              setActiveId(item.id);
              setDraggingId(item.id);
            }}
            type="button"
          >
            <div className="queueThumbImage">
              {queueThumbs[item.page_id] ? <img src={queueThumbs[item.page_id]} alt={`${item.copybook_title} 第 ${item.page_no} 页`} draggable={false} /> : <Spinner size="tiny" />}
            </div>
            <Text size={100} truncate>{item.copybook_title}</Text>
            <Text size={100} className="mutedText">第 {item.page_no} 页</Text>
          </button>
        ))}
      </div>
      <ExportPostDialog
        open={exportDialogOpen}
        name={exportName}
        saving={exporting}
        outputFormat={exportFormat}
        onNameChange={setExportName}
        onFormatChange={setExportFormat}
        onCancel={() => setExportDialogOpen(false)}
        onSave={exportPdf}
      />
      {analysisOpen && analysis && (
        <AnalysisEditor
          analysis={analysis}
          source={sourcePreview}
          saving={previewing}
          onCancel={() => setAnalysisOpen(false)}
          onRecognizeAgain={() => openAnalysis(true)}
          onSave={saveAnalysis}
        />
      )}
      {analyzing && (
        <Dialog open>
          <DialogSurface>
            <DialogBody>
              <DialogTitle>正在识别书帖</DialogTitle>
              <DialogContent>
                <Spinner label="首次使用会下载本地 OCR 模型，完成后可离线运行" />
              </DialogContent>
            </DialogBody>
          </DialogSurface>
        </Dialog>
      )}
    </section>
  );
}

function ExportPostDialog({
  open,
  name,
  saving,
  outputFormat,
  onNameChange,
  onFormatChange,
  onCancel,
  onSave,
}: {
  open: boolean;
  name: string;
  saving: boolean;
  outputFormat: "pdf" | "png";
  onNameChange: (value: string) => void;
  onFormatChange: (value: "pdf" | "png") => void;
  onCancel: () => void;
  onSave: () => Promise<void>;
}) {
  if (!open) return null;
  return (
    <Dialog open>
      <DialogSurface>
        <DialogBody>
          <DialogTitle>保存生成帖</DialogTitle>
          <DialogContent>
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
          </DialogContent>
          <DialogActions>
            <Button appearance="secondary" disabled={saving} onClick={onCancel}>取消</Button>
            <Button appearance="primary" icon={<Save24Regular />} disabled={saving || !name.trim()} onClick={onSave}>
              保存
            </Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
  );
}

function AnalysisEditor({
  analysis,
  source,
  saving,
  onCancel,
  onRecognizeAgain,
  onSave,
}: {
  analysis: PageAnalysis;
  source: string;
  saving: boolean;
  onCancel: () => void;
  onRecognizeAgain: () => Promise<void>;
  onSave: (groups: GlyphGroup[]) => Promise<void>;
}) {
  const [groups, setGroups] = useState<GlyphGroup[]>(() => JSON.parse(JSON.stringify(analysis.groups)));
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const glyphDrag = useRef<{
    groupId: string;
    glyphId: string;
    startX: number;
    startY: number;
    bbox: [number, number, number, number];
    resize: boolean;
  } | null>(null);
  const imageWidth = Math.max(1, analysis.image_size?.[0] || 1);
  const imageHeight = Math.max(1, analysis.image_size?.[1] || 1);

  useEffect(() => {
    setGroups(JSON.parse(JSON.stringify(analysis.groups)));
    setSelectedId(null);
  }, [analysis]);

  function updateGroup(groupId: string, change: Partial<GlyphGroup>) {
    setGroups((current) => current.map((group) => group.id === groupId ? { ...group, ...change } : group));
  }

  function updateGlyph(groupId: string, glyphId: string, change: Record<string, unknown>) {
    setGroups((current) => current.map((group) => group.id === groupId ? {
      ...group,
      glyphs: group.glyphs.map((glyph) => glyph.id === glyphId ? { ...glyph, ...change } : glyph),
    } : group));
  }

  function removeGlyph(groupId: string, glyphId: string) {
    setGroups((current) => current.map((group) => group.id === groupId ? {
      ...group,
      glyphs: group.glyphs.filter((glyph) => glyph.id !== glyphId),
    } : group));
  }

  function addGlyph(groupId: string) {
    const size = Math.round(Math.min(imageWidth, imageHeight) * 0.08);
    const left = Math.round((imageWidth - size) / 2);
    const top = Math.round((imageHeight - size) / 2);
    setGroups((current) => current.map((group) => group.id === groupId ? {
      ...group,
      glyphs: [...group.glyphs, {
        id: `manual-${Date.now()}`,
        text: "字",
        confidence: 1,
        bbox: [left, top, left + size, top + size],
        included: true,
        kind: "character",
      }],
    } : group));
  }

  return (
    <Dialog open>
      <DialogSurface className="analysisDialogSurface">
        <DialogBody>
          <DialogTitle>识别与校对</DialogTitle>
          <DialogContent className="analysisDialogContent">
            <div className="analysisCanvas">
              {source ? <img src={source} alt="待校对原图" /> : <Spinner />}
              <div className="analysisOverlay">
                {groups.flatMap((group) => group.glyphs.map((glyph) => {
                  const [left, top, right, bottom] = glyph.bbox;
                  return (
                    <button
                      key={glyph.id}
                      type="button"
                      title={`${glyph.text} · ${Math.round(glyph.confidence * 100)}%`}
                      className={[
                        "glyphBox",
                        glyph.confidence < 0.75 ? "lowConfidence" : "",
                        !glyph.included || !group.included ? "excluded" : "",
                        selectedId === glyph.id ? "selected" : "",
                      ].filter(Boolean).join(" ")}
                      style={{
                        left: `${left / imageWidth * 100}%`,
                        top: `${top / imageHeight * 100}%`,
                        width: `${Math.max(0.3, (right - left) / imageWidth * 100)}%`,
                        height: `${Math.max(0.3, (bottom - top) / imageHeight * 100)}%`,
                      }}
                      onClick={() => setSelectedId(glyph.id)}
                      onPointerDown={(event) => {
                        event.currentTarget.setPointerCapture(event.pointerId);
                        glyphDrag.current = {
                          groupId: group.id,
                          glyphId: glyph.id,
                          startX: event.clientX,
                          startY: event.clientY,
                          bbox: [...glyph.bbox],
                          resize: event.altKey,
                        };
                      }}
                      onPointerMove={(event) => {
                        const drag = glyphDrag.current;
                        const overlay = event.currentTarget.parentElement;
                        if (!drag || drag.glyphId !== glyph.id || !overlay) return;
                        const dx = Math.round((event.clientX - drag.startX) / overlay.clientWidth * imageWidth);
                        const dy = Math.round((event.clientY - drag.startY) / overlay.clientHeight * imageHeight);
                        const [startLeft, startTop, startRight, startBottom] = drag.bbox;
                        const bbox = drag.resize
                          ? [startLeft, startTop, Math.max(startLeft + 1, startRight + dx), Math.max(startTop + 1, startBottom + dy)]
                          : [startLeft + dx, startTop + dy, startRight + dx, startBottom + dy];
                        updateGlyph(drag.groupId, drag.glyphId, { bbox });
                      }}
                      onPointerUp={() => { glyphDrag.current = null; }}
                      onPointerCancel={() => { glyphDrag.current = null; }}
                    >
                      {glyph.text}
                    </button>
                  );
                }))}
              </div>
            </div>
            <div className="analysisList">
              <Text size={200} className="mutedText">
                {analysis.model_id} · {analysis.engine === "fallback" ? "降级定位" : "本地 OCR"} · 拖动框可移动，按住 Alt 拖动可缩放
              </Text>
              {groups.map((group, groupIndex) => (
                <Card key={group.id} className="analysisGroup">
                  <div className="analysisGroupHeader">
                    <Checkbox
                      checked={group.included}
                      label={`正文行 ${groupIndex + 1}`}
                      onChange={(_, data) => updateGroup(group.id, { included: Boolean(data.checked) })}
                    />
                    <Select value={group.direction} onChange={(event) => updateGroup(group.id, { direction: event.target.value === "vertical" ? "vertical" : "horizontal" })}>
                      <option value="horizontal">横排</option>
                      <option value="vertical">竖排</option>
                    </Select>
                    <Button size="small" icon={<Add24Regular />} onClick={() => addGlyph(group.id)}>补字</Button>
                  </div>
                  <div className="glyphEditorGrid">
                    {group.glyphs.map((glyph) => (
                      <div key={glyph.id} className={selectedId === glyph.id ? "glyphEditor selected" : "glyphEditor"}>
                        <Checkbox checked={glyph.included} onChange={(_, data) => updateGlyph(group.id, glyph.id, { included: Boolean(data.checked) })} />
                        <Input
                          size="small"
                          value={glyph.text}
                          onFocus={() => setSelectedId(glyph.id)}
                          onChange={(_, data) => updateGlyph(group.id, glyph.id, {
                            text: data.value,
                            kind: /^[\p{P}]+$/u.test(data.value) ? "punctuation" : "character",
                          })}
                        />
                        <Input
                          size="small"
                          aria-label="字符框坐标"
                          value={glyph.bbox.join(",")}
                          onFocus={() => setSelectedId(glyph.id)}
                          onChange={(_, data) => {
                            const values = data.value.split(",").map(Number);
                            if (values.length === 4 && values.every(Number.isFinite)) {
                              updateGlyph(group.id, glyph.id, { bbox: values.map(Math.round) });
                            }
                          }}
                        />
                        <Text size={100}>{Math.round(glyph.confidence * 100)}%</Text>
                        <Button appearance="subtle" size="small" icon={<Dismiss24Regular />} aria-label="删除字符" onClick={() => removeGlyph(group.id, glyph.id)} />
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          </DialogContent>
          <DialogActions>
            <Button disabled={saving} onClick={onCancel}>取消</Button>
            <Button disabled={saving} onClick={onRecognizeAgain}>重新识别</Button>
            <Button appearance="primary" disabled={saving} icon={<Save24Regular />} onClick={() => onSave(groups)}>保存校对</Button>
          </DialogActions>
        </DialogBody>
      </DialogSurface>
    </Dialog>
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

function ParamToolbar({ item, update }: { item: QueueItem; update: (params: Record<string, unknown>) => Promise<void> }) {
  const params = item.params;
  return (
    <div className="paramToolbar">
      <Field label="格子" size="small">
        <Select size="small" value={String(params.grid_style || "tian")} onChange={(event) => update({ grid_style: event.target.value })}>
          <option value="tian">田字格</option>
          <option value="mi">米字格</option>
        </Select>
      </Field>
      <Field label="格宽 mm" size="small"><Input size="small" type="number" min={10} max={30} step="0.5" value={String(Number(params.cell_size_mm || 15))} onChange={(_, data) => update({ cell_size_mm: Number(data.value) })} /></Field>
      <Field label="边距 mm" size="small"><Input size="small" type="number" min={5} max={30} step="0.5" value={String(Number(params.margin_mm || 15))} onChange={(_, data) => update({ margin_mm: Number(data.value) })} /></Field>
    </div>
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
