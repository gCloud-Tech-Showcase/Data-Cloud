import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { FilterOption } from "@/types";

const FILTER_LABELS: Record<string, string> = {
  category: "Category",
  mood: "Mood",
  color_mode: "Color",
  style: "Style",
};

interface FilterSidebarProps {
  filters: Record<string, FilterOption[]>;
  activeFilters: Record<string, string | null>;
  onFilterChange: (field: string, value: string | null) => void;
  onClearAll: () => void;
}

export function FilterSidebar({
  filters,
  activeFilters,
  onFilterChange,
  onClearAll,
}: FilterSidebarProps) {
  const hasActiveFilters = Object.values(activeFilters).some((v) => v !== null);
  const filterEntries = Object.entries(filters).filter(
    ([, options]) => options.length > 0
  );

  if (filterEntries.length === 0) return null;

  return (
    <aside className="w-56 flex-shrink-0 space-y-5">
      <div className="flex items-center justify-between">
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

      {filterEntries.map(([field, options]) => (
        <div key={field} className="space-y-2">
          <p className="text-xs text-muted-foreground uppercase tracking-wider">
            {FILTER_LABELS[field] || field}
          </p>
          <div className="flex flex-col gap-1">
            {options.map((opt) => {
              const isActive = activeFilters[field] === opt.name;
              return (
                <button
                  key={opt.name}
                  type="button"
                  className={`flex items-center justify-between px-2 py-1.5 rounded-md text-left text-sm transition-colors duration-200 ${
                    isActive
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-foreground hover:bg-muted"
                  }`}
                  onClick={() =>
                    onFilterChange(field, isActive ? null : opt.name)
                  }
                >
                  <span className="truncate capitalize">{opt.name.replace(/_/g, " ")}</span>
                  <span className="text-xs text-muted-foreground ml-2 flex-shrink-0">
                    {opt.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ))}

      {hasActiveFilters && (
        <div className="pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground mb-2">Active filters</p>
          <div className="flex flex-wrap gap-1">
            {Object.entries(activeFilters)
              .filter(([, v]) => v !== null)
              .map(([field, value]) => (
                <Badge
                  key={field}
                  variant="default"
                  className="gap-1 capitalize text-xs"
                >
                  {value!.replace(/_/g, " ")}
                  <X
                    className="w-3 h-3 cursor-pointer"
                    onClick={() => onFilterChange(field, null)}
                  />
                </Badge>
              ))}
          </div>
        </div>
      )}
    </aside>
  );
}
