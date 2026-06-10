import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Collapse,
  Divider,
  Group,
  Loader,
  SegmentedControl,
  Stack,
  Text,
} from "@mantine/core";
import {
  IconBook,
  IconChevronDown,
  IconChevronRight,
  IconDownload,
  IconGripVertical,
  IconRefresh,
} from "@tabler/icons-react";
import { apiService } from "../../services/apiService";
import type {
  Ensemble,
  EnsemblePartBook,
  PartBookLayout,
  PartName,
} from "../../services/apiService";

type Props = {
  ensemble: Ensemble;
  partNames: PartName[];
  onRefresh: () => void;
  onError: (message: string) => void;
  fillHeight?: boolean;
};

type SavedLayoutValue = "default" | PartBookLayout;
type OneOffLayoutValue = "saved" | PartBookLayout;

function layoutLabel(layout: PartBookLayout): string {
  return layout === "single_sided" ? "Single-sided" : "Double-sided";
}

function savedLayoutSubtitle(part: PartName, ensemble: Ensemble): string {
  const effective =
    part.effective_part_book_layout ??
    ensemble.default_part_book_layout ??
    "double_sided";
  if (part.part_book_layout_override) {
    return `${layoutLabel(effective)} (override)`;
  }
  return `${layoutLabel(effective)} (default)`;
}

