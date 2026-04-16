import { useState, type FormEvent } from "react";
import { Search, Loader2, Plus, CheckCircle, ExternalLink } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { searchArchive, ingestFromArchive } from "@/lib/api";
import type { ArchiveItem } from "@/types";

export function AddVideos() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ArchiveItem[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [ingesting, setIngesting] = useState<Set<string>>(new Set());
  const [ingested, setIngested] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    try {
      const data = await searchArchive(query.trim());
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setIsSearching(false);
    }
  }

  async function handleIngest(identifier: string) {
    setIngesting((prev) => new Set(prev).add(identifier));
    setError(null);
    try {
      await ingestFromArchive(identifier);
      setIngested((prev) => new Set(prev).add(identifier));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setIngesting((prev) => {
        const next = new Set(prev);
        next.delete(identifier);
        return next;
      });
    }
  }

  return (
    <div className="space-y-6">
      <div className="max-w-2xl mx-auto">
        <p className="text-sm text-muted-foreground text-center mb-4">
          Search Archive.org for public domain videos to add to your library.
          Videos are automatically segmented and indexed for semantic search.
        </p>
        <form onSubmit={handleSearch} className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search Archive.org (e.g. Superman, Betty Boop, health education)..."
            className="pl-10 pr-10 h-12 text-base"
            disabled={isSearching}
          />
          {isSearching && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground animate-spin" />
          )}
        </form>
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg p-4 text-sm">
          {error}
        </div>
      )}

      {results === null && !isSearching && (
        <div className="text-center py-12 space-y-3">
          <Plus className="w-12 h-12 text-muted-foreground/40 mx-auto" />
          <p className="text-muted-foreground">
            Search for public domain cartoons and educational films
          </p>
        </div>
      )}

      {results && results.length === 0 && (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No results found for "{query}"</p>
        </div>
      )}

      {results && results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {results.length} results from Archive.org
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {results.map((item) => {
              const isIngesting = ingesting.has(item.identifier);
              const isIngested = ingested.has(item.identifier);

              return (
                <Card key={item.identifier} className="overflow-hidden">
                  <CardContent className="p-0 flex">
                    <img
                      src={item.thumbnail_url}
                      alt={item.title}
                      className="w-32 h-24 object-cover flex-shrink-0 bg-muted"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                    <div className="p-3 flex-1 min-w-0 flex flex-col justify-between">
                      <div>
                        <h3 className="text-sm font-medium text-foreground truncate">
                          {item.title}
                        </h3>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {item.year && <span>{item.year}</span>}
                          {item.collection && (
                            <Badge variant="outline" className="ml-2 text-[10px] py-0">
                              {item.collection.includes("prelinger")
                                ? "Educational"
                                : "Cartoon"}
                            </Badge>
                          )}
                        </p>
                        {item.description && (
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {item.description}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2 mt-2">
                        {isIngested ? (
                          <Button size="sm" variant="secondary" disabled className="gap-1.5">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                            Added
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="default"
                            className="gap-1.5"
                            onClick={() => handleIngest(item.identifier)}
                            disabled={isIngesting}
                          >
                            {isIngesting ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Plus className="w-3.5 h-3.5" />
                            )}
                            {isIngesting ? "Adding..." : "Add to library"}
                          </Button>
                        )}
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button size="sm" variant="ghost" className="gap-1.5">
                            <ExternalLink className="w-3.5 h-3.5" />
                          </Button>
                        </a>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
