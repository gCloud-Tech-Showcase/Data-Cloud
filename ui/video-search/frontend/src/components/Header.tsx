import { Film, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  onAddVideos?: () => void;
  isAddView?: boolean;
  onBackToLibrary?: () => void;
}

export function Header({ onAddVideos, isAddView, onBackToLibrary }: HeaderProps) {
  return (
    <header className="bg-primary text-primary-foreground">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-4 flex items-center justify-between">
        <button
          type="button"
          className="flex items-center gap-3 hover:opacity-90 transition-opacity"
          onClick={onBackToLibrary}
        >
          <div className="bg-white/15 rounded-lg p-1.5">
            <Film className="w-5 h-5" />
          </div>
          <div className="text-left">
            <h1 className="text-lg font-bold tracking-tight">
              Video Library Intelligence
            </h1>
            <p className="text-xs text-primary-foreground/70">
              Semantic video search powered by Google Cloud
            </p>
          </div>
        </button>

        {!isAddView && onAddVideos && (
          <Button
            variant="secondary"
            size="sm"
            className="gap-1.5"
            onClick={onAddVideos}
          >
            <Plus className="w-4 h-4" />
            Add videos
          </Button>
        )}
      </div>
    </header>
  );
}
