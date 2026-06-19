import { useEffect, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, ReactElement, WheelEvent as ReactWheelEvent } from "react";
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
  Option,
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
  BookOpen24Regular,
  Box24Regular,
  Color24Regular,
  Dismiss24Regular,
  DocumentPdf24Regular,
  Home24Regular,
  Image24Regular,
  LineHorizontal1Regular,
  Maximize16Regular,
  Save24Regular,
  Settings24Regular,
} from "@fluentui/react-icons";
import packageJson from "../package.json";
import type { Api, Copybook, Page, Preset, QueueItem } from "./types";

type View = "home" | "library" | "make" | "presets" | "settings";

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
  async export_queue_to_pdf(queue_item_ids) {
    return { output_path: "", page_count: queue_item_ids.length };
  },
  async list_presets() {
    return [];
  },
  async create_preset(data) {
    return { id: Date.now(), name: data.name, background_image: "", ink_color: "#000000", foreground_threshold: 18, mode: "row", column_detection: "gray", params: {} };
  },
  async update_preset(preset_id, data) {
    return { id: preset_id, name: data.name || "", background_image: data.background_image || "", ink_color: data.ink_color || "#000000", foreground_threshold: data.foreground_threshold || 18, mode: data.mode || "row", column_detection: data.column_detection || "gray", params: data.params || {} };
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
  async window_minimize() {},
  async window_toggle_maximize() {},
  async window_close() {},
};

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
          <NavButton icon={<BookOpen24Regular />} active={view === "library"} onClick={() => setView("library")}>藏帖阁</NavButton>
          <NavButton icon={<DocumentPdf24Regular />} active={view === "make"} onClick={() => setView("make")}>生成帖</NavButton>
          <NavButton icon={<Color24Regular />} active={view === "presets"} onClick={() => setView("presets")}>预设</NavButton>
          <div className="navSpacer" />
          <NavButton icon={<Settings24Regular />} active={view === "settings"} onClick={() => setView("settings")}>设置</NavButton>
        </aside>
        <main className="workspace">
          {view === "home" && <Home stats={stats} />}
          {view === "library" && <Library setMessage={setMessage} refreshStats={refreshStats} />}
          {view === "make" && <Maker setMessage={setMessage} refreshStats={refreshStats} />}
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
  return (
    <header className="titleBar" onDoubleClick={() => api().window_toggle_maximize()}>
      <div className="titleBarDrag">
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

function Maker({ setMessage, refreshStats }: { setMessage: (value: string) => void; refreshStats: () => Promise<void> }) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [preview, setPreview] = useState("");
  const [sourcePreview, setSourcePreview] = useState("");
  const [queueThumbs, setQueueThumbs] = useState<Record<number, string>>({});
  const [comparePreview, setComparePreview] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [draggingId, setDraggingId] = useState<number | null>(null);
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
      const rendered = await api().render_queue_preview(active.id);
      if (previewRunId.current === runId) {
        setPreview(rendered);
      }
    } finally {
      if (previewRunId.current === runId) {
        setPreviewing(false);
      }
    }
  }

  async function exportPdf() {
    const result = await api().export_queue_to_pdf(items.map((item) => item.id), null, null);
    await refreshStats();
    setMessage(`已导出 ${result.page_count} 页：${result.output_path}`);
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
      setPreview("");
      setSourcePreview("");
      return;
    }

    const runId = ++previewRunId.current;
    setPreview("");
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
        <Checkbox checked={comparePreview} onChange={(_, data) => setComparePreview(Boolean(data.checked))} label="对照预览" />
        <Button appearance="primary" icon={<DocumentPdf24Regular />} disabled={!items.length} onClick={exportPdf}>导出 PDF</Button>
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
            <PreviewPane title="预览" image={preview} loading={previewing || !preview} />
          </>
        ) : (
          <PreviewPane title="预览" image={preview} loading={previewing || !preview} large />
        )}
      </div>

      <div className="queueStrip" aria-label="制作队列缩略图">
        {items.map((item) => (
          <button
            key={item.id}
            className={item.id === activeId ? "queueThumb active" : "queueThumb"}
            draggable
            onClick={() => setActiveId(item.id)}
            onDragStart={() => setDraggingId(item.id)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => moveQueueItem(item.id)}
            onDragEnd={() => setDraggingId(null)}
            type="button"
          >
            <div className="queueThumbImage">
              {queueThumbs[item.page_id] ? <img src={queueThumbs[item.page_id]} alt={`${item.copybook_title} 第 ${item.page_no} 页`} /> : <Spinner size="tiny" />}
            </div>
            <Text size={100} truncate>{item.copybook_title}</Text>
            <Text size={100} className="mutedText">第 {item.page_no} 页</Text>
          </button>
        ))}
      </div>
    </section>
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
  const inkColor = /^#[0-9a-fA-F]{6}$/.test(String(params.ink_color || "")) ? String(params.ink_color) : "#000000";
  return (
    <div className="paramToolbar">
      <Field label="模式" size="small">
        <Select size="small" value={String(params.mode || "row")} onChange={(event) => update({ mode: event.target.value })}>
          <Option value="row">横向行</Option>
          <Option value="col">竖向列</Option>
        </Select>
      </Field>
      <Field label="检测" size="small">
        <Select size="small" value={String(params.column_detection || "gray")} onChange={(event) => update({ column_detection: event.target.value })}>
          <Option value="gray">灰底</Option>
          <Option value="ink">墨迹</Option>
        </Select>
      </Field>
      <Field label="空白" size="small"><Input size="small" type="number" step="0.1" value={String(Number(params.blank_ratio || 1))} onChange={(_, data) => update({ blank_ratio: Number(data.value) })} /></Field>
      <Field label="字色" size="small"><input className="colorPicker" type="color" value={inkColor} onChange={(event) => update({ ink_color: event.target.value })} /></Field>
      <Field label="阈值" size="small"><Input size="small" type="number" value={String(Number(params.foreground_threshold || 18))} onChange={(_, data) => update({ foreground_threshold: Number(data.value) })} /></Field>
      <Field label="列" size="small"><Input size="small" type="number" placeholder="自动" value={params.columns ? String(params.columns) : ""} onChange={(_, data) => update({ columns: data.value ? Number(data.value) : "" })} /></Field>
      <Field label="行" size="small"><Input size="small" type="number" placeholder="自动" value={params.rows ? String(params.rows) : ""} onChange={(_, data) => update({ rows: data.value ? Number(data.value) : "" })} /></Field>
      <Field label="背景" size="small"><Input size="small" value={String(params.background_image || "")} onChange={(_, data) => update({ background_image: data.value })} /></Field>
    </div>
  );
}

