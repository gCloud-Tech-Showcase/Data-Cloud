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
  return (
    <div className="flex items-center justify-between py-2 border-b border-border">
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