export function EnsemblePartBooksSection({
  ensemble,
  partNames,
  onRefresh,
  onError,
  fillHeight = false,
}: Props) {
  const [expandedPartId, setExpandedPartId] = useState<number | null>(null);
  const [reorderingParts, setReorderingParts] = useState(false);
  const [draggedPartId, setDraggedPartId] = useState<number | null>(null);
  const [dragOverPartId, setDragOverPartId] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);
  const [regeneratingPartId, setRegeneratingPartId] = useState<number | null>(null);
  const [savingLayoutPartId, setSavingLayoutPartId] = useState<number | null>(null);
  const [oneOffLayouts, setOneOffLayouts] = useState<Record<number, OneOffLayoutValue>>({});

  const isAdmin = ensemble.is_admin;
  const latestRev = ensemble.latest_part_book_revision ?? 0;

  const getOneOffLayout = (partId: number): OneOffLayoutValue =>
    oneOffLayouts[partId] ?? "saved";

  const buildLayoutOverrides = (): Record<number, PartBookLayout> | undefined => {
    const overrides: Record<number, PartBookLayout> = {};
    for (const part of partNames) {
      const oneOff = getOneOffLayout(part.id);
      if (oneOff !== "saved") {
        overrides[part.id] = oneOff;
      }
    }
    return Object.keys(overrides).length > 0 ? overrides : undefined;
  };

  const clearOneOffLayouts = () => setOneOffLayouts({});

  const handleGeneratePartBooks = async () => {
    try {
      setGenerating(true);
      await apiService.generatePartBooksForEnsemble(
        ensemble.slug,
        buildLayoutOverrides()
      );
      clearOneOffLayouts();
      onRefresh();
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setGenerating(false);
    }
  };

  const handleRegeneratePart = async (part: PartName) => {
    try {
      setRegeneratingPartId(part.id);
      const oneOff = getOneOffLayout(part.id);
      await apiService.generatePartBookForPart(
        ensemble.slug,
        part.id,
        oneOff !== "saved" ? oneOff : undefined
      );
      setOneOffLayouts((prev) => {
        const next = { ...prev };
        delete next[part.id];
        return next;
      });
      onRefresh();
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setRegeneratingPartId(null);
    }
  };

  const handleSavedLayoutChange = async (
    part: PartName,
    value: SavedLayoutValue
  ) => {
    const override: PartBookLayout | null =
      value === "default" ? null : value;
    try {
      setSavingLayoutPartId(part.id);
      await apiService.updatePartBookLayout(ensemble.slug, [
        { id: part.id, part_book_layout_override: override },
      ]);
      onRefresh();
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingLayoutPartId(null);
    }
  };

  const sortedParts = partNames
    .slice()
    .sort((a, b) => {
      if (a.order !== null && b.order !== null) return a.order - b.order;
      if (a.order !== null) return -1;
      if (b.order !== null) return 1;
      return a.display_name.localeCompare(b.display_name);
    });

  return (
    <Card
      withBorder
      radius="md"
      p="lg"
      style={
        fillHeight
          ? { height: "100%", display: "flex", flexDirection: "column", minHeight: 0 }
          : undefined
      }
    >
      <Group mb="md" justify="space-between">
        <Group gap="xs">
          <IconBook size={20} />
          <Text fw={600} size="lg">
            Part books
          </Text>
          <Badge size="sm" variant="light">
            {partNames.length} parts
          </Badge>
          {ensemble.part_books_generating && (
            <Badge color="blue" variant="light" leftSection={<Loader size={12} />}>
              Generating…
            </Badge>
          )}
        </Group>
        {isAdmin && (
          <Button
            size="sm"
            variant="filled"
            leftSection={<IconRefresh size={14} />}
            onClick={handleGeneratePartBooks}
            loading={generating}
            disabled={!!ensemble.part_books_generating || partNames.length === 0}
          >
            Generate part books
          </Button>
        )}
      </Group>
      <Text size="sm" c="dimmed" mb="md">
        Compiled PDFs per part across all arrangements. Drag to reorder how parts appear in exports.
        Saved layout overrides persist; one-off layout applies only to the next generate/regenerate.
      </Text>
      <Divider mb="md" />

      {partNames.length === 0 ? (
        <Text size="sm" c="dimmed">
          No part books yet. Add part names above, then generate.
        </Text>
      ) : (
        <div
          style={
            fillHeight
              ? { flex: 1, minHeight: 0, overflowY: "auto" }
              : { maxHeight: 480, overflowY: "auto" }
          }
        >
          <Stack gap={0}>
            {sortedParts.map((part, index, sortedPartsList) => {
              const partBooks: EnsemblePartBook[] = (ensemble.part_books ?? [])
                .filter((b) => b.part_display_name === part.display_name)
                .sort((a, b) => b.revision - a.revision);
              const latestBook = partBooks[0];
              const olderBooks = partBooks.slice(1);
              const isExpanded = expandedPartId === part.id;
              const isDragging = draggedPartId === part.id;
              const isDragOver = dragOverPartId === part.id;
              const savedLayoutValue: SavedLayoutValue =
                part.part_book_layout_override ?? "default";
              const effectiveLayout =
                part.effective_part_book_layout ??
                ensemble.default_part_book_layout ??
                "double_sided";

              const handleDragStart = (e: React.DragEvent) => {
                if (!isAdmin) return;
                setDraggedPartId(part.id);
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/plain", part.id.toString());
                if (e.currentTarget instanceof HTMLElement) {
                  e.currentTarget.style.opacity = "0.5";
                }
              };

              const handleDragEnd = (e: React.DragEvent) => {
                setDraggedPartId(null);
                setDragOverPartId(null);
                if (e.currentTarget instanceof HTMLElement) {
                  e.currentTarget.style.opacity = "1";
                }
              };

              const handleDragOver = (e: React.DragEvent) => {
                if (!isAdmin || draggedPartId === part.id) return;
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                setDragOverPartId(part.id);
              };

              const handleDragLeave = () => setDragOverPartId(null);

              const handleDrop = async (e: React.DragEvent) => {
                e.preventDefault();
                if (!isAdmin || draggedPartId === null || draggedPartId === part.id) {
                  setDragOverPartId(null);
                  return;
                }

                const draggedIndex = sortedPartsList.findIndex((p) => p.id === draggedPartId);
                const targetIndex = index;
                if (draggedIndex === -1 || draggedIndex === targetIndex) {
                  setDragOverPartId(null);
                  return;
                }

                const reorderedParts = [...sortedPartsList];
                const [draggedPart] = reorderedParts.splice(draggedIndex, 1);
                reorderedParts.splice(targetIndex, 0, draggedPart);
                const updatedParts = reorderedParts.map((p, i) => ({ ...p, order: i }));

                try {
                  setReorderingParts(true);
                  await apiService.updatePartOrder(
                    ensemble.slug,
                    updatedParts.map((p) => ({ id: p.id, order: p.order ?? 0 }))
                  );
                  onRefresh();
                } catch (err) {
                  onError(
                    err instanceof Error ? err.message : "Failed to update part order."
                  );
                } finally {
                  setReorderingParts(false);
                  setDragOverPartId(null);
                  setDraggedPartId(null);
                }
              };

              return (
                <div key={part.id}>
                  <Card
                    withBorder
                    radius="sm"
                    p="sm"
                    mb="xs"
                    draggable={isAdmin && !reorderingParts}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    style={{
                      cursor: isAdmin ? (isDragging ? "grabbing" : "grab") : "default",
                      opacity: isDragging ? 0.5 : 1,
                      borderColor: isDragOver ? "var(--mantine-color-blue-6)" : undefined,
                      borderWidth: isDragOver ? 2 : undefined,
                      backgroundColor: isDragOver
                        ? "var(--mantine-color-blue-0)"
                        : undefined,
                      transition: "background-color 0.2s, border-color 0.2s",
                    }}
                  >
                    <Group justify="space-between" wrap="nowrap">
                      <Group gap="xs" style={{ minWidth: 0 }}>
                        {isAdmin && (
                          <ActionIcon
                            variant="subtle"
                            size="sm"
                            style={{ cursor: "grab" }}
                            title="Drag to reorder"
                            onMouseDown={(e) => e.stopPropagation()}
                            onClick={(e) => e.stopPropagation()}
                          >
                            <IconGripVertical size={16} />
                          </ActionIcon>
                        )}
                        <ActionIcon
                          variant="subtle"
                          size="sm"
                          onClick={() =>
                            setExpandedPartId(isExpanded ? null : part.id)
                          }
                        >
                          {isExpanded ? (
                            <IconChevronDown size={16} />
                          ) : (
                            <IconChevronRight size={16} />
                          )}
                        </ActionIcon>
                        <Stack gap={2} style={{ minWidth: 0 }}>
                          <Group gap="xs">
                            <Text size="sm" fw={600}>
                              {part.display_name}
                            </Text>
                            {latestBook && (
                              <>
                                <Badge
                                  size="xs"
                                  variant="light"
                                  color={
                                    latestBook.revision === latestRev ? "teal" : "gray"
                                  }
                                >
                                  r{latestBook.revision}{" "}
                                  {latestBook.revision === latestRev ? "(latest)" : ""}
                                </Badge>
                                {!latestBook.is_rendered && (
                                  <Badge size="xs" variant="light" color="yellow">
                                    Rendering…
                                  </Badge>
                                )}
                                {latestBook.layout && (
                                  <Badge size="xs" variant="outline">
                                    {layoutLabel(latestBook.layout)}
                                  </Badge>
                                )}
                              </>
                            )}
                            {!latestBook && (
                              <Text size="xs" c="dimmed">
                                No part book
                              </Text>
                            )}
                          </Group>
                          <Text size="xs" c="dimmed">
                            {savedLayoutSubtitle(part, ensemble)}
                          </Text>
                        </Stack>
                      </Group>
                      <Group gap="xs" wrap="nowrap">
                        {(isAdmin || latestBook) && (
                          <Button
                            size="xs"
                            variant="light"
                            leftSection={<IconRefresh size={14} />}
                            onClick={() => handleRegeneratePart(part)}
                            loading={regeneratingPartId === part.id}
                            disabled={!!ensemble.part_books_generating}
                          >
                            Regenerate
                          </Button>
                        )}
                        {latestBook?.is_rendered && latestBook.download_url && (
                          <Button
                            component="a"
                            href={latestBook.download_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            size="xs"
                            variant="light"
                            leftSection={<IconDownload size={14} />}
                          >
                            Download
                          </Button>
                        )}
                      </Group>
                    </Group>

                    <Collapse in={isExpanded}>
                      <Stack gap="sm" mt="sm" pl="md">
                        {isAdmin && (
                          <Stack gap={4}>
                            <Text size="xs" fw={500}>
                              Saved layout for this part
                            </Text>
                            <SegmentedControl
                              size="xs"
                              value={savedLayoutValue}
                              disabled={savingLayoutPartId === part.id}
                              onChange={(value) =>
                                handleSavedLayoutChange(
                                  part,
                                  value as SavedLayoutValue
                                )
                              }
                              data={[
                                { value: "default", label: "Use default" },
                                { value: "single_sided", label: "Single-sided" },
                                { value: "double_sided", label: "Double-sided" },
                              ]}
                            />
                          </Stack>
                        )}
                        {(isAdmin || latestBook) && (
                          <Stack gap={4}>
                            <Text size="xs" fw={500}>
                              Layout for this generation
                            </Text>
                            <SegmentedControl
                              size="xs"
                              value={getOneOffLayout(part.id)}
                              onChange={(value) =>
                                setOneOffLayouts((prev) => ({
                                  ...prev,
                                  [part.id]: value as OneOffLayoutValue,
                                }))
                              }
                              data={[
                                {
                                  value: "saved",
                                  label: `Use saved (${layoutLabel(effectiveLayout)})`,
                                },
                                { value: "single_sided", label: "Single-sided" },
                                { value: "double_sided", label: "Double-sided" },
                              ]}
                            />
                          </Stack>
                        )}

                        {olderBooks.length > 0 && (
                          <Stack
                            gap="xs"
                            style={{
                              borderLeft: "2px solid var(--mantine-color-default-border)",
                              paddingLeft: "var(--mantine-spacing-md)",
                            }}
                          >
                            <Text size="xs" c="dimmed" fw={500}>
                              Older revisions
                            </Text>
                            {olderBooks.map((book) => (
                              <Group key={book.id} justify="space-between">
                                <Group gap="xs">
                                  <Text size="sm">Revision {book.revision}</Text>
                                  {book.layout && (
                                    <Badge size="xs" variant="outline">
                                      {layoutLabel(book.layout)}
                                    </Badge>
                                  )}
                                  {book.layout &&
                                    book.layout !== effectiveLayout && (
                                      <Text size="xs" c="dimmed">
                                        (differs from current setting)
                                      </Text>
                                    )}
                                  {!book.is_rendered && (
                                    <Badge size="xs" variant="light" color="yellow">
                                      Rendering…
                                    </Badge>
                                  )}
                                </Group>
                                {book.is_rendered && book.download_url && (
                                  <Button
                                    component="a"
                                    href={book.download_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    size="xs"
                                    variant="subtle"
                                    leftSection={<IconDownload size={12} />}
                                  >
                                    Download
                                  </Button>
                                )}
                              </Group>
                            ))}
                          </Stack>
                        )}
                      </Stack>
                    </Collapse>
                  </Card>
                </div>
              );
            })}
          </Stack>
        </div>
      )}
    </Card>
  );
}
