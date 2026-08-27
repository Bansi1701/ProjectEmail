import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div>
          <Link className="wordmark wordmark--footer" href="/">
            <span className="wordmark__mark" aria-hidden="true">
              P
            </span>
            <span>ProjectEmail</span>
          </Link>
          <p>Temporary inboxes designed to expire, not follow you.</p>
        </div>
        <nav aria-label="Footer navigation">
          <Link href="/#how-it-works">How it works</Link>
          <Link href="/#security">Security</Link>
          <Link href="/#developers">Developers</Link>
          <a href="https://github.com/Bansi1701/ProjectEmail" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </div>
      <p className="site-footer__note">
        Inbound only. ProjectEmail cannot send, reply to, or forward email.
      </p>
    </footer>
  );
}
