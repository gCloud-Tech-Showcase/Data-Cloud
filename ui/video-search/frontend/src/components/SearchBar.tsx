import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useState, type FormEvent } from "react";

const EXPLORE_CHIPS = [
  "friendship",
  "chase scene",
  "music and dancing",
  "educational health",
  "animals",
  "war and military",
  "cooking",
  "outdoor adventure",
];

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim());
  }

  function handleChipClick(chip: string) {
    setQuery(chip);
    onSearch(chip);
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <form onSubmit={handleSubmit} className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search videos by describing what you're looking for..."
          className="pl-10 pr-10 h-12 text-base"
          disabled={isLoading}
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground animate-spin" />
        )}
      </form>

      <div className="flex flex-wrap justify-center gap-2">
        <span className="text-xs text-muted-foreground self-center mr-1">
          Explore:
        </span>
        {EXPLORE_CHIPS.map((chip) => (
          <Badge
            key={chip}
            variant="secondary"
            className="cursor-pointer hover:bg-accent transition-colors duration-200"
            onClick={() => handleChipClick(chip)}
          >
            {chip}
          </Badge>
        ))}
      </div>
    </div>
  );
}
