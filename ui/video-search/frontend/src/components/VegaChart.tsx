import { Component, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { VegaEmbed } from "react-vega";

type Props = {
  spec: Record<string, unknown>;
};

class ChartErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.warn("VegaChart render error:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="text-[11px] text-muted-foreground italic px-3 py-2 border border-dashed border-border rounded">
          (chart unavailable)
        </div>
      );
    }
    return this.props.children;
  }
}

// Vega-Lite responsive sizing. The default `autosize:"pad"` expands the view
// past the specified width to fit axes/legends, which produces a horizontal
// scrollbar in narrow chat bubbles. We override to `fit-x` (width is a hard
// cap that includes axes/legends) and pass an explicit measured width from a
// ResizeObserver — `width:"container"` in the spec is unreliable through
// react-vega's wrapper because vega-embed's parent-width detection doesn't
// always find an explicit width on the wrapping element.
//
// `fit` modes only work on single-view or layer specs (NOT facet/concat/
// repeat) — composed specs fall back to the spec's own width.
//
// NNG flags horizontal scroll as a hard antipattern for content the user
// asked for, so we also hard-clip the container with overflow-hidden as a
// backstop in case anything still tries to spill.
const COMPOSED_SPEC_KEYS = ["facet", "hconcat", "vconcat", "concat", "repeat"];
const FALLBACK_WIDTH = 320;
const CHART_HEIGHT = 240;
// Inner padding around the chart (p-2 = 8px each side) plus a small safety
// margin so vega never lands exactly on the container edge.
const CONTAINER_PADDING_PX = 20;

function isComposedSpec(spec: Record<string, unknown>): boolean {
  return COMPOSED_SPEC_KEYS.some((key) => key in spec);
}

function makeResponsiveSpec(
  spec: Record<string, unknown>,
  plotWidth: number,
): Record<string, unknown> {
  if (isComposedSpec(spec)) return spec;

  // Roughly one legend column per 120px of available width — keeps a 7-8
  // category legend wrapping to 2-3 rows under the chart at 400px, more at
  // 640px. Bottom-oriented horizontal legends free the width axis for the
  // plot, per vega-lite docs (default orient is "right" which steals width).
  const columns = Math.max(2, Math.floor(plotWidth / 120));
  const existingConfig = (spec.config as Record<string, unknown>) ?? {};
  const existingLegend = (existingConfig.legend as Record<string, unknown>) ?? {};

  return {
    ...spec,
    width: plotWidth,
    height: CHART_HEIGHT,
    autosize: { type: "fit-x", contains: "padding" },
    config: {
      ...existingConfig,
      legend: {
        ...existingLegend,
        orient: "bottom",
        direction: "horizontal",
        columns,
      },
    },
  };
}

export default function VegaChart({ spec }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(FALLBACK_WIDTH);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (w > 0) setContainerWidth(w);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Snap to 20px buckets to avoid re-rendering vega on every pixel of resize.
  const plotWidth = Math.max(
    160,
    Math.floor((containerWidth - CONTAINER_PADDING_PX) / 20) * 20,
  );
  const responsiveSpec = useMemo(
    () => makeResponsiveSpec(spec, plotWidth),
    [spec, plotWidth],
  );

  return (
    <ChartErrorBoundary>
      <div
        ref={containerRef}
        className="w-full overflow-hidden bg-background rounded border border-border p-2"
      >
        <VegaEmbed
          spec={responsiveSpec as Parameters<typeof VegaEmbed>[0]["spec"]}
          options={{
            actions: false,
            renderer: "canvas",
          }}
        />
      </div>
    </ChartErrorBoundary>
  );
}
