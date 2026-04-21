export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-background">
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>&copy; {year} Pulsar Interactive</span>
            <span className="hidden sm:inline text-border">|</span>
            <span>Powered by Google Cloud</span>
          </div>

          <nav className="flex items-center gap-4 text-xs text-muted-foreground">
            <a href="#" className="hover:text-foreground transition-colors">About</a>
            <a href="#" className="hover:text-foreground transition-colors">Help</a>
            <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
            <a href="#" className="hover:text-foreground transition-colors">Terms</a>
          </nav>
        </div>

        <p className="text-[10px] text-muted-foreground/50 text-center sm:text-left mt-3">
          Video analysis powered by Gemini 2.5 Flash &middot; Vector search powered by BigQuery &middot; Embeddings by multimodalembedding@001
        </p>
      </div>
    </footer>
  );
}
