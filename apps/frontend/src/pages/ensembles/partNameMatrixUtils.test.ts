import { describe, expect, it } from "vitest";
import {
  buildDisplayGroups,
  canLinkColumns,
  getConflictingArrangementIds,
  linkColumnToBase,
  unlinkColumn,
} from "./partNameMatrixUtils";
import type { PartNameMatrixColumn } from "../../services/apiService";

const columns: PartNameMatrixColumn[] = [
  { id: 1, display_name: "Flute", order: 0 },
  { id: 2, display_name: "Flute I", order: 1 },
  { id: 3, display_name: "Clarinet", order: 2 },
];

describe("partNameMatrixUtils", () => {
  it("groups linked columns adjacent to base", () => {
    const links = { 2: 1 };
    const groups = buildDisplayGroups(columns, links);
    expect(groups).toHaveLength(2);
    expect(groups[0]).toMatchObject({ kind: "merge", baseId: 1 });
    expect(groups[0].kind === "merge" && groups[0].columns.map((c) => c.id)).toEqual([
      1, 2,
    ]);
    expect(groups[1].kind).toBe("standalone");
  });

  it("links a column onto a base and re-parents former members", () => {
    const links = linkColumnToBase(3, 1, { 2: 1 });
    expect(links).toEqual({ 2: 1, 3: 1 });
  });

  it("unlinks a member column", () => {
    const links = unlinkColumn(2, { 2: 1 });
    expect(links).toEqual({});
  });

  it("detects conflicting arrangements when both parts exist on same row", () => {
    const cells = [
      { arrangement_id: 10, part_name_id: 1, part_asset_id: 100 },
      { arrangement_id: 10, part_name_id: 2, part_asset_id: 101 },
    ];
    expect(getConflictingArrangementIds([1, 2], cells)).toEqual([10]);
    expect(getConflictingArrangementIds([1], cells)).toEqual([]);
  });

  it("rejects link when merge would duplicate parts in same version", () => {
    const cells = [
      { arrangement_id: 10, part_name_id: 1, part_asset_id: 100 },
      { arrangement_id: 10, part_name_id: 2, part_asset_id: 101 },
    ];
    const result = canLinkColumns(2, 1, {}, cells, []);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toContain("same arrangement version");
    }
  });

  it("allows link when parts are on different arrangements", () => {
    const cells = [
      { arrangement_id: 10, part_name_id: 1, part_asset_id: 100 },
      { arrangement_id: 11, part_name_id: 2, part_asset_id: 101 },
    ];
    expect(canLinkColumns(2, 1, {}, cells, [])).toEqual({ ok: true });
  });
});
