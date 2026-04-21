import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { IconArrowLeft, IconMessageCircle, IconCheck } from "@tabler/icons-react";
import { apiService } from "../../services/apiService";
import type { ArrangementVersionCommentThread, VersionHistoryItem } from "../../services/apiService";

export function parseVersionIdParam(raw: string | null): number | null {
  if (!raw) return null;
  const id = Number(raw);
  if (!Number.isInteger(id) || id <= 0) return null;
  return id;
}

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
  const [threads, setThreads] = useState<ArrangementVersionCommentThread[]>([]);
  const [threadBody, setThreadBody] = useState("");
  const [replyBodies, setReplyBodies] = useState<Record<number, string>>({});
  const [placingAnchor, setPlacingAnchor] = useState<{ x: number; y: number } | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);

  const versionOptions = useMemo(
    () =>
      versionHistory.map((v) => ({
        value: String(v.id),
        label: `v${v.version_label}${v.is_latest ? " (latest)" : ""}`,
      })),
    [versionHistory]
  );

  async function loadThreads(versionId: number) {
    const data = await apiService.getVersionComments(versionId);
    setThreads(data.threads);
  }

  const requestedVersionParam = searchParams.get("version_id");

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

  async function onSelectVersion(value: string | null) {
    const nextId = parseVersionIdParam(value);
    if (!nextId) return;
    setSearchParams({ version_id: String(nextId) });
    const links = await apiService.getDownloadLinksForVersion(nextId);
    setSelectedVersionId(nextId);
    setScoreUrl(links.score_parts_pdf_link || links.score_pdf_url || "");
    await loadThreads(nextId);
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
    <Container size="xl" py="xl">
      <Stack gap="md">
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

        <Group align="flex-start" grow>
          <Card withBorder style={{ flex: 3, minHeight: 700 }}>
            <Stack gap="sm">
              <Text size="sm" c="dimmed">
                Click on the score area to place a page-position anchor, then submit your thread.
              </Text>
              <Group>
                <Text size="sm">Page number</Text>
                <Select
                  data={Array.from({ length: 200 }).map((_, i) => ({ value: String(i + 1), label: String(i + 1) }))}
                  value={String(pageNumber)}
                  onChange={(v) => setPageNumber(Number(v || 1))}
                  w={110}
                />
              </Group>
              <Box pos="relative" style={{ width: "100%", height: 900, border: "1px solid var(--mantine-color-gray-3)" }}>
                {scoreUrl ? (
                  <object data={scoreUrl} type="application/pdf" width="100%" height="100%">
                    <Text p="md">Unable to render PDF in-browser. Use download links on arrangement page.</Text>
                  </object>
                ) : (
                  <Text p="md">No score PDF available for this version.</Text>
                )}
                <Box
                  pos="absolute"
                  top={0}
                  left={0}
                  right={0}
                  bottom={0}
                  onClick={onOverlayClick}
                  style={{ cursor: "crosshair" }}
                />
                {threads
                  .filter((t) => t.page_number === pageNumber)
                  .map((thread) => (
                    <Badge
                      key={thread.id}
                      color={thread.status === "resolved" ? "green" : "blue"}
                      style={{
                        position: "absolute",
                        left: `${thread.x * 100}%`,
                        top: `${thread.y * 100}%`,
                        transform: "translate(-50%, -50%)",
                      }}
                    >
                      #{thread.id}
                    </Badge>
                  ))}
                {placingAnchor && (
                  <Badge
                    color="orange"
                    style={{
                      position: "absolute",
                      left: `${placingAnchor.x * 100}%`,
                      top: `${placingAnchor.y * 100}%`,
                      transform: "translate(-50%, -50%)",
                    }}
                  >
                    New
                  </Badge>
                )}
              </Box>
              <Textarea
                placeholder="Write a new comment thread..."
                value={threadBody}
                onChange={(e) => setThreadBody(e.currentTarget.value)}
                minRows={2}
              />
              <Button
                leftSection={<IconMessageCircle size={16} />}
                onClick={onCreateThread}
                disabled={!placingAnchor || !threadBody.trim() || !selectedVersionId}
              >
                Add Comment Thread
              </Button>
            </Stack>
          </Card>

          <Card withBorder style={{ flex: 2, maxHeight: 1000, overflowY: "auto" }}>
            <Stack gap="sm">
              <Title order={4}>Comment Threads</Title>
              {threads.length === 0 && <Text c="dimmed">No comments yet for this version.</Text>}
              {threads.map((thread) => (
                <Card key={thread.id} withBorder padding="sm">
                  <Stack gap="xs">
                    <Group justify="space-between">
                      <Group>
                        <Badge color={thread.status === "resolved" ? "green" : "blue"}>{thread.status}</Badge>
                        <Text size="sm">Page {thread.page_number}</Text>
                      </Group>
                      <Button
                        size="xs"
                        variant="light"
                        leftSection={<IconCheck size={14} />}
                        onClick={() => onResolveToggle(thread)}
                      >
                        {thread.status === "open" ? "Resolve" : "Reopen"}
                      </Button>
                    </Group>
                    {thread.resolved_by && thread.resolved_at && (
                      <Text size="xs" c="dimmed">
                        Resolved by {thread.resolved_by.username} at {new Date(thread.resolved_at).toLocaleString()}
                      </Text>
                    )}
                    {thread.comments.map((comment) => (
                      <Card key={comment.id} withBorder padding="xs">
                        <Text size="sm">{comment.body}</Text>
                        <Text size="xs" c="dimmed">
                          {comment.author.username} · {new Date(comment.created_at).toLocaleString()}
                        </Text>
                      </Card>
                    ))}
                    <Textarea
                      placeholder="Reply..."
                      value={replyBodies[thread.id] || ""}
                      onChange={(e) =>
                        setReplyBodies((prev) => ({ ...prev, [thread.id]: e.currentTarget.value }))
                      }
                      minRows={2}
                    />
                    <Button size="xs" variant="light" onClick={() => onReply(thread.id)}>
                      Reply
                    </Button>
                  </Stack>
                </Card>
              ))}
            </Stack>
          </Card>
        </Group>
      </Stack>
    </Container>
  );
}
