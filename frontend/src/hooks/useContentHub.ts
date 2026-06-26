import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface ContentHubItem {
  id: string;
  kind: "kv" | "reel";
  brand: string;
  campaign_name: string;
  campaign_id: string;
  headline: string;
  content_type: string;
  created_at: number;
}

export function contentHubAssetUrl(id: string): string {
  return `${API_BASE}/content-hub/items/${id}/asset`;
}

export async function saveToContentHub(params: {
  kind: "kv" | "reel";
  brand: string;
  campaignName: string;
  campaignId: string;
  headline: string;
  assetDataUrl: string; // a "data:...;base64,..." URL, or a plain https:// URL to fetch first
}): Promise<ContentHubItem> {
  let dataUrl = params.assetDataUrl;
  if (!dataUrl.startsWith("data:")) {
    const blob = await (await fetch(dataUrl)).blob();
    dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }
  const match = dataUrl.match(/^data:([^;]+);base64,(.*)$/);
  if (!match) throw new Error("Could not read asset as base64");
  const [, contentType, assetB64] = match;

  const res = await fetch(`${API_BASE}/content-hub/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: params.kind,
      brand: params.brand,
      campaign_name: params.campaignName,
      campaign_id: params.campaignId,
      headline: params.headline,
      asset_b64: assetB64,
      content_type: contentType,
    }),
  });
  if (!res.ok) throw new Error(`Save failed (${res.status})`);
  return res.json();
}

export function useContentHub() {
  const [items, setItems] = useState<ContentHubItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/content-hub/items`);
      if (!res.ok) throw new Error(`List failed (${res.status})`);
      const data = await res.json();
      setItems(data.items ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    await fetch(`${API_BASE}/content-hub/items/${id}`, { method: "DELETE" });
    setItems((prev) => prev.filter((it) => it.id !== id));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { items, loading, error, refresh, remove };
}
