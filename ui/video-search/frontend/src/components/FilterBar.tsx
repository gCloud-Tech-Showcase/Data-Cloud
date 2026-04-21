import { Badge } from "@/components/ui/badge";

interface CategoryFilter {
  name: string;
  count: number;
}

interface FilterBarProps {
  categories: CategoryFilter[];
  activeFilter: string | null;
  onFilterChange: (filter: string | null) => void;
  totalResults?: number;
}

export function FilterBar({
  categories,
  activeFilter,
  onFilterChange,
  totalResults,
}: FilterBarProps) {
  if (categories.length === 0) return null;

  return (
    <div className="flex items-center gap-3 border-t border-border pt-4">
      <span className="text-xs text-muted-foreground uppercase tracking-wider flex-shrink-0">
        Filter
      </span>
      <div className="flex flex-wrap gap-1.5">
        <Badge
          variant={activeFilter === null ? "default" : "outline"}
          className="cursor-pointer transition-colors duration-200"
          onClick={() => onFilterChange(null)}
        >
          All{totalResults !== undefined && ` ${totalResults}`}
        </Badge>
        {categories.map((cat) => (
          <Badge
            key={cat.name}
            variant={activeFilter === cat.name ? "default" : "outline"}
            className="cursor-pointer transition-colors duration-200"
            onClick={() =>
              onFilterChange(activeFilter === cat.name ? null : cat.name)
            }
          >
            {cat.name}
            <span
              className={
                activeFilter === cat.name
                  ? "text-primary-foreground/70 ml-1"
                  : "text-muted-foreground ml-1"
              }
            >
              {cat.count}
            </span>
          </Badge>
        ))}
      </div>
    </div>
  );
}
