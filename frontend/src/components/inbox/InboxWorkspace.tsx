"use client";

import { Check, Clock3, Copy, Inbox, LoaderCircle, ShieldCheck, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteHeader } from "@/components/site/SiteHeader";
import { useInboxStream } from "@/hooks/useInboxStream";
import { deleteInbox } from "@/lib/api";
import {
  type InboxSession,
  clearInboxSession,
  formatRemainingTime,
  loadInboxSession,
} from "@/lib/inbox-session";

export function InboxWorkspace() {
  const router = useRouter();
  const [session, setSession] = useState<InboxSession | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [copied, setCopied] = useState<string | null>(null);
  const [copyError, setCopyError] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(false);
  const { messages, status } = useInboxStream(session);

  useEffect(() => {
    setSession(loadInboxSession());
    setHydrated(true);
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  async function copyText(value: string, key: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopyError(false);
      setCopied(key);
      window.setTimeout(() => setCopied((current) => (current === key ? null : current)), 1600);
    } catch {
      setCopyError(true);
    }
  }

  async function eraseInbox() {
    if (
      !session ||
      !window.confirm("Delete this inbox and every message now? This cannot be undone.")
    ) {
      return;
    }
    setDeleting(true);
    setDeleteError(false);
    try {
      await deleteInbox(session);
      clearInboxSession();
      router.replace("/");
    } catch {
      setDeleteError(true);
    } finally {
      setDeleting(false);
    }
  }

  function startAgain() {
    clearInboxSession();
    router.replace("/");
  }

  if (!hydrated) {
    return (
      <main className="inbox-loading" aria-live="polite">
        <LoaderCircle className="spin" aria-hidden="true" />
        Restoring your private inbox…
      </main>
    );
  }

  if (!session) {
    return (
      <>
        <SiteHeader compact />
        <main className="missing-session" id="main-content">
          <Inbox aria-hidden="true" />
          <p className="eyebrow">No active inbox</p>
          <h1>Create an inbox to start receiving mail.</h1>
          <p>ProjectEmail keeps the possession token in this browser tab only.</p>
          <Link className="button button--primary" href="/">
            Create free inbox
          </Link>
        </main>
        <SiteFooter />
      </>
    );
  }

  const expired = Date.parse(session.expiresAt) <= now;
  const connectionLabel =
    status === "open" ? "Live" : status === "connecting" ? "Reconnecting" : "Closed";

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to inbox
      </a>
      <SiteHeader compact />
      <main className="inbox-page" id="main-content">
        <section className="inbox-toolbar" aria-labelledby="inbox-title">
          <div>
            <p className="eyebrow">ProjectEmail / Live inbox</p>
            <h1 id="inbox-title">Your temporary inbox</h1>
          </div>
          <div className="inbox-toolbar__status" aria-live="polite">
            <span className={`connection-dot connection-dot--${status}`} aria-hidden="true" />
            {expired ? "Expired" : connectionLabel}
          </div>
        </section>

        <section className="address-card" aria-label="Temporary address">
          <div>
            <span className="field-label">Your address</span>
            <strong>{session.address}</strong>
          </div>
          <button
            className="button button--copy"
            type="button"
            onClick={() => copyText(session.address, "address")}
          >
            {copied === "address" ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
            {copied === "address" ? "Copied" : "Copy"}
          </button>
          <div
            className="expiry-pill"
            aria-label={`Expires in ${formatRemainingTime(session.expiresAt, now)}`}
          >
            <Clock3 aria-hidden="true" />
            {formatRemainingTime(session.expiresAt, now)} remaining
          </div>
          {copyError && (
            <p className="inbox-error" role="alert">
              Clipboard access was blocked. Select and copy the address manually.
            </p>
          )}
        </section>

        <div className="inbox-grid">
          <section className="message-list" aria-labelledby="messages-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Messages</p>
                <h2 id="messages-title">Inbox ({messages.length})</h2>
              </div>
              <span>Newest first</span>
            </div>

            {expired ? (
              <div className="inbox-state">
                <Clock3 aria-hidden="true" />
                <h3>This inbox has expired.</h3>
                <p>Its messages are no longer readable and are being permanently removed.</p>
                <button className="button button--primary" type="button" onClick={startAgain}>
                  Create another inbox
                </button>
              </div>
            ) : messages.length === 0 ? (
              <div className="inbox-state" aria-live="polite">
                <Inbox aria-hidden="true" />
                <h3>Waiting for mail</h3>
                <p>Use the address above. New messages will appear here automatically.</p>
                <span className="waiting-line">
                  <span className="status-dot" aria-hidden="true" />
                  {status === "open" ? "Connected and listening" : "Restoring live connection"}
                </span>
              </div>
            ) : (
              <ol className="messages">
                {messages.map((message) => (
                  <li className="message-card" key={message.id}>
                    <div className="message-card__meta">
                      <strong>{message.sender}</strong>
                      <time dateTime={message.receivedAt}>
                        {new Date(message.receivedAt).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </time>
                    </div>
                    <h3>{message.subject || "No subject"}</h3>
                    {message.otp && (
                      <div className="otp-card">
                        <div>
                          <span>Verification code</span>
                          <strong>{message.otp}</strong>
                        </div>
                        <button
                          className="button button--copy"
                          type="button"
                          onClick={() => copyText(message.otp ?? "", `otp-${message.id}`)}
                        >
                          {copied === `otp-${message.id}` ? (
                            <Check aria-hidden="true" />
                          ) : (
                            <Copy aria-hidden="true" />
                          )}
                          {copied === `otp-${message.id}` ? "Copied" : "Copy code"}
                        </button>
                      </div>
                    )}
                    {message.verificationLink && (
                      <p className="protected-link">
                        Verification link protected until the warning screen is ready.
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </section>

          <aside className="inbox-safety" aria-labelledby="safety-title">
            <ShieldCheck aria-hidden="true" />
            <p className="eyebrow">Private by design</p>
            <h2 id="safety-title">This inbox leaves very little behind.</h2>
            <ul>
              <li>No account or recovery profile</li>
              <li>Full HTML stays gated until isolation is complete</li>
              <li>Inbound only—ProjectEmail cannot send mail</li>
              <li>Messages disappear when the inbox expires</li>
            </ul>
            <button
              className="delete-button"
              type="button"
              onClick={eraseInbox}
              disabled={deleting}
            >
              <Trash2 aria-hidden="true" />
              {deleting ? "Deleting…" : "Delete inbox now"}
            </button>
            {deleteError && (
              <p className="inbox-error" role="alert">
                ProjectEmail could not delete this inbox. Try again in a moment.
              </p>
            )}
          </aside>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
