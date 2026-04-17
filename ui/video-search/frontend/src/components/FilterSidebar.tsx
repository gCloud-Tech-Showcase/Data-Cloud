import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { FilterOption } from "@/types";
import { ChevronDown, ChevronRight, Sparkles, X } from "lucide-react";
import { useState } from "react";

const FILTER_LABELS: Record<string, string> = {
  category: "Category",
  mood: "Mood",
  color_mode: "Color",
  style: "Style",
};

// All expanded by default
const DEFAULT_EXPANDED = new Set(["category", "mood", "color_mode", "style"]);

interface FilterSidebarProps {
  filters: Record<string, FilterOption[]>;
  activeFilters: Record<string, Set<string>>;
  onFilterChange: (field: string, value: string) => void;
  onClearAll: () => void;
}

export function FilterSidebar({
  filters,
  activeFilters,
  onFilterChange,
  onClearAll,
}: FilterSidebarProps) {
  const [expanded, setExpanded] = useState<Set<string>>(DEFAULT_EXPANDED);

  const hasActiveFilters = Object.values(activeFilters).some((s) => s.size > 0);
  const filterEntries = Object.entries(filters).filter(
    ([, options]) => options.length > 0,
  );

  if (filterEntries.length === 0) return null;

  function toggleExpanded(field: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(field)) next.delete(field);
      else next.add(field);
      return next;
    });
  }

  // Collect all active filter values across all fields
  const activeChips: { field: string; value: string }[] = [];
  for (const [field, values] of Object.entries(activeFilters)) {
    for (const value of values) {
      activeChips.push({ field, value });
    }
  }

  return (
    <aside className="w-56 flex-shrink-0 space-y-1 bg-background rounded-xl border border-border p-4 shadow-sm h-fit sticky top-4">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-medium text-foreground">Filters</h3>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs text-muted-foreground"
            onClick={onClearAll}
          >
            Clear all
          </Button>
        )}
      </div>
      <p className="flex items-center gap-1 text-[10px] text-primary opacity-70 mb-3">
        <Sparkles className="w-3 h-3" />
        Gemini-extracted video attributes
      </p>

      {/* Active filter chips */}
      {activeChips.length > 0 && (
        <div className="flex flex-wrap gap-1 pb-3 border-b border-border mb-3">
          {activeChips.map(({ field, value }) => (
            <Badge
              key={`${field}-${value}`}
              variant="default"
              className="gap-1 capitalize text-xs cursor-pointer hover:bg-primary/80 transition-colors"
              onClick={() => onFilterChange(field, value)}
            >
              {value.replace(/_/g, " ")}
              <X className="w-3 h-3" />
            </Badge>
          ))}
        </div>
      )}

      {filterEntries.map(([field, options]) => {
        const isExpanded = expanded.has(field);
        const activeSet = activeFilters[field] || new Set();

        return (
          <div key={field}>
            <button
              type="button"
              className="flex items-center justify-between w-full py-2 text-left"
              onClick={() => toggleExpanded(field)}
            >
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground uppercase tracking-wider">
                {FILTER_LABELS[field] || field}
                <Sparkles className="w-2.5 h-2.5 text-primary opacity-50" />
              </span>
              {isExpanded ? (
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
              )}
            </button>

            {isExpanded && (
              <div className="flex flex-col gap-0.5 pb-2">
                {options.map((opt) => {
                  const isActive = activeSet.has(opt.name);
                  return (
                    <button
                      key={opt.name}
                      type="button"
                      className={`flex items-center justify-between px-2 py-1.5 rounded-md text-left text-sm transition-colors duration-200 ${
                        isActive
                          ? "bg-primary/10 text-primary font-medium"
                          : "text-foreground hover:bg-muted"
                      }`}
                      onClick={() => onFilterChange(field, opt.name)}
                    >
                      <span className="truncate capitalize">
                        {opt.name.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-muted-foreground ml-2 flex-shrink-0">
                        {opt.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </aside>
  );
}
