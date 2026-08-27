import {
  ArrowRight,
  Ban,
  CheckCircle2,
  Clock3,
  Code2,
  Copy,
  EyeOff,
  Inbox,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import type { Metadata } from "next";

import { InboxGenerator } from "@/components/inbox/InboxGenerator";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteHeader } from "@/components/site/SiteHeader";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://bansi1701.github.io/ProjectEmail/";

const structuredData = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "ProjectEmail",
  applicationCategory: "UtilitiesApplication",
  operatingSystem: "Any",
  url: siteUrl,
  description:
    "Create a temporary inbound-only email address to receive verification codes without opening an account.",
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
};

export const metadata: Metadata = {
  alternates: { canonical: siteUrl },
};

const trustItems = [
  { icon: LockKeyhole, label: "No signup" },
  { icon: Clock3, label: "10–60 minute expiry" },
  { icon: Ban, label: "Inbound only" },
  { icon: EyeOff, label: "HTML sanitized" },
];

const steps = [
  {
    number: "01",
    icon: Sparkles,
    title: "Create",
    body: "One click creates a random address and a private possession token in this browser tab.",
  },
  {
    number: "02",
    icon: Inbox,
    title: "Receive",
    body: "Keep the tab open. New mail appears through a live connection without manual refreshing.",
  },
  {
    number: "03",
    icon: Copy,
    title: "Copy and expire",
    body: "Verification codes are surfaced for one-tap copy, then the inbox and messages expire.",
  },
];

const faqs = [
  {
    question: "Is a temporary ProjectEmail inbox private?",
    answer:
      "Reading requires the possession token created with the inbox, not just its address. The token remains in this browser tab. Temporary email still should not be used for banking, healthcare, legal, or long-term account recovery.",
  },
  {
    question: "How long does an inbox last?",
    answer:
      "Each inbox displays its exact expiry countdown. The service supports a short 10–60 minute window and hides expired data immediately while physical deletion runs automatically.",
  },
  {
    question: "Can ProjectEmail send or forward email?",
    answer:
      "No. ProjectEmail is permanently inbound only. It has no reply, forwarding, or outbound email capability.",
  },
  {
    question: "Why might an email arrive late?",
    answer:
      "The sender and its mail provider control the first part of delivery. Keep the live inbox tab open, verify the exact address, and request a new code only after the sender’s normal retry window.",
  },
];

export default function HomePage() {
  return (
    <>
      <script type="application/ld+json">{JSON.stringify(structuredData)}</script>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <SiteHeader />

      <main id="main-content">
        <section className="hero">
          <div className="hero__glow" aria-hidden="true" />
          <div className="hero__content">
            <p className="eyebrow">
              <span className="eyebrow__line" aria-hidden="true" />
              Private inbox. Zero account.
            </p>
            <h1>Private email in one click.</h1>
            <p className="hero__lede">
              Receive a code. Copy it. Leave no account behind. ProjectEmail gives you a temporary,
              inbound-only inbox without asking who you are.
            </p>
            <a className="button button--primary button--hero" href="#generator">
              Create free inbox
              <ArrowRight aria-hidden="true" />
            </a>
            <p className="hero__microcopy">Free during private alpha · no signup · no password</p>
          </div>
          <div className="hero__tool">
            <InboxGenerator />
          </div>
        </section>

        <section className="trust-strip" aria-label="Product privacy commitments">
          {trustItems.map(({ icon: Icon, label }) => (
            <div key={label}>
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </div>
          ))}
        </section>

        <section className="section" id="how-it-works">
          <div className="section-intro">
            <p className="eyebrow">How it works</p>
            <h2>From blank tab to copied code in three steps.</h2>
            <p>
              ProjectEmail removes the account setup that slows down a single-use verification task.
            </p>
          </div>
          <div className="steps-grid">
            {steps.map(({ number, icon: Icon, title, body }) => (
              <article className="step-card" key={number}>
                <div className="step-card__top">
                  <span>{number}</span>
                  <Icon aria-hidden="true" />
                </div>
                <h3>{title}</h3>
                <p>{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="security-section" id="security">
          <div className="security-section__visual" aria-hidden="true">
            <div className="security-orbit security-orbit--outer" />
            <div className="security-orbit security-orbit--inner" />
            <ShieldCheck />
          </div>
          <div className="security-section__content">
            <p className="eyebrow eyebrow--light">Security before convenience</p>
            <h2>Email HTML is treated as hostile input.</h2>
            <p>
              Incoming HTML is sanitized before storage and kept out of the main application
              document. The full message viewer stays unavailable until separate-origin rendering,
              remote-image protection, and the link-warning screen are complete.
            </p>
            <ul className="check-list">
              <li>
                <CheckCircle2 aria-hidden="true" /> Random addresses with at least 64 bits of
                entropy
              </li>
              <li>
                <CheckCircle2 aria-hidden="true" /> Possession token required for every inbox read
              </li>
              <li>
                <CheckCircle2 aria-hidden="true" /> No message bodies in analytics or application
                logs
              </li>
            </ul>
          </div>
        </section>

        <section className="section developer-section" id="developers">
          <div className="developer-card">
            <div>
              <p className="eyebrow">Built for real testing</p>
              <h2>Fast enough for people. Predictable enough for QA.</h2>
              <p>
                The public API is being hardened around the same create, stream, read, and delete
                contract used by this site. Documentation and stable test examples arrive after the
                private-alpha reliability gate.
              </p>
            </div>
            <div className="code-sample" aria-label="Planned API flow example">
              <div className="code-sample__bar">
                <span /> <span /> <span />
                <small>API flow</small>
              </div>
              <pre>
                <code>
                  {
                    "POST /api/v1/inbox\nGET  /inbox/{id}/stream\nGET  /inbox/{id}/messages\nDELETE /inbox/{id}"
                  }
                </code>
              </pre>
            </div>
          </div>
          <div className="developer-points">
            <span>
              <Zap aria-hidden="true" /> Live SSE delivery
            </span>
            <span>
              <Code2 aria-hidden="true" /> OpenAPI contract
            </span>
            <span>
              <ShieldCheck aria-hidden="true" /> Inbound-only boundary
            </span>
          </div>
        </section>

        <section className="section faq-section">
          <div className="section-intro">
            <p className="eyebrow">Clear answers</p>
            <h2>What to know before using a temporary inbox.</h2>
          </div>
          <div className="faq-list">
            {faqs.map((faq) => (
              <details key={faq.question}>
                <summary>{faq.question}</summary>
                <p>{faq.answer}</p>
              </details>
            ))}
          </div>
        </section>
      </main>

      <SiteFooter />
    </>
  );
}
