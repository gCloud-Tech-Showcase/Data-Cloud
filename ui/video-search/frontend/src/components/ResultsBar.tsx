import { useState } from "react";
import { Link, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ResultsBarProps {
  totalResults: number;
  searchTime?: number;
  query?: string;
  sortBy: string;
  onSortChange: (sort: string) => void;
}

const SORT_OPTIONS = [
  { value: "title", label: "Title (A-Z)" },
  { value: "title-desc", label: "Title (Z-A)" },
  { value: "year-desc", label: "Newest first" },
  { value: "year-asc", label: "Oldest first" },
  { value: "relevance", label: "Relevance" },
];

export function ResultsBar({
  totalResults,
  searchTime,
  query,
  sortBy,
  onSortChange,
}: ResultsBarProps) {
  const [copied, setCopied] = useState(false);

  function handleCopyLink() {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const hasShareableState = query || window.location.search;

  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-3">
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{totalResults}</span>
          {" "}video{totalResults !== 1 ? "s" : ""}
          {query && !query.startsWith("similar:") && (
            <span> for &ldquo;{query}&rdquo;</span>
          )}
          {searchTime !== undefined && (
            <span className="text-muted-foreground/60 ml-1">
              ({searchTime}ms)
            </span>
          )}
        </p>

        {hasShareableState && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs gap-1 text-muted-foreground"
            onClick={handleCopyLink}
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-500" />
                Copied!
              </>
            ) : (
              <>
                <Link className="w-3 h-3" />
                Share
              </>
            )}
          </Button>
        )}
      </div>

      <select
        value={sortBy}
        onChange={(e) => onSortChange(e.target.value)}
        className="text-sm text-muted-foreground bg-transparent border border-border rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-ring"
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
