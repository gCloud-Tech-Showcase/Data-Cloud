import { Film, Plus, Bell, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";

interface HeaderProps {
  onAddVideos?: () => void;
  isAddView?: boolean;
  onBackToLibrary?: () => void;
}

export function Header({ onAddVideos, isAddView, onBackToLibrary }: HeaderProps) {
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains("dark")
  );

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [dark]);

  return (
    <header className="bg-primary text-primary-foreground">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-3 flex items-center justify-between">
        {/* Left: Logo + product name + org */}
        <button
          type="button"
          className="flex items-center gap-3 hover:opacity-90 transition-opacity"
          onClick={onBackToLibrary}
        >
          <div className="bg-white/15 rounded-lg p-1.5">
            <Film className="w-5 h-5" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight">
                Video Library Intelligence
              </h1>
              <span className="text-xs bg-white/15 px-1.5 py-0.5 rounded text-primary-foreground/80 hidden sm:inline">
                Beta
              </span>
            </div>
            <p className="text-xs text-primary-foreground/60">
              Pulsar Interactive
            </p>
          </div>
        </button>

        {/* Right: Actions + avatar */}
        <div className="flex items-center gap-2">
          {!isAddView && onAddVideos && (
            <Button
              variant="secondary"
              size="sm"
              className="gap-1.5"
              onClick={onAddVideos}
            >
              <Plus className="w-4 h-4" />
              <span className="hidden sm:inline">Add videos</span>
            </Button>
          )}

          <button
            type="button"
            className="p-1.5 rounded-md hover:bg-white/10 transition-colors"
            onClick={() => setDark(!dark)}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <button
            type="button"
            className="relative p-1.5 rounded-md hover:bg-white/10 transition-colors"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-amber-400 rounded-full" />
          </button>

          <div className="flex items-center gap-2 ml-1 pl-3 border-l border-white/20">
            <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-xs font-medium">
              CA
            </div>
            <div className="hidden md:block text-right">
              <p className="text-xs font-medium leading-tight">Carlos A.</p>
              <p className="text-[10px] text-primary-foreground/50">Admin</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
