export interface InboxSession {
  id: string;
  address: string;
  token: string;
  expiresAt: string;
}

const STORAGE_KEY = "projectemail.inbox.v1";

function getStorage(storage?: Storage): Storage | null {
  if (storage) return storage;
  if (typeof window === "undefined") return null;
  return window.sessionStorage;
}

function isInboxSession(value: unknown): value is InboxSession {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.address === "string" &&
    typeof candidate.token === "string" &&
    typeof candidate.expiresAt === "string" &&
    Number.isFinite(Date.parse(candidate.expiresAt))
  );
}

export function saveInboxSession(session: InboxSession, storage?: Storage): void {
  getStorage(storage)?.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function loadInboxSession(storage?: Storage): InboxSession | null {
  const target = getStorage(storage);
  const raw = target?.getItem(STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed: unknown = JSON.parse(raw);
    if (isInboxSession(parsed)) return parsed;
  } catch {
    // Corrupt browser state is disposable. Remove it and return to a clean start.
  }

  target?.removeItem(STORAGE_KEY);
  return null;
}

export function clearInboxSession(storage?: Storage): void {
  getStorage(storage)?.removeItem(STORAGE_KEY);
}

export function formatRemainingTime(expiresAt: string, now = Date.now()): string {
  const remainingSeconds = Math.max(0, Math.ceil((Date.parse(expiresAt) - now) / 1000));
  const minutes = Math.floor(remainingSeconds / 60);
  const seconds = remainingSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
