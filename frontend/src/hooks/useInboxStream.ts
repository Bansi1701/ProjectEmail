"use client";

import { useEffect, useState } from "react";

import { type InboxMessage, apiUrl, listMessages } from "@/lib/api";
import type { InboxSession } from "@/lib/inbox-session";

/**
 * Subscribes to an inbox's live message stream over Server-Sent Events.
 *
 * SSE rather than WebSockets because the flow is entirely server -> client, and
 * `EventSource` gives us automatic reconnection with no client library.
 * See docs/adr/0002-sse-over-websockets.md.
 */

type Status = "connecting" | "open" | "closed";

function parseEnvelope(raw: string): InboxMessage | null {
  try {
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object") return null;
    const message = value as Record<string, unknown>;
    if (
      typeof message.id !== "string" ||
      typeof message.sender !== "string" ||
      typeof message.subject !== "string" ||
      (typeof message.otp !== "string" && message.otp !== null) ||
      (typeof message.verificationLink !== "string" && message.verificationLink !== null) ||
      typeof message.receivedAt !== "string"
    ) {
      return null;
    }
    return {
      id: message.id,
      sender: message.sender,
      subject: message.subject,
      otp: message.otp,
      verificationLink: message.verificationLink,
      receivedAt: message.receivedAt,
    };
  } catch {
    return null;
  }
}

export function useInboxStream(session: InboxSession | null) {
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [status, setStatus] = useState<Status>("connecting");

  useEffect(() => {
    if (!session) return;

    let active = true;
    setMessages([]);
    setStatus("connecting");

    void listMessages(session)
      .then((initial) => {
        if (active) setMessages(initial);
      })
      .catch(() => {
        // The live stream remains useful if the initial refresh fails temporarily.
      });

    let url: URL;
    try {
      url = new URL(apiUrl(`/api/v1/inbox/${encodeURIComponent(session.id)}/stream`));
    } catch {
      setStatus("closed");
      return () => {
        active = false;
      };
    }
    url.searchParams.set("token", session.token);

    const source = new EventSource(url.toString());

    source.onopen = () => setStatus("open");

    source.onmessage = (event: MessageEvent<string>) => {
      const envelope = parseEnvelope(event.data);
      if (!envelope) return;
      // Prepend, and guard against duplicates on reconnect — EventSource replays
      // from Last-Event-ID, so the same message can legitimately arrive twice.
      setMessages((current) =>
        current.some((m) => m.id === envelope.id) ? current : [envelope, ...current],
      );
    };

    // The browser reconnects on its own; surface the state rather than tearing down.
    source.onerror = () => setStatus("connecting");

    return () => {
      active = false;
      source.close();
      setStatus("closed");
    };
  }, [session]);

  return { messages, status };
}
