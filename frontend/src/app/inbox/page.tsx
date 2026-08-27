import type { Metadata } from "next";

import { InboxWorkspace } from "@/components/inbox/InboxWorkspace";

export const metadata: Metadata = {
  title: "Your temporary inbox",
  description: "Private ProjectEmail inbox session.",
  robots: { index: false, follow: false, noarchive: true, nocache: true },
  referrer: "no-referrer",
};

export default function InboxPage() {
  return <InboxWorkspace />;
}
