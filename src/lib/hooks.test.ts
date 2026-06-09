import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebounce, useMounted, useAnimatedNumber, useHotkey, usePolling } from "./hooks";

describe("useDebounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns the initial value immediately", () => {
    const { result } = renderHook(() => useDebounce("hello", 200));
    expect(result.current).toBe("hello");
  });

  it("updates only after the delay elapses", () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 200),
      { initialProps: { value: "first" } },
    );
    rerender({ value: "second" });
    expect(result.current).toBe("first");

    act(() => {
      vi.advanceTimersByTime(199);
    });
    expect(result.current).toBe("first");

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe("second");
  });
});

describe("useMounted", () => {
  it("returns true after mount", () => {
    const { result } = renderHook(() => useMounted());
    expect(result.current).toBe(true);
  });
});

describe("useAnimatedNumber", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts at 0", () => {
    const { result } = renderHook(() => useAnimatedNumber(100, 600));
    expect(result.current).toBe(0);
  });

  it("animates towards target over duration", () => {
    const { result } = renderHook(() => useAnimatedNumber(100, 600));

    // Advance partway through animation
    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Should have progressed but not reached target yet
    expect(result.current).toBeGreaterThan(0);
    expect(result.current).toBeLessThan(100);
  });

  it("handles target updates", () => {
    const { result, rerender } = renderHook(
      ({ target }) => useAnimatedNumber(target, 600),
      { initialProps: { target: 100 } }
    );

    act(() => {
      vi.advanceTimersByTime(300);
    });
    const firstValue = result.current;
    expect(firstValue).toBeGreaterThan(0);

    // Change target
    rerender({ target: 200 });

    // Animation should progress from current value
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toBeGreaterThan(firstValue);
  });

  it("uses easing for smooth animation", () => {
    const { result } = renderHook(() => useAnimatedNumber(100, 1000));

    const values: number[] = [];

    // Record values at different points
    for (let i = 0; i <= 4; i++) {
      act(() => {
        vi.advanceTimersByTime(200);
      });
      values.push(result.current);
    }

    // Each value should increase
    for (let i = 1; i < values.length; i++) {
      expect(values[i]).toBeGreaterThan(values[i - 1]);
    }
  });
});

describe("useHotkey", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("fires handler when key matches", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("Enter", handler));

    const event = new KeyboardEvent("keydown", { key: "Enter" });
    act(() => {
      window.dispatchEvent(event);
    });

    expect(handler).toHaveBeenCalledOnce();
  });

  it("ignores non-matching keys", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("Enter", handler));

    const event = new KeyboardEvent("keydown", { key: "Escape" });
    act(() => {
      window.dispatchEvent(event);
    });

    expect(handler).not.toHaveBeenCalled();
  });

  it("is case-insensitive", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("enter", handler));

    const event = new KeyboardEvent("keydown", { key: "ENTER" });
    act(() => {
      window.dispatchEvent(event);
    });

    expect(handler).toHaveBeenCalledOnce();
  });

  it("respects meta modifier", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("s", handler, { meta: true }));

    // Without meta key
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "s" }));
    });
    expect(handler).not.toHaveBeenCalled();

    // With meta key
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "s", metaKey: true }));
    });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("respects ctrl modifier", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("k", handler, { ctrl: true }));

    // Without ctrl key
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k" }));
    });
    expect(handler).not.toHaveBeenCalled();

    // With ctrl key
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
    });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("respects shift modifier", () => {
    const handler = vi.fn();
    renderHook(() => useHotkey("A", handler, { shift: true }));

    // Without shift key
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
    });
    expect(handler).not.toHaveBeenCalled();

    // With shift key
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "A", shiftKey: true }));
    });
    expect(handler).toHaveBeenCalledOnce();
  });

  it("detaches listener on unmount", () => {
    const handler = vi.fn();
    const { unmount } = renderHook(() => useHotkey("Enter", handler));

    unmount();

    const event = new KeyboardEvent("keydown", { key: "Enter" });
    act(() => {
      window.dispatchEvent(event);
    });

    expect(handler).not.toHaveBeenCalled();
  });

  it("updates handler reference without detaching", () => {
    const handler1 = vi.fn();
    const handler2 = vi.fn();
    const { rerender } = renderHook(
      ({ handler }) => useHotkey("Enter", handler),
      { initialProps: { handler: handler1 } }
    );

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });
    expect(handler1).toHaveBeenCalledOnce();

    rerender({ handler: handler2 });

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    });
    // handler1 should not be called again; handler2 should be called
    expect(handler1).toHaveBeenCalledOnce();
    expect(handler2).toHaveBeenCalledOnce();
  });
});

describe("usePolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("loads data on mount", async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: "test" });
    const { result } = renderHook(() => usePolling(fetcher, 1000));

    expect(result.current.loading).toBe(true);

    // Wait for the first fetch to complete
    await act(async () => {
      vi.runAllTimers();
    });

    expect(result.current.data).toEqual({ data: "test" });
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("captures fetch errors", async () => {
    const error = new Error("Fetch failed");
    const fetcher = vi.fn().mockRejectedValue(error);
    const { result } = renderHook(() => usePolling(fetcher, 1000));

    await act(async () => {
      vi.runAllTimers();
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeDefined();
    expect((result.current.error as Error).message).toContain("Fetch failed");
    expect(result.current.loading).toBe(false);
  });

  it("does not poll when disabled", async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: "test" });
    const { result } = renderHook(() => usePolling(fetcher, 1000, false));

    await act(async () => {
      vi.runAllTimers();
    });

    expect(result.current.loading).toBe(true);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("clears loading on successful fetch", async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: "test" });
    const { result } = renderHook(() => usePolling(fetcher, 1000));

    expect(result.current.loading).toBe(true);

    await act(async () => {
      vi.runAllTimers();
    });

    expect(result.current.loading).toBe(false);
  });

  it("supports manual refetch triggering", async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: "test" });
    const { result } = renderHook(() => usePolling(fetcher, 5000));

    // Initial fetch
    await act(async () => {
      vi.runAllTimers();
    });
    const initialCall = fetcher.mock.calls.length;

    // Trigger refetch
    act(() => {
      result.current.refetch();
    });

    // Advance to trigger the refetched call
    await act(async () => {
      vi.runAllTimers();
    });

    expect(fetcher.mock.calls.length).toBeGreaterThan(initialCall);
  });

  it("returns data, error, loading, and refetch", () => {
    const fetcher = vi.fn().mockResolvedValue({ data: "test" });
    const { result } = renderHook(() => usePolling(fetcher, 1000));

    expect(result.current).toHaveProperty("data");
    expect(result.current).toHaveProperty("error");
    expect(result.current).toHaveProperty("loading");
    expect(result.current).toHaveProperty("refetch");
    expect(typeof result.current.refetch).toBe("function");
  });
});
