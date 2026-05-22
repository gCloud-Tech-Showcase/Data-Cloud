import { Component, type ReactNode } from "react";
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

// react-vega v8 ships only VegaEmbed; vega-embed (underlying library) auto-
// routes to Vega vs Vega-Lite based on the spec's $schema URL.
//
// Sizing approach: pass width/height via vega-embed's EmbedOptions instead
// of mutating the spec. The spec mutation path (width:"container") was
// unreliable because CA emits Vega-Lite v4 specs and we run vega-lite v6,
// which changed how container sizing behaves. EmbedOptions.width/.height
// override the spec without triggering the v4-vs-v6 differences.
//
// 280px target fits inside the ~340px effective chat-bubble width (85% of
// the 400px chat panel minus padding/border).
const CHART_WIDTH = 280;
const CHART_HEIGHT = 260;

export default function VegaChart({ spec }: Props) {
  return (
    <ChartErrorBoundary>
      <div className="w-full bg-background rounded border border-border p-2">
        <VegaEmbed
          spec={spec as Parameters<typeof VegaEmbed>[0]["spec"]}
          options={{
            actions: false,
            renderer: "canvas",
            width: CHART_WIDTH,
            height: CHART_HEIGHT,
            // EmbedOptions.width controls the plot area only — legends
            // and axes add to the total width. Orienting the legend to
            // the bottom keeps horizontal width = plot width so the
            // chart fits the narrow chat bubble without overflow.
            config: {
              legend: { orient: "bottom" },
            },
          }}
        />
      </div>
    </ChartErrorBoundary>
  );
}
