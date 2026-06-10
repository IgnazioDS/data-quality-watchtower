import { describe, expect, it } from "vitest";
import { PROJECT, type ProjectSpec } from "./project";

describe("PROJECT", () => {
  it("has all required fields", () => {
    expect(PROJECT).toHaveProperty("slug");
    expect(PROJECT).toHaveProperty("name");
    expect(PROJECT).toHaveProperty("category");
    expect(PROJECT).toHaveProperty("track");
    expect(PROJECT).toHaveProperty("stage");
    expect(PROJECT).toHaveProperty("summary");
    expect(PROJECT).toHaveProperty("problem");
    expect(PROJECT).toHaveProperty("users");
    expect(PROJECT).toHaveProperty("stack");
    expect(PROJECT).toHaveProperty("why_now");
    expect(PROJECT).toHaveProperty("mvp");
    expect(PROJECT).toHaveProperty("github_url");
    expect(PROJECT).toHaveProperty("system_slug");
    expect(PROJECT).toHaveProperty("eleventh_url");
    expect(PROJECT).toHaveProperty("live_url");
    expect(PROJECT).toHaveProperty("fleet_url");
    expect(PROJECT).toHaveProperty("builder");
  });

  it("has correct slug identity", () => {
    expect(PROJECT.slug).toBe("data-quality-watchtower");
    expect(PROJECT.system_slug).toBe("data-quality-watchtower");
  });

  it("has non-empty strings for all required text fields", () => {
    expect(typeof PROJECT.name).toBe("string");
    expect(PROJECT.name.length).toBeGreaterThan(0);

    expect(typeof PROJECT.category).toBe("string");
    expect(PROJECT.category.length).toBeGreaterThan(0);

    expect(typeof PROJECT.summary).toBe("string");
    expect(PROJECT.summary.length).toBeGreaterThan(0);

    expect(typeof PROJECT.problem).toBe("string");
    expect(PROJECT.problem.length).toBeGreaterThan(0);

    expect(typeof PROJECT.users).toBe("string");
    expect(PROJECT.users.length).toBeGreaterThan(0);
  });

  it("has non-empty stack array", () => {
    expect(Array.isArray(PROJECT.stack)).toBe(true);
    expect(PROJECT.stack.length).toBeGreaterThan(0);
    PROJECT.stack.forEach((lang) => {
      expect(typeof lang).toBe("string");
      expect(lang.length).toBeGreaterThan(0);
    });
  });

  it("has non-empty mvp array", () => {
    expect(Array.isArray(PROJECT.mvp)).toBe(true);
    expect(PROJECT.mvp.length).toBeGreaterThan(0);
    PROJECT.mvp.forEach((item) => {
      expect(typeof item).toBe("string");
      expect(item.length).toBeGreaterThan(0);
    });
  });

  it("has valid URLs", () => {
    const urls = [
      PROJECT.github_url,
      PROJECT.eleventh_url,
      PROJECT.live_url,
      PROJECT.fleet_url,
    ];
    urls.forEach((url) => {
      expect(typeof url).toBe("string");
      expect(url).toMatch(/^https?:\/\//);
    });
  });

  it("confirms type safety", () => {
    const _test: ProjectSpec = PROJECT;
    expect(_test).toBeDefined();
  });
});
