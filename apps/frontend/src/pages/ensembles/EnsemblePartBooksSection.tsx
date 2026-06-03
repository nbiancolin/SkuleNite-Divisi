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
import type { Ensemble, EnsemblePartBook, PartName } from "../../services/apiService";

type Props = {
  ensemble: Ensemble;
  partNames: PartName[];
  onRefresh: () => void;
  onError: (message: string) => void;
};

export function EnsemblePartBooksSection({
  ensemble,
  partNames,
  onRefresh,
  onError,
}: Props) {
  const [expandedPartId, setExpandedPartId] = useState<number | null>(null);
  const [reorderingParts, setReorderingParts] = useState(false);
  const [draggedPartId, setDraggedPartId] = useState<number | null>(null);
  const [dragOverPartId, setDragOverPartId] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);

  const isAdmin = ensemble.is_admin;
  const latestRev = ensemble.latest_part_book_revision ?? 0;

  const handleGeneratePartBooks = async () => {
    try {
      setGenerating(true);
      await apiService.generatePartBooksForEnsemble(ensemble.slug);
      onRefresh();
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : String(err));
    } finally {
      setGenerating(false);
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
    <Card withBorder radius="md" p="lg">
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
      </Text>
      <Divider mb="md" />

      {partNames.length === 0 ? (
        <Text size="sm" c="dimmed">
          No part books yet. Add part names above, then generate.
        </Text>
      ) : (
        <div style={{ maxHeight: 480, overflowY: "auto" }}>
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
                          disabled={olderBooks.length === 0}
                          title={olderBooks.length ? "Older revisions" : undefined}
                        >
                          {olderBooks.length > 0 ? (
                            isExpanded ? (
                              <IconChevronDown size={16} />
                            ) : (
                              <IconChevronRight size={16} />
                            )
                          ) : (
                            <IconChevronRight size={16} style={{ opacity: 0.3 }} />
                          )}
                        </ActionIcon>
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
                          </>
                        )}
                        {!latestBook && (
                          <Text size="xs" c="dimmed">
                            No part book
                          </Text>
                        )}
                      </Group>
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
                    <Collapse in={isExpanded && olderBooks.length > 0}>
                      <Stack
                        gap="xs"
                        mt="sm"
                        pl="md"
                        style={{
                          borderLeft: "2px solid var(--mantine-color-default-border)",
                        }}
                      >
                        <Text size="xs" c="dimmed" fw={500}>
                          Older revisions
                        </Text>
                        {olderBooks.map((book) => (
                          <Group key={book.id} justify="space-between">
                            <Group gap="xs">
                              <Text size="sm">Revision {book.revision}</Text>
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
