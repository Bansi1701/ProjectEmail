"use client";

import { useEffect, useRef } from "react";

/**
 * An ad slot that reserves its dimensions BEFORE the ad loads.
 *
 * This is not a style preference. Cumulative Layout Shift affects both SEO rank and
 * advertiser bid quality, and this product's entire revenue is programmatic advertising.
 * An ad that reflows content costs money twice. See CLAUDE.md Rule 5.
 */

interface AdSlotProps {
  slotId: string;
  width: number;
  height: number;
  /** Refresh cadence in seconds. Gated on viewability + tab focus. Phase 3. */
  refreshSeconds?: number;
}

export function AdSlot({ slotId, width, height, refreshSeconds }: AdSlotProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!refreshSeconds || !ref.current) return;

    const element = ref.current;
    let visible = false;

    // Refresh only while the slot is genuinely on screen AND the tab is focused.
    // Refreshing a slot nobody is looking at inflates impressions without viewability
    // and is what gets publishers demonetized.
    const observer = new IntersectionObserver(
      ([entry]) => {
        visible = (entry?.intersectionRatio ?? 0) > 0.5;
      },
      { threshold: [0, 0.5, 1] },
    );
    observer.observe(element);

    const timer = setInterval(() => {
      if (visible && document.visibilityState === "visible") {
        // TODO(Phase 3): googletag.pubads().refresh([slot])
      }
    }, refreshSeconds * 1000);

    return () => {
      observer.disconnect();
      clearInterval(timer);
    };
  }, [refreshSeconds]);

  return (
    <div
      ref={ref}
      data-slot-id={slotId}
      // Fixed dimensions reserved up front — this is the whole point of the component.
      style={{ width, height, minWidth: width, minHeight: height }}
      className="flex items-center justify-center overflow-hidden bg-neutral-100 dark:bg-neutral-900"
      aria-hidden="true"
    />
  );
}
