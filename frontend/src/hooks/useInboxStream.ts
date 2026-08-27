"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Subscribes to an inbox's live message stream over Server-Sent Events.
 *
 * SSE rather than WebSockets because the flow is entirely server -> client, and
 * `EventSource` gives us automatic reconnection with no client library.
 * See docs/adr/0002-sse-over-websockets.md.
 */

export interface MessageEnvelope {
  id: string;
  sender: string;
  subject: string;
  receivedAt: string;
  /** Surfaced by the backend so the user rarely needs to open the message at all. */
  otp: string | null;
  hasAttachments: boolean;
}

type Status = "connecting" | "open" | "closed";

export function useInboxStream(inboxId: string | null, token: string | null) {
  const [messages, setMessages] = useState<MessageEnvelope[]>([]);
  const [status, setStatus] = useState<Status>("connecting");
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!inboxId || !token) return;

    const url = new URL(`/api/v1/inbox/${inboxId}/stream`, process.env.NEXT_PUBLIC_API_URL);
    url.searchParams.set("token", token);

    const source = new EventSource(url.toString());
    sourceRef.current = source;

    source.onopen = () => setStatus("open");

    source.onmessage = (event: MessageEvent<string>) => {
      const envelope = JSON.parse(event.data) as MessageEnvelope;
      // Prepend, and guard against duplicates on reconnect — EventSource replays
      // from Last-Event-ID, so the same message can legitimately arrive twice.
      setMessages((current) =>
        current.some((m) => m.id === envelope.id) ? current : [envelope, ...current],
      );
    };

    // The browser reconnects on its own; surface the state rather than tearing down.
    source.onerror = () => setStatus("connecting");

    return () => {
      source.close();
      setStatus("closed");
    };
  }, [inboxId, token]);

  return { messages, status };
}
