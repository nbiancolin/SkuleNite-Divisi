import { describe, expect, it } from "vitest";
import { parseVersionIdParam } from "./ScoreReviewPage";

describe("parseVersionIdParam", () => {
  it("parses valid positive integer ids", () => {
    expect(parseVersionIdParam("123")).toBe(123);
  });

  it("returns null for empty, non-numeric, or non-positive values", () => {
    expect(parseVersionIdParam(null)).toBeNull();
    expect(parseVersionIdParam("")).toBeNull();
    expect(parseVersionIdParam("abc")).toBeNull();
    expect(parseVersionIdParam("-5")).toBeNull();
    expect(parseVersionIdParam("0")).toBeNull();
  });
});
