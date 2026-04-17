import { Film } from "lucide-react";

export function Header() {
  return (
    <header className="bg-primary text-primary-foreground">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-4 flex items-center gap-3">
        <div className="bg-white/15 rounded-lg p-1.5">
          <Film className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight">
            Video Library Intelligence
          </h1>
          <p className="text-xs text-primary-foreground/70">
            Semantic video search powered by Google Cloud
          </p>
        </div>
      </div>
    </header>
  );
}
