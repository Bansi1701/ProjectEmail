/**
 * Renders an email message.
 *
 * The body is NEVER injected into this document. It is loaded from a separate origin
 * inside a sandboxed iframe, because email HTML is attacker-controlled input.
 *
 * Do not add `allow-scripts` and `allow-same-origin` together — combined, they let the
 * framed document reach into this page, read session state and tamper with ad scripts,
 * which defeats the sandbox entirely. See docs/SECURITY.md section 1.
 */

interface MessageViewerProps {
  messageId: string;
  subject: string;
  sender: string;
}

export function MessageViewer({ messageId, subject, sender }: MessageViewerProps) {
  const sandboxOrigin = process.env.NEXT_PUBLIC_SANDBOX_ORIGIN;

  return (
    <article className="flex h-full flex-col">
      <header className="border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
        <h2 className="font-semibold text-lg">{subject}</h2>
        <p className="text-neutral-500 text-sm">{sender}</p>
      </header>

      <iframe
        title={subject}
        src={`${sandboxOrigin}/msg/${messageId}`}
        // NO allow-same-origin. NO allow-scripts.
        sandbox="allow-popups allow-popups-to-escape-sandbox"
        referrerPolicy="no-referrer"
        className="min-h-0 flex-1 border-0 bg-white"
      />
    </article>
  );
}
