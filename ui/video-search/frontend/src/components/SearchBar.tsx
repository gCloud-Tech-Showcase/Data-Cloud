import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useState, useEffect, type FormEvent } from "react";

const EXPLORE_CHIPS = [
  "friendship",
  "chase scene",
  "music and dancing",
  "educational health",
  "animals",
  "war and military",
];

interface SearchBarProps {
  onSearch: (query: string) => void;
  onClear?: () => void;
  isLoading: boolean;
  externalQuery?: string;
}

export function SearchBar({
  onSearch,
  onClear,
  isLoading,
  externalQuery,
}: SearchBarProps) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (externalQuery !== undefined) setQuery(externalQuery);
  }, [externalQuery]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim());
  }

  function handleChipClick(chip: string) {
    setQuery(chip);
    onSearch(chip);
  }

  return (
    <div className="max-w-2xl mx-auto space-y-3">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (e.target.value === "" && onClear) onClear();
            }}
            placeholder="Search videos by describing what you're looking for..."
            className="pl-10 h-12 text-base"
            disabled={isLoading}
          />
        </div>
        <Button type="submit" size="lg" className="h-12 w-24" disabled={isLoading || !query.trim()}>
          {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Search"}
        </Button>
      </form>

      <p className="text-xs text-muted-foreground text-center">
        Try:{" "}
        {EXPLORE_CHIPS.map((chip, i) => (
          <span key={chip}>
            <button
              type="button"
              className="text-primary/70 hover:text-primary hover:underline transition-colors"
              onClick={() => handleChipClick(chip)}
            >
              {chip}
            </button>
            {i < EXPLORE_CHIPS.length - 1 && <span className="mx-1">&middot;</span>}
          </span>
        ))}
      </p>
    </div>
  );
}
