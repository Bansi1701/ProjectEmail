"use client";

import { ArrowRight, LoaderCircle, MailPlus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, createInbox } from "@/lib/api";
import { saveInboxSession } from "@/lib/inbox-session";

type GeneratorState = "idle" | "creating" | "error";

export function InboxGenerator() {
  const router = useRouter();
  const [state, setState] = useState<GeneratorState>("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    setState("creating");
    setError(null);
    try {
      const session = await createInbox();
      saveInboxSession(session);
      router.push("/inbox");
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "The inbox service could not be reached. Please try again.",
      );
      setState("error");
    }
  }

  const creating = state === "creating";

  return (
    <div className="generator" id="generator">
      <div className="generator__eyebrow">
        <span className="status-dot" aria-hidden="true" />
        Ready when you are
      </div>
      <h2>Your temporary address</h2>
      <p className="generator__description">
        One secure click creates a private inbox. No name, password, or recovery email.
      </p>
      <button
        className="button button--primary button--generator"
        type="button"
        onClick={handleCreate}
        disabled={creating}
      >
        {creating ? (
          <>
            <LoaderCircle className="spin" aria-hidden="true" />
            Creating securely…
          </>
        ) : (
          <>
            <MailPlus aria-hidden="true" />
            Generate address
            <ArrowRight aria-hidden="true" />
          </>
        )}
      </button>
      <p className="generator__hint">The address is the tool—there are no form fields.</p>
      <div className="generator__status" aria-live="polite" aria-atomic="true">
        {error && (
          <p role="alert">
            {error}{" "}
            <button type="button" onClick={handleCreate}>
              Try again
            </button>
          </p>
        )}
      </div>
    </div>
  );
}
