import { describe, expect, it } from "vitest";
import { shouldUseFixtures } from "./api";

describe("dashboard fixture mode", () => {
  it("enables fixtures only for an explicit true value", () => {
    expect(shouldUseFixtures("true")).toBe(true);
    expect(shouldUseFixtures("TRUE")).toBe(true);
    expect(shouldUseFixtures("false")).toBe(false);
    expect(shouldUseFixtures(undefined)).toBe(false);
  });
});
