import { describe, expect, it, vi } from "vitest";
import { listPages, shouldUseFixtures } from "./api";

describe("dashboard fixture mode", () => {
  it("enables fixtures only for an explicit true value", () => {
    expect(shouldUseFixtures("true")).toBe(true);
    expect(shouldUseFixtures("TRUE")).toBe(true);
    expect(shouldUseFixtures("false")).toBe(false);
    expect(shouldUseFixtures(undefined)).toBe(false);
  });
});

describe("concurrent API reads", () => {
  it("shares an in-flight page request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    try {
      const [first, second] = await Promise.all([listPages("workspace"), listPages("workspace")]);
      expect(first).toEqual([]);
      expect(second).toEqual([]);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
