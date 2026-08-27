import Link from "next/link";

interface SiteHeaderProps {
  compact?: boolean;
}

export function SiteHeader({ compact = false }: SiteHeaderProps) {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link className="wordmark" href="/" aria-label="ProjectEmail home">
          <span className="wordmark__mark" aria-hidden="true">
            P
          </span>
          <span>ProjectEmail</span>
        </Link>

        {!compact && (
          <nav className="site-nav" aria-label="Primary navigation">
            <a href="#how-it-works">How it works</a>
            <a href="#developers">Developers</a>
            <a href="#security">Security</a>
          </nav>
        )}

        <Link className="button button--small button--outline" href={compact ? "/" : "#generator"}>
          {compact ? "Home" : "Create inbox"}
        </Link>
      </div>
    </header>
  );
}
