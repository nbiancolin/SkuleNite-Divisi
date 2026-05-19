import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Collapse,
  Container,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconMessageCircle, IconCheck, IconMusic, IconRefresh } from "@tabler/icons-react";
import { Document, Page, pdfjs } from "react-pdf";
import { apiService } from "../../services/apiService";
import type { ArrangementVersionCommentThread, VersionHistoryItem } from "../../services/apiService";
import { parseVersionIdParam } from "./scoreReviewUtils";

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export default function ScoreReviewPage() {
  const { id: arrangementIdParam = "" } = useParams();
  const arrangementId = Number(arrangementIdParam);
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [arrangementTitle, setArrangementTitle] = useState<string>("");
  const [versionHistory, setVersionHistory] = useState<VersionHistoryItem[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [scoreUrl, setScoreUrl] = useState<string>("");
  const [audioUrl, setAudioUrl] = useState<string>("");
  const [audioActionLoading, setAudioActionLoading] = useState(false);
  const [renderableScoreUrl, setRenderableScoreUrl] = useState<string>("");
  const [scoreLoadError, setScoreLoadError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [threads, setThreads] = useState<ArrangementVersionCommentThread[]>([]);
  const [threadBody, setThreadBody] = useState("");
  const [replyBodies, setReplyBodies] = useState<Record<number, string>>({});
  const [placingAnchor, setPlacingAnchor] = useState<{ x: number; y: number } | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [collapsedResolvedThreads, setCollapsedResolvedThreads] = useState<Record<number, boolean>>({});
  const [pdfPageWidth, setPdfPageWidth] = useState<number>(900);
  const [selectedThreadId, setSelectedThreadId] = useState<number | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const commentsContainerRef = useRef<HTMLDivElement | null>(null);
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const commentPageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const threadCardRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const versionSequenceById = useMemo(() => {
    // Compute a user-facing version number from oldest -> newest.
    const sorted = [...versionHistory].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
    return new Map(sorted.map((version, index) => [version.id, index + 1]));
  }, [versionHistory]);

  const versionOptions = useMemo(
    () =>
      versionHistory.map((v) => ({
        value: String(v.id),
        label: `v${versionSequenceById.get(v.id) ?? "?"}${v.is_latest ? " (latest)" : ""}`,
      })),
    [versionHistory, versionSequenceById]
  );

  const audioState = useMemo(() => {
    if (!selectedVersionId) return "none" as const;
    return versionHistory.find((v) => v.id === selectedVersionId)?.audio_state ?? "none";
  }, [versionHistory, selectedVersionId]);

  const sortedThreads = useMemo(
    () => [...threads].sort((a, b) => a.page_number - b.page_number || a.id - b.id),
    [threads]
  );

  const unresolvedThreadCount = useMemo(
    () => threads.filter((thread) => thread.status === "open").length,
    [threads]
  );

  async function refreshAudioLinks(versionId: number) {
    const links = await apiService.getDownloadLinksForVersion(versionId);
    setAudioUrl(links.mp3_link || "");
  }

  async function pollUntilAudioSettled(versionId: number) {
    const maxAttempts = 120;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      await new Promise((r) => setTimeout(r, 1500));
      const history = await apiService.getVersionHistory(arrangementId);
      setVersionHistory(history);
      const state = history.find((v) => v.id === versionId)?.audio_state ?? "none";
      if (state === "complete" || state === "error") {
        return state;
      }
    }
    return "none" as const;
  }

  async function onCheckAudioStatus() {
    if (!selectedVersionId) return;
    try {
      setAudioActionLoading(true);
      const history = await apiService.getVersionHistory(arrangementId);
      setVersionHistory(history);
      const state = history.find((v) => v.id === selectedVersionId)?.audio_state ?? "none";
      if (state === "complete") {
        await refreshAudioLinks(selectedVersionId);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setAudioActionLoading(false);
    }
  }

  async function onGenerateMidi() {
    if (!selectedVersionId || audioState === "error") return;
    try {
      setAudioActionLoading(true);
      await apiService.triggerAudioExport(selectedVersionId);
      setVersionHistory((prev) =>
        prev.map((v) => (v.id === selectedVersionId ? { ...v, audio_state: "processing" } : v))
      );
      const settled = await pollUntilAudioSettled(selectedVersionId);
      if (settled === "complete") {
        await refreshAudioLinks(selectedVersionId);
      }
    } catch (err) {
      console.error(err);
      const history = await apiService.getVersionHistory(arrangementId);
      setVersionHistory(history);
    } finally {
      setAudioActionLoading(false);
    }
  }

  async function loadThreads(versionId: number) {
    const data = await apiService.getVersionComments(versionId);
    setThreads(data.threads);
    setSelectedThreadId(null);
  }

  const requestedVersionParam = searchParams.get("version_id");

  useEffect(() => {
    let isCancelled = false;
    let nextBlobUrl: string | null = null;

    async function fetchPdfData() {
      setRenderableScoreUrl("");
      setScoreLoadError(null);
      setNumPages(0);
      if (!scoreUrl) return;

      try {
        const response = await fetch(scoreUrl);
        if (!response.ok) {
          throw new Error(`Failed to fetch PDF bytes (status ${response.status})`);
        }
        const blob = await response.blob();
        nextBlobUrl = URL.createObjectURL(blob);
        if (!isCancelled) {
          setRenderableScoreUrl(nextBlobUrl);
        }
      } catch (err) {
        if (!isCancelled) {
          setScoreLoadError(err instanceof Error ? err.message : "Unable to fetch PDF file.");
        }
      }
    }

    fetchPdfData();

    return () => {
      isCancelled = true;
      if (nextBlobUrl) {
        URL.revokeObjectURL(nextBlobUrl);
      }
    };
  }, [scoreUrl]);

  useEffect(() => {
    async function loadInitial() {
      try {
        setLoading(true);
        setError(null);
        const arrangement = await apiService.getArrangementById(arrangementId);
        setArrangementTitle(`${arrangement.mvt_no}: ${arrangement.title}`);
        const history = await apiService.getVersionHistory(arrangementId);
        setVersionHistory(history);

        const requestedVersionId = parseVersionIdParam(requestedVersionParam);
        const latestVersionId = arrangement.latest_version?.id ?? history[0]?.id ?? null;
        const versionIdToLoad =
          requestedVersionId && history.some((v) => v.id === requestedVersionId)
            ? requestedVersionId
            : latestVersionId;

        if (!versionIdToLoad) {
          setError("No arrangement version is available yet.");
          return;
        }

        if (requestedVersionId !== versionIdToLoad) {
          setSearchParams({ version_id: String(versionIdToLoad) }, { replace: true });
        }

        const links = await apiService.getDownloadLinksForVersion(versionIdToLoad);
        setSelectedVersionId(versionIdToLoad);
        setScoreUrl(links.score_parts_pdf_link || links.score_pdf_url || "");
        setAudioUrl(links.mp3_link || "");
        await loadThreads(versionIdToLoad);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load score review.");
      } finally {
        setLoading(false);
      }
    }

    if (Number.isInteger(arrangementId) && arrangementId > 0) {
      loadInitial();
    } else {
      setError("Invalid arrangement id.");
      setLoading(false);
    }
  }, [arrangementId, requestedVersionParam, setSearchParams]);

  useEffect(() => {
    setCollapsedResolvedThreads((prev) => {
      const next = { ...prev };
      for (const thread of threads) {
        if (thread.status === "resolved" && next[thread.id] === undefined) {
          next[thread.id] = true;
        }
      }
      return next;
    });
  }, [threads]);

  useEffect(() => {
    function updatePdfPageWidth() {
      if (!scrollContainerRef.current) return;
      const containerWidth = scrollContainerRef.current.clientWidth;
      // Account for container padding and keep a small right-side gutter.
      const width = Math.max(320, Math.floor(containerWidth - 28));
      setPdfPageWidth(width);
    }

    updatePdfPageWidth();

    const observer = new ResizeObserver(() => updatePdfPageWidth());
    if (scrollContainerRef.current) {
      observer.observe(scrollContainerRef.current);
    }

    window.addEventListener("resize", updatePdfPageWidth);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updatePdfPageWidth);
    };
  }, []);

  async function onSelectVersion(value: string | null) {
    const nextId = parseVersionIdParam(value);
    if (!nextId) return;
    setSearchParams({ version_id: String(nextId) });
    const links = await apiService.getDownloadLinksForVersion(nextId);
    setSelectedVersionId(nextId);
    setScoreUrl(links.score_parts_pdf_link || links.score_pdf_url || "");
    setAudioUrl(links.mp3_link || "");
    await loadThreads(nextId);
  }

  function onDocumentLoadSuccess({ numPages: nextNumPages }: { numPages: number }) {
    setNumPages(nextNumPages);
    if (pageNumber > nextNumPages) {
      setPageNumber(nextNumPages);
    }
    setScoreLoadError(null);
  }

  function onDocumentLoadError() {
    setScoreLoadError("Could not load this PDF in the in-page viewer.");
  }

  async function onCreateThread() {
    if (!selectedVersionId || !placingAnchor || !threadBody.trim()) return;
    await apiService.createVersionCommentThread(selectedVersionId, {
      page_number: pageNumber,
      x: placingAnchor.x,
      y: placingAnchor.y,
      body: threadBody.trim(),
    });
    setThreadBody("");
    setPlacingAnchor(null);
    setCreateModalOpen(false);
    await loadThreads(selectedVersionId);
  }

  async function onReply(threadId: number) {
    if (!selectedVersionId) return;
    const body = replyBodies[threadId]?.trim();
    if (!body) return;
    await apiService.createVersionCommentMessage(selectedVersionId, threadId, { body });
    setReplyBodies((prev) => ({ ...prev, [threadId]: "" }));
    await loadThreads(selectedVersionId);
  }

  async function onResolveToggle(thread: ArrangementVersionCommentThread) {
    if (!selectedVersionId) return;
    if (thread.status === "open") {
      await apiService.resolveVersionCommentThread(selectedVersionId, thread.id);
    } else {
      await apiService.reopenVersionCommentThread(selectedVersionId, thread.id);
    }
    await loadThreads(selectedVersionId);
  }

  function onOverlayClick(event: MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    setPlacingAnchor({ x, y });
    setCreateModalOpen(true);
  }

  function handlePageSelect(value: string | null) {
    const nextPage = Number(value || "1");
    if (!Number.isInteger(nextPage) || nextPage < 1) return;
    setPageNumber(nextPage);
    const pageNode = pageRefs.current[nextPage];
    if (pageNode) {
      pageNode.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function onScrollPdfContainer() {
    if (!scrollContainerRef.current) return;
    const containerRect = scrollContainerRef.current.getBoundingClientRect();
    let bestPage = pageNumber;
    let bestDistance = Number.MAX_SAFE_INTEGER;

    for (let p = 1; p <= numPages; p += 1) {
      const node = pageRefs.current[p];
      if (!node) continue;
      const pageRect = node.getBoundingClientRect();
      const distance = Math.abs(pageRect.top - containerRect.top);
      if (distance < bestDistance) {
        bestDistance = distance;
        bestPage = p;
      }
    }

    if (bestPage !== pageNumber) {
      setPageNumber(bestPage);
    }
  }

  useEffect(() => {
    if (!commentsContainerRef.current) return;
    const pageNode = commentPageRefs.current[pageNumber];
    if (!pageNode) return;
    pageNode.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [pageNumber]);

  function onSelectThread(thread: ArrangementVersionCommentThread) {
    const threadId = thread.id;
    const threadPage = thread.page_number;
    setSelectedThreadId(threadId);
    if (threadPage !== pageNumber) {
      setPageNumber(threadPage);
    }
    const scrollContainer = scrollContainerRef.current;
    const pageNode = pageRefs.current[threadPage];
    if (scrollContainer && pageNode) {
      const containerRect = scrollContainer.getBoundingClientRect();
      const pageRect = pageNode.getBoundingClientRect();
      const pageTopWithinContainer = pageRect.top - containerRect.top + scrollContainer.scrollTop;
      const targetTop = pageTopWithinContainer + thread.y * pageNode.clientHeight - scrollContainer.clientHeight * 0.25;
      scrollContainer.scrollTo({
        top: Math.max(0, targetTop),
        behavior: "smooth",
      });
    }
    const threadNode = threadCardRefs.current[threadId];
    if (threadNode) {
      threadNode.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  if (loading) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center">
          <Loader />
          <Text>Loading score review...</Text>
        </Group>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="lg" py="xl">
        <Alert color="red">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container
      fluid
      py={0}
      px="md"
      style={{ height: "100%", overflow: "hidden", boxSizing: "border-box" }}
    >
      <Stack gap="md" style={{ height: "100%", minHeight: 0, overflow: "hidden" }}>
        <Group justify="space-between">
          <Group>
            <Button
              component={Link}
              to={`/app/arrangements/${arrangementId}`}
              variant="subtle"
              leftSection={<IconArrowLeft size={16} />}
            >
              Back to Arrangement
            </Button>
            <Title order={3}>Score Review: {arrangementTitle}</Title>
          </Group>
          <Select
            placeholder="Select version"
            data={versionOptions}
            value={selectedVersionId ? String(selectedVersionId) : null}
            onChange={onSelectVersion}
            w={280}
          />
        </Group>

        <Group align="stretch" wrap="nowrap" style={{ flex: 1, minHeight: 0 }}>
          <Card withBorder style={{ flex: 4, minHeight: 0, height: "100%", display: "flex" }}>
            <Stack gap="sm" style={{ flex: 1, minHeight: 0 }}>
              <Group>
                <Text size="sm">Jump to page:</Text>
                <Select
                  data={Array.from({ length: Math.max(numPages, 1) }).map((_, i) => ({
                    value: String(i + 1),
                    label: String(i + 1),
                  }))}
                  value={String(pageNumber)}
                  onChange={handlePageSelect}
                  w={110}
                />
              </Group>
              <Card withBorder padding="sm" bg="var(--mantine-color-gray-0)">
                <Group gap="xs" mb={6} justify="space-between" wrap="nowrap">
                  <Group gap="xs">
                    <IconMusic size={16} />
                    <Text size="sm" fw={600}>
                      MIDI playback
                    </Text>
                  </Group>
                  {audioState === "none" && (
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<IconMusic size={14} />}
                      loading={audioActionLoading}
                      onClick={onGenerateMidi}
                    >
                      Generate audio
                    </Button>
                  )}
                  {audioState === "processing" && (
                    <Button
                      size="xs"
                      variant="subtle"
                      leftSection={<IconRefresh size={14} />}
                      loading={audioActionLoading}
                      onClick={onCheckAudioStatus}
                    >
                      Check status
                    </Button>
                  )}
                </Group>
                {audioState === "processing" && (
                  <Group gap="xs" py="xs">
                    <Loader size="sm" />
                    <Text size="sm" c="dimmed">
                      Generating audio…
                    </Text>
                  </Group>
                )}
                {audioState === "error" && (
                  <Alert color="red" variant="light" py="xs">
                    Audio export failed. Try again from the arrangement page or contact an admin.
                  </Alert>
                )}
                {audioState === "complete" && audioUrl && (
                  <audio controls preload="none" src={audioUrl}>
                    Your browser does not support embedded audio playback.
                  </audio>
                )}
                {audioState === "complete" && !audioUrl && (
                  <Text size="sm" c="dimmed">
                    Audio is ready but no file URL was returned.{" "}
                    <Button
                      variant="subtle"
                      size="xs"
                      onClick={() => {
                        if (selectedVersionId) void refreshAudioLinks(selectedVersionId);
                      }}
                    >
                      Retry load
                    </Button>
                  </Text>
                )}
                {audioState === "none" && (
                  <Text size="xs" c="dimmed">
                    Export an MP3 preview of this version to listen while you review.
                  </Text>
                )}
              </Card>
              <Box
                ref={scrollContainerRef}
                onScroll={onScrollPdfContainer}
                style={{
                  width: "100%",
                  flex: 1,
                  minHeight: 0,
                  border: "1px solid var(--mantine-color-gray-3)",
                  overflowY: "auto",
                  padding: 8,
                  background: "var(--mantine-color-gray-0)",
                }}
              >
                {!scoreUrl && <Text p="md">No score PDF available for this version.</Text>}
                {scoreUrl && !renderableScoreUrl && !scoreLoadError && (
                  <Group justify="center" py="xl">
                    <Loader size="sm" />
                    <Text size="sm" c="dimmed">
                      Loading PDF...
                    </Text>
                  </Group>
                )}
                {renderableScoreUrl && (
                  <Document
                    file={renderableScoreUrl}
                    onLoadSuccess={onDocumentLoadSuccess}
                    onLoadError={onDocumentLoadError}
                  >
                    {Array.from({ length: numPages || 0 }).map((_, index) => {
                      const renderedPage = index + 1;
                      return (
                        <Box
                          key={renderedPage}
                          ref={(node) => {
                            pageRefs.current[renderedPage] = node;
                          }}
                          pos="relative"
                          mb="md"
                          onClick={(event) => {
                            setPageNumber(renderedPage);
                            onOverlayClick(event);
                          }}
                          style={{ cursor: "crosshair", width: "fit-content", marginInline: "auto" }}
                        >
                          <Page
                            pageNumber={renderedPage}
                            width={pdfPageWidth}
                            renderTextLayer={false}
                            renderAnnotationLayer={false}
                          />
                          {sortedThreads
                            .filter((t) => t.page_number === renderedPage)
                            .map((thread) => (
                              <Badge
                                key={thread.id}
                                color={thread.status === "resolved" ? "gray" : "blue"}
                                variant={selectedThreadId === thread.id ? "filled" : "light"}
                                  onClick={(event) => {
                                  event.stopPropagation();
                                  onSelectThread(thread);
                                }}
                                style={{
                                  position: "absolute",
                                  left: `${thread.x * 100}%`,
                                  top: `${thread.y * 100}%`,
                                  transform: "translate(-50%, -50%)",
                                  cursor: "pointer",
                                }}
                              >
                                #{thread.id}
                              </Badge>
                            ))}
                          {placingAnchor && pageNumber === renderedPage && (
                            <Badge
                              color="orange"
                              style={{
                                position: "absolute",
                                left: `${placingAnchor.x * 100}%`,
                                top: `${placingAnchor.y * 100}%`,
                                transform: "translate(-50%, -50%)",
                                pointerEvents: "none",
                              }}
                            >
                              New
                            </Badge>
                          )}
                        </Box>
                      );
                    })}
                  </Document>
                )}
              </Box>
              {scoreLoadError && (
                <Alert color="yellow" variant="light">
                  {scoreLoadError} Open the source PDF directly:{" "}
                  <a href={scoreUrl} target="_blank" rel="noreferrer">
                    Open score PDF
                  </a>
                </Alert>
              )}
            </Stack>
          </Card>

          <Card
            withBorder
            style={{ flex: 1.5, minHeight: 0, height: "100%", overflowY: "auto" }}
            ref={commentsContainerRef}
          >
            <Stack gap="sm">
              <Group justify="space-between" align="center">
                <Title order={4}>Comment Threads</Title>
                <Text size="sm" c="dimmed">
                  {unresolvedThreadCount} unresolved
                </Text>
              </Group>
              {threads.length === 0 && <Text c="dimmed">No comments yet for this version.</Text>}
              {Array.from({ length: Math.max(numPages, 1) }).map((_, index) => {
                const renderedPage = index + 1;
                const threadsForPage = sortedThreads.filter((t) => t.page_number === renderedPage);
                return (
                  <Box
                    key={renderedPage}
                    ref={(node) => {
                      commentPageRefs.current[renderedPage] = node;
                    }}
                  >
                    <Text
                      size="sm"
                      fw={600}
                      c={renderedPage === pageNumber ? "blue" : undefined}
                      mb="xs"
                    >
                      Page {renderedPage}
                    </Text>
                    <Stack gap="xs">
                      {threadsForPage.length === 0 && (
                        <Text size="xs" c="dimmed">
                          No comments on this page.
                        </Text>
                      )}
                      {threadsForPage.map((thread) => {
                        const isResolved = thread.status === "resolved";
                        const isCollapsed = isResolved && collapsedResolvedThreads[thread.id] !== false;
                        return (
                          <Card
                            key={thread.id}
                            withBorder
                            padding="sm"
                            ref={(node) => {
                              threadCardRefs.current[thread.id] = node;
                            }}
                            onClick={() => onSelectThread(thread)}
                            style={{
                              opacity: isResolved ? 0.78 : 1,
                              cursor: "pointer",
                              borderColor:
                                selectedThreadId === thread.id
                                  ? "var(--mantine-color-blue-6)"
                                  : "var(--mantine-color-gray-3)",
                              background:
                                selectedThreadId === thread.id
                                  ? "var(--mantine-color-blue-0)"
                                  : undefined,
                            }}
                          >
                            <Stack gap="xs">
                              <Group justify="space-between">
                                <Group>
                                  <Badge color={thread.status === "resolved" ? "gray" : "blue"}>
                                    {thread.status}
                                  </Badge>
                                  <Text size="sm">Thread #{thread.id}</Text>
                                </Group>
                                <Group gap="xs">
                                  {isResolved && (
                                    <Button
                                      size="xs"
                                      variant="subtle"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        setCollapsedResolvedThreads((prev) => ({
                                          ...prev,
                                          [thread.id]: !isCollapsed,
                                        }));
                                      }}
                                    >
                                      {isCollapsed ? "Expand" : "Collapse"}
                                    </Button>
                                  )}
                                  <Button
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconCheck size={14} />}
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      onResolveToggle(thread);
                                    }}
                                  >
                                    {thread.status === "open" ? "Resolve" : "Reopen"}
                                  </Button>
                                </Group>
                              </Group>
                              {thread.resolved_by && thread.resolved_at && (
                                <Text size="xs" c="dimmed">
                                  Resolved by {thread.resolved_by.username} at{" "}
                                  {new Date(thread.resolved_at).toLocaleString()}
                                </Text>
                              )}
                              <Collapse in={!isCollapsed}>
                                <Stack gap="xs">
                                  {thread.comments.map((comment) => (
                                    <Card key={comment.id} withBorder padding="xs">
                                      <Text size="sm">{comment.body}</Text>
                                      <Text size="xs" c="dimmed">
                                        {comment.author.username} ·{" "}
                                        {new Date(comment.created_at).toLocaleString()}
                                      </Text>
                                    </Card>
                                  ))}
                                  <Textarea
                                    placeholder="Reply..."
                                    value={replyBodies[thread.id] || ""}
                                    onChange={(e) =>
                                      setReplyBodies((prev) => ({
                                        ...prev,
                                        [thread.id]: e.currentTarget.value,
                                      }))
                                    }
                                    minRows={2}
                                    onClick={(event) => event.stopPropagation()}
                                  />
                                  <Button
                                    size="xs"
                                    variant="light"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      onReply(thread.id);
                                    }}
                                  >
                                    Reply
                                  </Button>
                                </Stack>
                              </Collapse>
                            </Stack>
                          </Card>
                        );
                      })}
                    </Stack>
                  </Box>
                );
              })}
            </Stack>
          </Card>
        </Group>
        <Modal
          opened={createModalOpen}
          onClose={() => setCreateModalOpen(false)}
          title="Add Comment Thread"
        >
          <Stack>
            <Text size="sm" c="dimmed">
              Page {pageNumber}
              {placingAnchor
                ? ` at (${placingAnchor.x.toFixed(3)}, ${placingAnchor.y.toFixed(3)})`
                : ""}
            </Text>
            <Textarea
              placeholder="Write a new comment thread..."
              value={threadBody}
              onChange={(e) => setThreadBody(e.currentTarget.value)}
              minRows={3}
              autoFocus
            />
            <Button
              leftSection={<IconMessageCircle size={16} />}
              onClick={onCreateThread}
              disabled={!placingAnchor || !threadBody.trim() || !selectedVersionId}
            >
              Add Comment Thread
            </Button>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