function Presets({ setMessage }: { setMessage: (value: string) => void }) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [form, setForm] = useState({ name: "", background_image: "", ink_color: "#000000", foreground_threshold: 18, mode: "row", column_detection: "gray" });

  async function load() {
    setPresets(await api().list_presets());
  }

  async function chooseBackground() {
    const path = await api().choose_background_image();
    if (path) setForm({ ...form, background_image: path });
  }

  async function create() {
    if (!form.name.trim()) {
      setMessage("预设需要名称");
      return;
    }
    await api().create_preset(form);
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
          <Text className="mutedText">管理背景、字色和默认检测参数</Text>
        </div>
        <Button appearance="primary" icon={<Save24Regular />} onClick={create}>保存预设</Button>
      </div>
      <Card className="contentCard">
        <div className="formGrid">
          <Field label="名称"><Input value={form.name} onChange={(_, data) => setForm({ ...form, name: data.value })} /></Field>
          <Field label="背景图"><Input value={form.background_image} onChange={(_, data) => setForm({ ...form, background_image: data.value })} /></Field>
          <div className="fieldButton">
            <Tooltip content="选择背景图" relationship="label">
              <Button icon={<Image24Regular />} onClick={chooseBackground}>选择背景图</Button>
            </Tooltip>
          </div>
          <Field label="字色"><Input value={form.ink_color} onChange={(_, data) => setForm({ ...form, ink_color: data.value })} /></Field>
          <Field label="前景阈值"><Input type="number" value={String(form.foreground_threshold)} onChange={(_, data) => setForm({ ...form, foreground_threshold: Number(data.value) })} /></Field>
          <Field label="模式">
            <Select value={form.mode} onChange={(event) => setForm({ ...form, mode: event.target.value })}>
              <Option value="row">横向行</Option>
              <Option value="col">竖向列</Option>
            </Select>
          </Field>
          <Field label="列检测">
            <Select value={form.column_detection} onChange={(event) => setForm({ ...form, column_detection: event.target.value })}>
              <Option value="gray">灰底栏</Option>
              <Option value="ink">墨迹列</Option>
            </Select>
          </Field>
        </div>
      </Card>
      <div className="presetGrid">
        {presets.map((preset) => (
          <Card key={preset.id} className="presetCard">
            <CardHeader header={<Text weight="semibold">{preset.name}</Text>} description={<Text size={200}>{preset.mode} · {preset.column_detection}</Text>} />
            <Text size={200}>{preset.ink_color} · 阈值 {preset.foreground_threshold}</Text>
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
          <Text className="mutedText">配置本地数据目录和默认导出行为</Text>
        </div>
        <Button appearance="primary" icon={<Save24Regular />} onClick={save}>保存</Button>
      </div>
      <Card className="contentCard">
        <div className="formGrid">
          <Field label="数据目录"><Input value={settings.data_dir || ""} onChange={(_, data) => setSettings({ ...settings, data_dir: data.value })} /></Field>
          <Field label="默认 DPI"><Input value={settings.default_dpi || "300"} onChange={(_, data) => setSettings({ ...settings, default_dpi: data.value })} /></Field>
          <Field label="默认导出目录"><Input value={settings.default_export_dir || ""} onChange={(_, data) => setSettings({ ...settings, default_export_dir: data.value })} /></Field>
        </div>
      </Card>
    </section>
  );
}
