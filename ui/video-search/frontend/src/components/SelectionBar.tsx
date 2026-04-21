import { useState } from "react";
import { Download, FolderPlus, X, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { VideoResult } from "@/types";

interface SelectionBarProps {
  selectedVideos: VideoResult[];
  onClearSelection: () => void;
}

export function SelectionBar({ selectedVideos, onClearSelection }: SelectionBarProps) {
  const [showExport, setShowExport] = useState(false);
  const [collectionName, setCollectionName] = useState("");
  const [collectionDesc, setCollectionDesc] = useState("");

  if (selectedVideos.length === 0) return null;

  function handleExportCSV() {
    const headers = [
      "title", "year", "category", "mood", "color_mode", "style",
      "ai_description", "themes", "characters", "source_url",
      "duration_seconds", "relevance_pct",
    ];

    const rows = selectedVideos.map((v) => [
      v.title,
      v.year ?? "",
      v.category ?? "",
      v.mood ?? "",
      v.color_mode ?? "",
      v.style ?? "",
      v.ai_description ?? "",
      "", // themes not in VideoResult currently
      "", // characters not in VideoResult currently
      v.source_url ?? "",
      v.duration_total_seconds ?? "",
      v.relevance_pct > 0 ? `${v.relevance_pct}%` : "",
    ]);

    const csv = [headers.join(","), ...rows.map((r) =>
      r.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")
    )].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = collectionName
      ? `${collectionName.toLowerCase().replace(/\s+/g, "-")}.csv`
      : "video-collection.csv";
    a.click();
    URL.revokeObjectURL(url);
    setShowExport(false);
  }

  function handleExportJSON() {
    const data = {
      collection: collectionName || "Untitled Collection",
      description: collectionDesc,
      created: new Date().toISOString(),
      video_count: selectedVideos.length,
      videos: selectedVideos.map((v) => ({
        title: v.title,
        year: v.year,
        video_id: v.video_id,
        category: v.category,
        mood: v.mood,
        color_mode: v.color_mode,
        style: v.style,
        ai_description: v.ai_description,
        source_url: v.source_url,
        duration_seconds: v.duration_total_seconds,
        relevance_pct: v.relevance_pct > 0 ? v.relevance_pct : undefined,
      })),
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = collectionName
      ? `${collectionName.toLowerCase().replace(/\s+/g, "-")}.json`
      : "video-collection.json";
    a.click();
    URL.revokeObjectURL(url);
    setShowExport(false);
  }

  return (
    <>
      {/* Floating action bar */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-foreground text-background rounded-full shadow-2xl px-6 py-3 flex items-center gap-4 animate-in slide-in-from-bottom-4">
        <span className="text-sm font-medium">
          {selectedVideos.length} video{selectedVideos.length !== 1 ? "s" : ""} selected
        </span>

        <div className="w-px h-5 bg-background/20" />

        <Button
          size="sm"
          variant="ghost"
          className="text-background hover:bg-background/10 gap-1.5"
          onClick={() => setShowExport(true)}
        >
          <FolderPlus className="w-4 h-4" />
          Create collection
        </Button>

        <Button
          size="sm"
          variant="ghost"
          className="text-background hover:bg-background/10 gap-1.5"
          onClick={handleExportCSV}
        >
          <Download className="w-4 h-4" />
          Export CSV
        </Button>

        <div className="w-px h-5 bg-background/20" />

        <Button
          size="sm"
          variant="ghost"
          className="text-background hover:bg-background/10"
          onClick={onClearSelection}
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Collection modal */}
      {showExport && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-medium text-foreground flex items-center gap-2">
                <FolderPlus className="w-5 h-5 text-primary" />
                Create Collection
              </h2>
              <Button variant="ghost" size="sm" onClick={() => setShowExport(false)}>
                <X className="w-4 h-4" />
              </Button>
            </div>

            <p className="text-sm text-muted-foreground">
              {selectedVideos.length} video{selectedVideos.length !== 1 ? "s" : ""} selected.
              All AI-generated metadata will be included in the export.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-muted-foreground">Collection name</label>
                <Input
                  value={collectionName}
                  onChange={(e) => setCollectionName(e.target.value)}
                  placeholder="e.g., Adventure Campaign Q3"
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Description (optional)</label>
                <Input
                  value={collectionDesc}
                  onChange={(e) => setCollectionDesc(e.target.value)}
                  placeholder="e.g., Selected clips for the adventure marketing campaign"
                  className="mt-1"
                />
              </div>
            </div>

            <div className="flex items-center gap-2 text-[10px] text-primary/60">
              <Sparkles className="w-3 h-3" />
              Export includes AI-generated category, mood, themes, and descriptions
            </div>

            <div className="flex gap-2 pt-2">
              <Button className="flex-1 gap-1.5" onClick={handleExportJSON}>
                <Download className="w-4 h-4" />
                Export JSON
              </Button>
              <Button variant="outline" className="flex-1 gap-1.5" onClick={handleExportCSV}>
                <Download className="w-4 h-4" />
                Export CSV
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
