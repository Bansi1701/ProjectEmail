import type { InboxSession } from "@/lib/inbox-session";

interface InboxCreatedResponse {
  id: string;
  address: string;
  token: string;
  expires_at: string;
}

interface MessageSummaryResponse {
  id: string;
  sender: string;
  subject: string;
  otp: string | null;
  verification_link: string | null;
  received_at: string;
}

export interface InboxMessage {
  id: string;
  sender: string;
  subject: string;
  otp: string | null;
  verificationLink: string | null;
  receivedAt: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function apiUrl(path: string): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!configured || configured.includes("api.invalid")) {
    throw new ApiError("Inbox service is not connected yet. Please try again shortly.");
  }
  return new URL(path.replace(/^\//, ""), `${configured.replace(/\/$/, "")}/`).toString();
}

async function responseError(response: Response): Promise<ApiError> {
  if (response.status === 503) {
    return new ApiError("No receiving domain is available yet. Please try again shortly.", 503);
  }
  if (response.status === 429) {
    return new ApiError("Too many requests. Wait a moment and try again.", 429);
  }
  return new ApiError("ProjectEmail could not complete that request.", response.status);
}

function isInboxCreated(value: unknown): value is InboxCreatedResponse {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.address === "string" &&
    typeof candidate.token === "string" &&
    typeof candidate.expires_at === "string"
  );
}

function isMessageSummary(value: unknown): value is MessageSummaryResponse {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.sender === "string" &&
    typeof candidate.subject === "string" &&
    (typeof candidate.otp === "string" || candidate.otp === null) &&
    (typeof candidate.verification_link === "string" || candidate.verification_link === null) &&
    typeof candidate.received_at === "string"
  );
}

export async function createInbox(): Promise<InboxSession> {
  const response = await fetch(apiUrl("/api/v1/inbox"), {
    method: "POST",
    cache: "no-store",
    credentials: "omit",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw await responseError(response);

  const body: unknown = await response.json();
  if (!isInboxCreated(body)) throw new ApiError("The inbox service returned an invalid response.");
  return {
    id: body.id,
    address: body.address,
    token: body.token,
    expiresAt: body.expires_at,
  };
}

export async function listMessages(session: InboxSession): Promise<InboxMessage[]> {
  const url = new URL(apiUrl(`/api/v1/inbox/${encodeURIComponent(session.id)}/messages`));
  url.searchParams.set("token", session.token);
  const response = await fetch(url, { cache: "no-store", credentials: "omit" });
  if (!response.ok) throw await responseError(response);

  const body: unknown = await response.json();
  if (!Array.isArray(body) || !body.every(isMessageSummary)) {
    throw new ApiError("The inbox service returned an invalid message list.");
  }
  return body.map((message) => ({
    id: message.id,
    sender: message.sender,
    subject: message.subject,
    otp: message.otp,
    verificationLink: message.verification_link,
    receivedAt: message.received_at,
  }));
}

export async function deleteInbox(session: InboxSession): Promise<void> {
  const url = new URL(apiUrl(`/api/v1/inbox/${encodeURIComponent(session.id)}`));
  url.searchParams.set("token", session.token);
  const response = await fetch(url, { method: "DELETE", cache: "no-store", credentials: "omit" });
  if (!response.ok && response.status !== 404) throw await responseError(response);
}
