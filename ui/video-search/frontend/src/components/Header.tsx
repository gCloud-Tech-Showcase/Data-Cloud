import { Film } from "lucide-react";

export function Header() {
  return (
    <header className="border-b border-border bg-card">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-4 flex items-center gap-3">
        <Film className="w-6 h-6 text-primary" />
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Video Library Intelligence
          </h1>
          <p className="text-xs text-muted-foreground">
            Semantic video search powered by Google Cloud
          </p>
        </div>
      </div>
    </header>
  );
}
