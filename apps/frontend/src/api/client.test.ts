import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { getCsrfToken } from "./client";

describe("getCsrfToken", () => {
  const originalCookie = document.cookie;

  beforeEach(() => {
    document.cookie = "";
  });

  afterEach(() => {
    document.cookie = originalCookie;
  });

  it("returns null when csrftoken cookie is absent", () => {
    expect(getCsrfToken()).toBeNull();
  });

  it("parses csrftoken from document.cookie", () => {
    document.cookie = "csrftoken=abc123; path=/";
    expect(getCsrfToken()).toBe("abc123");
  });
});
