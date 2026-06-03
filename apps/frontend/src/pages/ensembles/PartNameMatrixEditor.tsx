import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { IconGripVertical, IconLink, IconX } from "@tabler/icons-react";
import { apiService } from "../../services/apiService";
import { usePartNameMatrix } from "./usePartNameMatrix";
import {
  buildDisplayGroups,
  canLinkColumns,
  cellKey,
  getBaseId,
  getConflictingArrangementIds,
  getPendingMergeIds,
  groupCellBorderClass,
  linkColumnToBase,
  pairsConflict,
  unlinkColumn,
  type DisplayGroup,
  type MergeLinks,
} from "./partNameMatrixUtils";
import "./PartNameMatrixEditor.css";

type Props = {
  ensembleSlug: string;
  isAdmin: boolean;
  onSaved?: () => void;
};

function ColumnHeader({
  displayName,
  isAdmin,
  isMergeBase,
  isMember,
  isDragging,
  isDropTarget,
  onDisplayNameChange,
  onUnlink,
  onDragHandleStart,
  onDragHandleEnd,
}: {
  displayName: string;
  isAdmin: boolean;
  isMergeBase: boolean;
  isMember: boolean;
  isDragging: boolean;
  isDropTarget: boolean;
  onDisplayNameChange: (value: string) => void;
  onUnlink?: () => void;
  onDragHandleStart: (e: React.DragEvent) => void;
  onDragHandleEnd: (e: React.DragEvent) => void;
}) {
  const className = [
    isMergeBase || isDropTarget ? "merge-header-base" : "",
    isMember ? "merge-header-member" : "",
    isDropTarget ? "merge-header-drop-target" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Stack gap={4} className={className} p={4} style={{ opacity: isDragging ? 0.45 : 1 }}>
      {isAdmin && (
        <Group gap={4} wrap="nowrap" justify="space-between">
          <Box
            component="span"
            draggable
            onDragStart={onDragHandleStart}
            onDragEnd={onDragHandleEnd}
            style={{ cursor: "grab", display: "inline-flex", lineHeight: 0 }}
            title="Drag to merge into another part"
          >
            <IconGripVertical size={14} />
          </Box>
          {isMergeBase && (
            <Badge size="xs" variant="filled" color="teal">
              Base
            </Badge>
          )}
          {isMember && onUnlink && (
            <Tooltip label="Unlink from merge">
              <ActionIcon
                variant="subtle"
                size="xs"
                color="gray"
                onClick={onUnlink}
                aria-label="Unlink"
              >
                <IconX size={12} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      )}
      {isAdmin ? (
        <TextInput
          size="xs"
          value={displayName}
          onChange={(e) => onDisplayNameChange(e.currentTarget.value)}
          aria-label={`Part name ${displayName}`}
        />
      ) : (
        <Text size="xs" fw={600} ta="center">
          {displayName}
        </Text>
      )}
      {isAdmin && isDropTarget && (
        <Text size="10px" c="dimmed" ta="center">
          Release to merge here
        </Text>
      )}
      {isAdmin && isMember && (
        <Group gap={4} justify="center">
          <IconLink size={12} style={{ color: "var(--mantine-color-teal-6)" }} />
          <Text size="10px" c="teal">
            Linked
          </Text>
        </Group>
      )}
    </Stack>
  );
}

export function PartNameMatrixEditor({ ensembleSlug, isAdmin, onSaved }: Props) {
  const { matrix, loading, error, reload } = usePartNameMatrix(ensembleSlug);
  const [displayNames, setDisplayNames] = useState<Record<number, string>>({});
  const [mergeLinks, setMergeLinks] = useState<MergeLinks>({});
  const [draggedColumnId, setDraggedColumnId] = useState<number | null>(null);
  const draggedColumnIdRef = useRef<number | null>(null);
  const [dropTargetBaseId, setDropTargetBaseId] = useState<number | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!matrix) return;
    const names: Record<number, string> = {};
    for (const col of matrix.columns) {
      names[col.id] = col.display_name;
    }
    setDisplayNames(names);
    setMergeLinks({});
    setDraggedColumnId(null);
    draggedColumnIdRef.current = null;
    setDropTargetBaseId(null);
    setLinkError(null);
  }, [matrix]);

  const displayGroups = useMemo(
    () => (matrix ? buildDisplayGroups(matrix.columns, mergeLinks) : []),
    [matrix, mergeLinks]
  );

  const flatColumns = useMemo(
    () => displayGroups.flatMap((g) => g.columns),
    [displayGroups]
  );

  const cellSet = useMemo(() => {
    const set = new Set<string>();
    if (!matrix) return set;
    for (const cell of matrix.cells) {
      set.add(cellKey(cell.arrangement_id, cell.part_name_id));
    }
    return set;
  }, [matrix]);

  const pendingMergeGroups = useMemo(() => {
    const baseIds = new Set<number>();
    for (const memberIdStr of Object.keys(mergeLinks)) {
      baseIds.add(mergeLinks[Number(memberIdStr)]);
    }
    return [...baseIds].map((baseId) => ({
      baseId,
      ids: getPendingMergeIds(baseId, mergeLinks),
    }));
  }, [mergeLinks]);

  const conflictArrangementIds = useMemo(() => {
    if (!matrix) return [];
    const ids: number[] = [];
    for (const { ids: groupIds } of pendingMergeGroups) {
      ids.push(...getConflictingArrangementIds(groupIds, matrix.cells));
    }
    return [...new Set(ids)];
  }, [matrix, pendingMergeGroups]);

  const mergeBlocked = useMemo(() => {
    if (!matrix) return false;
    for (const { ids } of pendingMergeGroups) {
      if (ids.length < 2) continue;
      if (pairsConflict(ids, matrix.merge_conflicts)) return true;
      if (getConflictingArrangementIds(ids, matrix.cells).length > 0) return true;
    }
    return false;
  }, [matrix, pendingMergeGroups]);

  const dirtyRenames = useMemo(() => {
    if (!matrix) return [];
    const mergingIds = new Set(Object.keys(mergeLinks).map(Number));
    for (const { baseId, ids } of pendingMergeGroups) {
      ids.forEach((id) => mergingIds.add(id));
      mergingIds.add(baseId);
    }
    return matrix.columns.filter((col) => {
      const newName = (displayNames[col.id] ?? col.display_name).trim();
      return newName !== col.display_name && !mergingIds.has(col.id);
    });
  }, [matrix, displayNames, mergeLinks, pendingMergeGroups]);

  const hasPendingMerges = Object.keys(mergeLinks).length > 0;
  const hasChanges =
    dirtyRenames.length > 0 || (hasPendingMerges && !mergeBlocked);

  const clearDragState = () => {
    draggedColumnIdRef.current = null;
    setDraggedColumnId(null);
    setDropTargetBaseId(null);
  };

  const handleDragHandleStart = (columnId: number) => (e: React.DragEvent) => {
    if (!isAdmin) return;
    e.stopPropagation();
    draggedColumnIdRef.current = columnId;
    setDraggedColumnId(columnId);
    setLinkError(null);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("application/x-part-name-id", String(columnId));
    e.dataTransfer.setData("text/plain", String(columnId));
  };

  const handleDragHandleEnd = () => {
    clearDragState();
  };

  const handleHeaderDragOver = (targetColumnId: number) => (e: React.DragEvent) => {
    const sourceId = draggedColumnIdRef.current;
    if (!isAdmin || sourceId === null || !matrix) return;

    const check = canLinkColumns(
      sourceId,
      targetColumnId,
      mergeLinks,
      matrix.cells,
      matrix.merge_conflicts
    );
    if (!check.ok) return;

    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "move";
    setDropTargetBaseId(getBaseId(targetColumnId, mergeLinks));
  };

  const handleHeaderDrop = (targetColumnId: number) => (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const sourceId = draggedColumnIdRef.current;
    if (!isAdmin || sourceId === null || !matrix) {
      clearDragState();
      return;
    }

    const check = canLinkColumns(
      sourceId,
      targetColumnId,
      mergeLinks,
      matrix.cells,
      matrix.merge_conflicts
    );

    if (!check.ok) {
      setLinkError(check.reason);
      clearDragState();
      return;
    }

    const targetBase = getBaseId(targetColumnId, mergeLinks);
    setMergeLinks((prev) => linkColumnToBase(sourceId, targetBase, prev));
    setLinkError(null);
    clearDragState();
  };

  const handleSave = useCallback(async () => {
    if (!matrix || !isAdmin) return;
    setSaving(true);
    setSaveError(null);

    try {
      for (const col of dirtyRenames) {
        const newName = (displayNames[col.id] ?? col.display_name).trim();
        if (!newName) throw new Error("Part names cannot be empty.");
        await apiService.renamePartName(ensembleSlug, col.id, newName);
      }

      if (hasPendingMerges) {
        if (mergeBlocked) {
          throw new Error(
            "Cannot merge: linked part names both have parts in the same arrangement version."
          );
        }

        for (const { baseId, ids } of pendingMergeGroups) {
          const mergeIds = ids.filter((id) => id !== baseId);
          if (mergeIds.length === 0) continue;
          const finalName = (displayNames[baseId] ?? "").trim();
          for (const otherId of mergeIds) {
            await apiService.mergePartNames(
              ensembleSlug,
              baseId,
              otherId,
              finalName || null
            );
          }
        }
      }

      await reload();
      onSaved?.();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : String(err));
      await reload();
    } finally {
      setSaving(false);
    }
  }, [
    matrix,
    isAdmin,
    dirtyRenames,
    displayNames,
    hasPendingMerges,
    mergeBlocked,
    pendingMergeGroups,
    ensembleSlug,
    reload,
    onSaved,
  ]);

  const renderHeaderCells = (group: DisplayGroup) =>
    group.columns.map((col) => {
      const isBase = group.kind === "merge" && col.id === group.baseId;
      const isMember = group.kind === "merge" && col.id !== group.baseId;
      const borderClass = groupCellBorderClass(group, col.id);
      const isDropTarget =
        isAdmin && dropTargetBaseId !== null && col.id === dropTargetBaseId;

      const thProps = isAdmin
        ? {
            onDragOver: handleHeaderDragOver(col.id),
            onDragLeave: () => setDropTargetBaseId(null),
            onDrop: handleHeaderDrop(col.id),
          }
        : {};

      return (
        <Table.Th
          key={col.id}
          className={borderClass}
          style={{
            minWidth: 120,
            verticalAlign: "bottom",
            padding: 0,
          }}
          {...thProps}
        >
          <ColumnHeader
            displayName={displayNames[col.id] ?? col.display_name}
            isAdmin={isAdmin}
            isMergeBase={isBase}
            isMember={isMember}
            isDragging={draggedColumnId === col.id}
            isDropTarget={isDropTarget}
            onDisplayNameChange={(value) =>
              setDisplayNames((prev) => ({ ...prev, [col.id]: value }))
            }
            onUnlink={
              isMember
                ? () => setMergeLinks((prev) => unlinkColumn(col.id, prev))
                : undefined
            }
            onDragHandleStart={handleDragHandleStart(col.id)}
            onDragHandleEnd={handleDragHandleEnd}
          />
        </Table.Th>
      );
    });

  const renderBodyCells = (arrangementId: number, group: DisplayGroup) =>
    group.columns.map((col) => {
      const filled = cellSet.has(cellKey(arrangementId, col.id));
      const borderClass = groupCellBorderClass(group, col.id);
      return (
        <Table.Td key={col.id} ta="center" className={borderClass}>
          {filled ? (
            <Text size="lg" c="teal" aria-label="Has part">
              ●
            </Text>
          ) : (
            <Text size="sm" c="dimmed">
              —
            </Text>
          )}
        </Table.Td>
      );
    });

  if (loading) {
    return (
      <Group justify="center" py="md">
        <Loader size="sm" />
        <Text size="sm" c="dimmed">
          Loading part names…
        </Text>
      </Group>
    );
  }

  if (error) {
    return (
      <Alert color="red" title="Could not load part names">
        {error}
      </Alert>
    );
  }

  if (!matrix || matrix.columns.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        No part names yet. Part names are added when you upload arrangement versions with parts.
      </Text>
    );
  }

  return (
    <Stack gap="sm">
      <Text size="xs" c="dimmed">
        Each row is an arrangement; each column is a part name.{" "}
        {isAdmin &&
          "Use the grip (⠿) on a column and drag it onto the part you want to keep. You cannot merge two names that both have a part in the same arrangement."}
      </Text>

      {linkError && (
        <Alert color="red" onClose={() => setLinkError(null)} withCloseButton>
          {linkError}
        </Alert>
      )}

      {saveError && (
        <Alert color="red" onClose={() => setSaveError(null)} withCloseButton>
          {saveError}
        </Alert>
      )}

      {mergeBlocked && isAdmin && hasPendingMerges && (
        <Alert color="orange" title="Merge blocked">
          Linked part names both have parts in the same arrangement version
          {conflictArrangementIds.length > 0 && (
            <>
              {" "}
              for{" "}
              {conflictArrangementIds
                .map((id) => matrix.arrangements.find((a) => a.id === id)?.title ?? id)
                .join(", ")}
            </>
          )}
          . Unlink a column before saving.
        </Alert>
      )}

      <Table.ScrollContainer minWidth={900} type="native" style={{ maxWidth: "100%" }}>
        <Table striped highlightOnHover withTableBorder withColumnBorders stickyHeader>
          <Table.Thead>
            {displayGroups.some((g) => g.kind === "merge") && (
              <Table.Tr>
                <Table.Th
                  style={{ position: "sticky", left: 0, zIndex: 3, background: "var(--mantine-color-body)" }}
                />
                {displayGroups.map((group) =>
                  group.kind === "merge" ? (
                    <Table.Th
                      key={`connector-${group.baseId}`}
                      colSpan={group.columns.length}
                      p={0}
                      style={{ verticalAlign: "bottom", border: "none" }}
                    >
                      <Box className="merge-connector-bar" mx={4} />
                    </Table.Th>
                  ) : (
                    <Table.Th key={`connector-solo-${group.columns[0].id}`} p={0} style={{ border: "none" }} />
                  )
                )}
              </Table.Tr>
            )}
            <Table.Tr>
              <Table.Th
                style={{
                  minWidth: 140,
                  position: "sticky",
                  left: 0,
                  zIndex: 2,
                  background: "var(--mantine-color-body)",
                }}
              >
                Arrangement
              </Table.Th>
              {displayGroups.map((group) => (
                <Fragment key={group.kind === "merge" ? `h-${group.baseId}` : `h-${group.columns[0].id}`}>
                  {renderHeaderCells(group)}
                </Fragment>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {matrix.arrangements.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={flatColumns.length + 1}>
                  <Text size="sm" c="dimmed">
                    No arrangements in this ensemble.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              matrix.arrangements.map((arr) => {
                const rowConflict = conflictArrangementIds.includes(arr.id);
                return (
                  <Table.Tr
                    key={arr.id}
                    style={
                      rowConflict
                        ? { backgroundColor: "var(--mantine-color-red-0)" }
                        : undefined
                    }
                  >
                    <Table.Td
                      style={{
                        position: "sticky",
                        left: 0,
                        background: rowConflict
                          ? "var(--mantine-color-red-0)"
                          : "var(--mantine-color-body)",
                        zIndex: 1,
                      }}
                    >
                      <Text size="sm" fw={500}>
                        {arr.mvt_no ? `${arr.mvt_no}. ` : ""}
                        {arr.title}
                      </Text>
                    </Table.Td>
                    {displayGroups.map((group) => (
                      <Fragment key={group.kind === "merge" ? `b-${arr.id}-${group.baseId}` : `b-${arr.id}-${group.columns[0].id}`}>
                        {renderBodyCells(arr.id, group)}
                      </Fragment>
                    ))}
                  </Table.Tr>
                );
              })
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      {isAdmin && (
        <Group justify="flex-end">
          <Button variant="light" size="sm" onClick={() => reload()} disabled={saving}>
            Reset
          </Button>
          <Button size="sm" onClick={handleSave} loading={saving} disabled={!hasChanges}>
            Save changes
          </Button>
        </Group>
      )}
    </Stack>
  );
}
