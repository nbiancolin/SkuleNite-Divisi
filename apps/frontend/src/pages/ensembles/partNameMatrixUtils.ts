import type {
  PartNameMatrixCell,
  PartNameMatrixColumn,
} from "../../services/apiService";

export type MergeLinks = Record<number, number>;

export type DisplayGroup =
  | { kind: "standalone"; columns: PartNameMatrixColumn[] }
  | { kind: "merge"; baseId: number; columns: PartNameMatrixColumn[] };

export function getBaseId(columnId: number, mergeLinks: MergeLinks): number {
  return mergeLinks[columnId] ?? columnId;
}

export function getGroupMemberIds(baseId: number, mergeLinks: MergeLinks): number[] {
  return Object.entries(mergeLinks)
    .filter(([, base]) => base === baseId)
    .map(([memberId]) => Number(memberId));
}

export function getPendingMergeIds(baseId: number, mergeLinks: MergeLinks): number[] {
  return [baseId, ...getGroupMemberIds(baseId, mergeLinks)];
}

export function buildDisplayGroups(
  columns: PartNameMatrixColumn[],
  mergeLinks: MergeLinks
): DisplayGroup[] {
  const memberIds = new Set(Object.keys(mergeLinks).map(Number));
  const membersByBase = new Map<number, number[]>();

  for (const [memberIdStr, baseId] of Object.entries(mergeLinks)) {
    const memberId = Number(memberIdStr);
    if (!membersByBase.has(baseId)) membersByBase.set(baseId, []);
    membersByBase.get(baseId)!.push(memberId);
  }

  const columnIndex = new Map(columns.map((c, i) => [c.id, i]));
  const sortByColumnOrder = (a: number, b: number) =>
    (columnIndex.get(a) ?? 0) - (columnIndex.get(b) ?? 0);

  const groups: DisplayGroup[] = [];

  for (const col of columns) {
    if (memberIds.has(col.id)) continue;

    const memberIdsForBase = (membersByBase.get(col.id) ?? []).sort(sortByColumnOrder);
    const memberCols = memberIdsForBase
      .map((id) => columns.find((c) => c.id === id))
      .filter((c): c is PartNameMatrixColumn => c != null);

    if (memberCols.length > 0) {
      groups.push({ kind: "merge", baseId: col.id, columns: [col, ...memberCols] });
    } else {
      groups.push({ kind: "standalone", columns: [col] });
    }
  }

  return groups;
}

export function linkColumnToBase(
  sourceId: number,
  targetBaseId: number,
  mergeLinks: MergeLinks
): MergeLinks {
  if (sourceId === targetBaseId) return mergeLinks;

  const next: MergeLinks = { ...mergeLinks };
  const sourceBase = getBaseId(sourceId, next);
  const sourceMembers = getGroupMemberIds(sourceBase, next);

  for (const memberId of sourceMembers) {
    next[memberId] = targetBaseId;
  }

  if (sourceId !== sourceBase) {
    delete next[sourceId];
  }

  next[sourceId] = targetBaseId;

  return next;
}

export function unlinkColumn(memberId: number, mergeLinks: MergeLinks): MergeLinks {
  const next = { ...mergeLinks };
  delete next[memberId];
  return next;
}

export function pairsConflict(selectedIds: number[], mergeConflicts: [number, number][]) {
  const selected = new Set(selectedIds);
  return mergeConflicts.some(([a, b]) => selected.has(a) && selected.has(b));
}

/** Arrangements where more than one of the given part names has a part (latest version). */
export function getConflictingArrangementIds(
  partNameIds: number[],
  cells: PartNameMatrixCell[]
): number[] {
  if (partNameIds.length < 2) return [];

  const idSet = new Set(partNameIds);
  const partNamesPerArrangement = new Map<number, Set<number>>();

  for (const cell of cells) {
    if (!idSet.has(cell.part_name_id)) continue;
    let parts = partNamesPerArrangement.get(cell.arrangement_id);
    if (!parts) {
      parts = new Set();
      partNamesPerArrangement.set(cell.arrangement_id, parts);
    }
    parts.add(cell.part_name_id);
  }

  const conflicts: number[] = [];
  for (const [arrangementId, parts] of partNamesPerArrangement) {
    const overlapCount = partNameIds.filter((id) => parts.has(id)).length;
    if (overlapCount >= 2) conflicts.push(arrangementId);
  }
  return conflicts;
}

export function getIdsAfterLink(
  sourceId: number,
  targetBaseId: number,
  mergeLinks: MergeLinks
): number[] {
  return getPendingMergeIds(targetBaseId, linkColumnToBase(sourceId, targetBaseId, mergeLinks));
}

export function canLinkColumns(
  sourceId: number,
  targetColumnId: number,
  mergeLinks: MergeLinks,
  cells: PartNameMatrixCell[],
  mergeConflicts: [number, number][]
): { ok: true } | { ok: false; reason: string; arrangementIds?: number[] } {
  const targetBase = getBaseId(targetColumnId, mergeLinks);
  const sourceBase = getBaseId(sourceId, mergeLinks);

  if (sourceId === targetBase) {
    return { ok: false, reason: "Cannot merge a part name into itself." };
  }

  const sourceMembers = getGroupMemberIds(sourceBase, mergeLinks);
  if (sourceMembers.includes(targetBase)) {
    return { ok: false, reason: "That part is already linked to this base." };
  }

  if (targetBase === sourceBase) {
    return { ok: false, reason: "That part is already the base for this group." };
  }

  const mergedIds = getIdsAfterLink(sourceId, targetBase, mergeLinks);

  if (pairsConflict(mergedIds, mergeConflicts)) {
    return {
      ok: false,
      reason:
        "Cannot merge: these part names both have parts in the same arrangement version.",
    };
  }

  const conflictArrangementIds = getConflictingArrangementIds(mergedIds, cells);
  if (conflictArrangementIds.length > 0) {
    return {
      ok: false,
      reason:
        "Cannot merge: these part names both have parts in the same arrangement version.",
      arrangementIds: conflictArrangementIds,
    };
  }

  return { ok: true };
}

export function cellKey(arrangementId: number, partNameId: number) {
  return `${arrangementId}-${partNameId}`;
}

export function groupCellBorderClass(
  group: DisplayGroup,
  columnId: number
): string | undefined {
  if (group.kind !== "merge" || group.columns.length < 2) return undefined;
  const idx = group.columns.findIndex((c) => c.id === columnId);
  if (idx < 0) return undefined;
  if (idx === 0) return "merge-group-start";
  if (idx === group.columns.length - 1) return "merge-group-end";
  return "merge-group-middle";
}
