import { describe, expect, it } from "vitest";

import {
  type InboxSession,
  clearInboxSession,
  formatRemainingTime,
  loadInboxSession,
  saveInboxSession,
} from "./inbox-session";

class MemoryStorage implements Storage {
  private readonly values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  key(index: number) {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string) {
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
}

const session: InboxSession = {
  id: "71588d0b-3520-4d2d-b041-3783a4516585",
  address: "private@example.test",
  token: "possession-token",
  expiresAt: "2026-08-27T20:00:00.000Z",
};

describe("inbox session", () => {
  it("round-trips only through session storage", () => {
    const storage = new MemoryStorage();
    saveInboxSession(session, storage);
    expect(loadInboxSession(storage)).toEqual(session);
  });

  it("clears corrupt browser state", () => {
    const storage = new MemoryStorage();
    storage.setItem("projectemail.inbox.v1", "not-json");
    expect(loadInboxSession(storage)).toBeNull();
    expect(storage.length).toBe(0);
  });

  it("clears the active inbox on request", () => {
    const storage = new MemoryStorage();
    saveInboxSession(session, storage);
    clearInboxSession(storage);
    expect(loadInboxSession(storage)).toBeNull();
  });
});

describe("expiry presentation", () => {
  it("formats a stable mm:ss countdown", () => {
    expect(formatRemainingTime("2026-08-27T20:01:05.000Z", Date.parse(session.expiresAt))).toBe(
      "1:05",
    );
  });

  it("never displays a negative duration", () => {
    expect(formatRemainingTime(session.expiresAt, Date.parse(session.expiresAt) + 10_000)).toBe(
      "0:00",
    );
  });
});
